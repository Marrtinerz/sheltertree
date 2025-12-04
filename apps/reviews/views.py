from datetime import timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.db.models import Avg, Count, Sum, OuterRef, Subquery, Case, When, IntegerField
from django.views.generic import TemplateView, CreateView, View
from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector
from .models import Property, PropertyUnit, Review, PropertyStatus, ReviewStatus, Vote, PropertyManager, FloodingSeverity
from .forms import PropertyForm, PropertyUnitForm, ReviewForm, PropertySearchForm
from django.db.models import Q, F
from django.template.loader import render_to_string
from django.http import HttpResponse
from collections import defaultdict
from django.contrib.auth.mixins import LoginRequiredMixin
from apps.users.forms import FeatureInterestForm
from apps.users.models import FeatureInterest
from django.db.models.functions import Coalesce
from apps.core.event_bus import EventBus
from django.db.models import Count
from apps.core.forms import PlatformFeedbackForm
from apps.core.models import PlatformFeedback
from django.utils import timezone


# --- READ-ONLY VIEWS (for the public) ---


# Search and find using just Prefix Full-Text Search
# def find_properties(query_string):
#     """Encapsulates the core search logic."""
#     if not query_string or len(query_string) < 3:
#         return Property.objects.none()

#     # Populate search_vector on the fly. For ultimate performance, this should be a database trigger.
#     Property.objects.update(search_vector=SearchVector('name', 'address'))

#     vector = SearchVector('name', 'address')
#     query = SearchQuery(query_string)
    
#     return Property.objects.annotate(
#         rank=SearchRank(vector, query)
#     ).filter(
#         search_vector=query, 
#         status=PropertyStatus.APPROVED
#     ).order_by('-rank')


# Hybrid search and find
def find_properties(query_string):
    """
    This is now the single source of truth for all property searches.
    It performs a hybrid search and returns a single, ordered, and CHAINABLE QuerySet.
    """
    if not query_string or len(query_string) < 3:
        return Property.objects.none() # Return an empty QuerySet

    # === Method 1: High-Relevance FTS Search ===
    fts_query = SearchQuery(query_string, search_type='websearch')
    fts_results = Property.objects.annotate(
        rank=SearchRank(F('search_vector'), fts_query)
    ).filter(
        search_vector=fts_query,
        status=PropertyStatus.APPROVED
    ).order_by('-rank')
    
    # Get an ordered list of IDs from the high-relevance results
    fts_result_ids = list(fts_results.values_list('id', flat=True))

    # === Method 2: Broad Substring Search (`icontains`) ===
    substring_query = Q(name__icontains=query_string) | \
                      Q(address__icontains=query_string) | \
                      Q(city__icontains=query_string) | \
                      Q(state__name__icontains=query_string) | \
                      Q(country__name__icontains=query_string)

    substring_results = Property.objects.filter(
        substring_query,
        status=PropertyStatus.APPROVED
    ).exclude(id__in=fts_result_ids).distinct()
    
    substring_result_ids = list(substring_results.values_list('id', flat=True))

    # === Combine the IDs, preserving the order (FTS results first) ===
    final_ids = fts_result_ids + substring_result_ids

    if not final_ids:
        return Property.objects.none() # Return an empty QuerySet

    # === The World-Class Pattern: Preserve Custom Order in a QuerySet ===
    # This creates a temporary "ordering" field in the database based on the
    # position of each ID in our Python list.
    preserved_order = Case(*[When(pk=pk, then=pos) for pos, pk in enumerate(final_ids)])
    
    # Finally, return a SINGLE QuerySet containing all the properties,
    # ordered by our custom ranking. This QuerySet can be paginated,
    # annotated, or filtered further.
    return Property.objects.filter(id__in=final_ids).order_by(preserved_order)


class SearchView(TemplateView):
    template_name = 'reviews/search_results.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        form = PropertySearchForm(self.request.GET or None)
        query = self.request.GET.get('q')

        # --- THE CRITICAL FIX ---
        # We now explicitly track if a search has been performed.
        # This is True if 'q' is in the URL, even if its value is empty.
        search_performed = 'q' in self.request.GET
        context['search_performed'] = search_performed
        
        # Only run the search query if a search was actually performed.
        if search_performed and form.is_valid():
            cleaned_query = form.cleaned_data.get('q', '')
            context['results'] = find_properties(cleaned_query)
        
        context['form'] = form
        context['query'] = query
        context['intent'] = self.request.GET.get('intent', '')
        
        return context

# NEW view for our live search
def live_search_results(request):
    """
    Returns an HTML fragment containing search results for HTMX to display.
    """
    form = PropertySearchForm(request.GET or None)
    context = {"results": None}

    if form.is_valid():
        query = form.cleaned_data.get('q')
        context['results'] = find_properties(query)

    # Note: We render a DIFFERENT, smaller template here.
    return render(request, 'reviews/partials/_live_search_results.html', context)


class PropertyListView(ListView):
    model = Property
    template_name = 'reviews/property_list.html'
    context_object_name = 'properties'
    paginate_by = 9

    def get_queryset(self):
        """
        This view now delegates all annotation logic to the custom manager method,
        ensuring that only approved reviews are included in calculations.
        """
        query = self.request.GET.get('q')

        if query:
            # If there is a search query, use our powerful search engine.
            base_queryset = find_properties(query)
        else:
            # If there is no search, we apply our new, engagement-first sorting.
            # --- THE WORLD-CLASS FIX IS HERE ---
            # 1. Start with all approved properties.
            # 2. Use our manager to add the `review_count` annotation.
            # 3. Order by review_count DESC, then by created_at DESC.
            base_queryset = Property.objects.filter(status=PropertyStatus.APPROVED) \
                                            .with_reputation_data() \
                                            .order_by('-review_count', '-created_at')

        # --- THE FIX ---
        # Replace the manual annotation with the manager method.
        # This guarantees that only APPROVED reviews are counted and averaged.
        return base_queryset

    def get_context_data(self, **kwargs):
        """
        Pass the search query back to the template for display.
        """
        context = super().get_context_data(**kwargs)
        context['query'] = self.request.GET.get('q', '')
        return context


UNIT_BUTTON_DISPLAY_COUNT = 3

# Now, update the HTMX view to do the same
def get_unit_reviews(request, property_pk, unit_pk):
    """
    This HTMX view now renders a LARGER partial that includes the filters.
    """
    property_obj = get_object_or_404(Property, pk=property_pk)
    
    # --- THE NEW SEARCH LOGIC ---
    unit_query = request.GET.get('unit_q', '') # Get the search query from the URL
    
    all_units = PropertyUnit.objects.filter(property=property_obj) \
                                    .annotate(review_count=Count('reviews')) \
                                    .order_by('-review_count', 'unit_identifier')
    
    if unit_query:
        # If there's a search, filter the units by the identifier
        all_units = all_units.filter(unit_identifier__icontains=unit_query)
    
    active_unit = get_object_or_404(PropertyUnit, pk=unit_pk)
    
    all_reviews_grouped = get_annotated_reviews_for_property(property_obj, request.user)
    reviews_for_unit = all_reviews_grouped.get(active_unit, [])
    
    context = {
        'property': property_obj,
        'units': all_units,
        'reviews': reviews_for_unit,
        'active_unit': active_unit, # Pass the active unit to the partial
        'unit_query': unit_query, # Pass the query back to the template
        'UNIT_BUTTON_DISPLAY_COUNT': UNIT_BUTTON_DISPLAY_COUNT, # Pass the setting
        'unit_buttons': all_units[:UNIT_BUTTON_DISPLAY_COUNT],
        'unit_dropdown_items': all_units[UNIT_BUTTON_DISPLAY_COUNT:],
        'units': all_units, # Still needed for the 'Add My Unit' button
    }
    
    # --- RENDER THE NEW, LARGER PARTIAL ---
    return render(request, 'reviews/partials/_review_hub_content.html', context)

# ====================================================================
# 1. The World-Class Helper Function
# This function encapsulates all complex review-fetching logic.
# ====================================================================
def get_annotated_reviews_for_property(property_obj, user):
    """
    The single source of truth for fetching and preparing reviews for display.

    This function is architected for high performance:
    1.  Fetches all approved reviews for a property in one query, efficiently
        joining the author data with `select_related`.
    2.  Annotates each review with its helpful/unhelpful vote counts in the same query.
    3.  Fetches the current user's votes in a second, efficient query.
    4.  Attaches the user's vote to each review object in Python.
    
    Returns a dictionary of {unit: [annotated_reviews]}.
    """
    # Step 1 & 2: Fetch and annotate all reviews, including author data.
    # --- THE RESTORED LOGIC ---
    # `select_related('author')` is a critical performance optimization that
    # prevents a separate database query for every single review's author.
    all_reviews = Review.objects.filter(
        unit__property=property_obj,
        status=ReviewStatus.APPROVED
    ).select_related('author').annotate(
        helpful_votes=Count('votes', filter=Q(votes__value=1)),
        unhelpful_votes=Count('votes', filter=Q(votes__value=-1))
    ).order_by('-created_at')

    # Step 3: Get the current user's votes.
    user_votes_map = {}
    if user.is_authenticated:
        user_votes = Vote.objects.filter(
            review__in=all_reviews,
            user=user
        ).values('review_id', 'value')
        user_votes_map = {vote['review_id']: vote['value'] for vote in user_votes}
    
    # Step 4: Attach the user's vote to each review.
    for review in all_reviews:
        review.user_vote_value = user_votes_map.get(review.id)

    # Step 5: Group the fully prepared reviews by unit.
    reviews_by_unit = defaultdict(list)
    for review in all_reviews:
        reviews_by_unit[review.unit].append(review)
            
    return dict(reviews_by_unit)


# ====================================================================
# 2. The Full, Corrected, and World-Class Class-Based View
# ====================================================================
class PropertyDetailView(DetailView):
    """
    The definitive, world-class view for the Property Dashboard.
    It is now fully context-aware, ensuring the correct users can see
    the correct property states, while remaining highly performant.
    """
    # We no longer define a static queryset here, as it needs to be dynamic.
    template_name = 'reviews/property_detail.html'
    context_object_name = 'property'

    def get_queryset(self):
        """
        This is the new, world-class method for fetching the correct properties.
        It is context-aware based on the user's role and is the single
        source of truth for accessing a Property object.
        """
        # Start with our high-performance, annotated queryset. This is the base
        # for all user types, ensuring reputation data is always available.
        base_queryset = Property.objects.with_reputation_data()

        # Case 1: The user is an admin or staff member. They can see everything.
        if self.request.user.is_staff:
            return base_queryset
        
        # Case 2: The user is an authenticated, regular user.
        if self.request.user.is_authenticated:
            # They can see all APPROVED properties OR any property they personally added,
            # regardless of its current status.
            return base_queryset.filter(
                Q(status=PropertyStatus.APPROVED) | Q(added_by=self.request.user)
            ).distinct()
        
        # Case 3: The user is anonymous (not logged in).
        # They can ONLY see approved properties.
        return base_queryset.filter(status=PropertyStatus.APPROVED)

    def get_context_data(self, **kwargs):
        """
        This method is now built upon our robust get_queryset. It correctly
        preserves all the efficient data-fetching logic from your previous version.
        """
        context = super().get_context_data(**kwargs)
        property_obj = self.get_object()

        # --- Logic from your previous version (preserved and correct) ---
        
        # 1. Get ALL units for this property to power the filter buttons, ordered by the number of reviews.
        all_units = PropertyUnit.objects.filter(property=property_obj) \
                                    .annotate(review_count=Count('reviews')) \
                                    .order_by('-review_count', 'unit_identifier')
        
        # --- THE CRITICAL FIX ---
        # Prepare the two lists directly in the view using Python's powerful slicing.
        context['unit_buttons'] = all_units[:UNIT_BUTTON_DISPLAY_COUNT]
        context['unit_dropdown_items'] = all_units[UNIT_BUTTON_DISPLAY_COUNT:]
        
        # This original context variable is still useful for the 'Add My Unit' button
        context['units'] = all_units 

        # 2. Get all APPROVED and fully annotated reviews for this property.
        reviews_by_unit = get_annotated_reviews_for_property(property_obj, self.request.user)
        context['reviews_by_unit'] = reviews_by_unit
        
        # 3. For the initial display, get reviews for the first unit.
        first_unit = all_units.first()
        if first_unit:
            context['reviews'] = reviews_by_unit.get(first_unit, [])
            context['active_unit'] = first_unit
        else:
            context['reviews'] = []
            context['active_unit'] = None

        # 4. Explicitly calculate and pass the summary data for the "At a Glance" card.
        summary_data = Review.objects.filter(
            unit__property=property_obj, 
            status=ReviewStatus.APPROVED
        ).aggregate(
            avg_security=Avg('security_rating'),
            avg_electricity=Avg('electricity_rating'),
            avg_water=Avg('water_rating'),
            avg_management=Avg('management_rating'),
            avg_roads=Avg('road_network_rating'),
            avg_mobile=Avg('mobile_network_rating'),
        )
        context['summary'] = summary_data
        # context['unit_query'] = '' # On initial load, the query is empty
        context['UNIT_BUTTON_DISPLAY_COUNT'] = UNIT_BUTTON_DISPLAY_COUNT
        
        # --- THE WORLD-CLASS ADDITION: FLOODING INSIGHT CALCULATION ---

        # 1. Get the distribution of flooding responses in a single, efficient query.
        flooding_distribution = Review.objects.filter(
            unit__property=property_obj,
            status=ReviewStatus.APPROVED
        ).values('flooding_severity').annotate(count=Count('flooding_severity'))

        # 2. Process this data in Python to find the most severe insight.
        # We create a map for easy lookup.
        counts = {item['flooding_severity']: item['count'] for item in flooding_distribution}
        
        flooding_insight = None
        total_responses = sum(counts.values())

        if total_responses > 0:
            # We check in order of severity, from worst to best.
            if FloodingSeverity.CATASTROPHIC in counts:
                flooding_insight = {
                    'severity': 'high',
                    'label': 'Internal Flooding Reported',
                    'description': f"{counts[FloodingSeverity.CATASTROPHIC]} of {total_responses} reviewers reported water entering their home."
                }
            elif FloodingSeverity.COMPOUND in counts:
                flooding_insight = {
                    'severity': 'medium',
                    'label': 'Compound Flooding Reported',
                    'description': f"{counts[FloodingSeverity.COMPOUND]} of {total_responses} reviewers reported water in parking/common areas."
                }
            elif FloodingSeverity.EXTERNAL in counts:
                flooding_insight = {
                    'severity': 'low',
                    'label': 'External Flooding Reported',
                    'description': f"{counts[FloodingSeverity.EXTERNAL]} of {total_responses} reviewers reported flooding on access roads."
                }
            else: # If only 'NONE' is present
                flooding_insight = {
                    'severity': 'safe',
                    'label': 'No Flooding Reported',
                    'description': f"All {total_responses} reviewers reported the property and access roads remain dry."
                }
        
        context['flooding_insight'] = flooding_insight
            
            
        return context


# --- WRITE VIEWS (for logged-in users, protected by @login_required) ---

class AddPropertyView(CreateView):
    """
    Handles the creation of a new Property.
    Supports "Lazy Registration" (Anonymous Submissions).
    - Logged In: Creates property linked to user.
    - Anonymous: Creates 'Orphan' property and prompts login to claim it.
    """
    model = Property
    form_class = PropertyForm
    template_name = 'reviews/add_property.html'
    
    def form_valid(self, form):
        # --- PATH A: LOGGED IN ---
        if self.request.user.is_authenticated:
            form.instance.status = PropertyStatus.PENDING_APPROVAL
            form.instance.added_by = self.request.user
            self.object = form.save()
            
            # messages.success(self.request, _("Property submitted for review! Now, please add your unit and review."))
            
            return redirect(self.get_success_url())

        # --- PATH B: ANONYMOUS (The "Growth" Flow) ---
        else:
            # 1. SAVE to Database immediately (Capture the Inventory)
            form.instance.status = PropertyStatus.PENDING_APPROVAL
            form.instance.added_by = None # Orphaned for now
            self.object = form.save()
            
            # 2. Store ID in session for "claiming" later
            pending_data = {
                'property_id': self.object.pk,
                'type': 'property_claim' # Flag for the Handler
            }
            self.request.session['pending_property_submission'] = pending_data
            
            # 3. Redirect to Login -> Handler
            login_url = reverse_lazy('account_login')
            handler_url = reverse_lazy('reviews:process-pending-property')
            
            messages.info(self.request, _("Property saved! Please log in or sign up to claim it and add your review."))
            
            return redirect(f'{login_url}?next={handler_url}')

    def get_success_url(self):
        return reverse_lazy('reviews:add-property-success', kwargs={'pk': self.object.pk})

def add_property_success(request, pk):
    """
    A success page shown after a property is submitted.
    It guides the user to Stage 2: adding their unit and review.
    """
    property_instance = get_object_or_404(Property, pk=pk)
    return render(request, 'reviews/add_property_success.html', {'property': property_instance})


class ProcessPendingPropertyView(LoginRequiredMixin, View):
    """
    Handles 'claiming' a property submitted anonymously.
    Includes robustness for Signal race conditions and session loss.
    """
    def get(self, request, *args, **kwargs):
        # 1. Try to get ID from Session
        pending_data = request.session.get('pending_property_submission')
        property_id = pending_data.get('property_id') if pending_data else None
        
        property_obj = None

        # 2. Strategy A: Look up by ID (if session survived)
        if property_id:
            try:
                property_obj = Property.objects.get(pk=property_id)
            except Property.DoesNotExist:
                pass
        
        # 3. Strategy B: Database Fallback (if session died)
        if not property_obj:
            # Look back 30 mins to match the Signal/Adapter window
            recent_time = timezone.now() - timedelta(minutes=30)
            property_obj = Property.objects.filter(
                added_by=request.user, 
                created_at__gte=recent_time
            ).order_by('-created_at').first()

        # 4. Final Validation (Stop the Loop Here)
        if not property_obj:
            # We truly have nothing. Stop loop and exit.
            request.session['lazy_flow_completed'] = True
            return redirect('home')

        # --- CONVERGENCE POINT ---

        # 5. Ownership Enforcement
        # If we found it via Session ID, we ensure the current user owns it.
        # This handles the "Typo User" case where we need to steal it back.
        if property_obj.added_by != request.user:
            property_obj.added_by = request.user
            property_obj.save()

        # 6. Analytics
        bus = EventBus(request)
        bus.push_event('submit_property') 

        # 7. Clean up Session
        if 'pending_property_submission' in request.session:
            del request.session['pending_property_submission']
            
        # 8. Mark Flow Complete (Stop Middleware)
        request.session['lazy_flow_completed'] = True

        messages.success(request, _("Property verified! Now, please add your unit and review."))
        return redirect('reviews:add-property-success', pk=property_obj.pk)

class PropertyContinueToReviewView(LoginRequiredMixin, View):
    """
    Sets the lazy flow as complete, then forwards user to add a review.
    """
    def get(self, request, property_pk):
        # 1. Mark flow as complete so middleware stops intercepting
        if not request.user.lazy_registration_complete:
            request.user.lazy_registration_complete = True
            request.user.save(update_fields=['lazy_registration_complete'])
        
        # 2. Redirect to the next step
        return redirect('reviews:add-unit-and-review', property_pk=property_pk)

class AddUnitAndReviewView(TemplateView):
    """
    Handles the creation of a new PropertyUnit and its associated Review.
    Refactored for Lazy Registration (Draft Pattern).
    """
    template_name = 'reviews/add_unit_and_review.html'
    
    def dispatch(self, request, *args, **kwargs):
        self.property = get_object_or_404(Property, pk=self.kwargs['property_pk'])
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['property'] = self.property
        context.setdefault('unit_form', PropertyUnitForm(property=self.property))
        context.setdefault('review_form', ReviewForm())
        return context

    def get(self, request, *args, **kwargs):
        return self.render_to_response(self.get_context_data())

    def post(self, request, *args, **kwargs):
        unit_form = PropertyUnitForm(request.POST, property=self.property)
        review_form = ReviewForm(request.POST)

        # Both forms must be valid to proceed
        if unit_form.is_valid() and review_form.is_valid():
            return self.forms_valid(unit_form, review_form)
        else:
            return self.forms_invalid(unit_form, review_form)

    def forms_valid(self, unit_form, review_form):
        
        # --- PATH A: LOGGED IN (Standard Flow) ---
        if self.request.user.is_authenticated:
            # 1. Save Unit
            unit = unit_form.save(commit=False)
            unit.property = self.property
            unit.save()

            # 2. Save Review
            review = review_form.save(commit=False)
            review.unit = unit
            review.author = self.request.user
            review.status = ReviewStatus.PENDING_CONTENT_REVIEW
            review.save()
            
            # 3. Handle Feedback
            feedback_text = review_form.cleaned_data.get('platform_feedback')
            if feedback_text and feedback_text.strip():
                PlatformFeedback.objects.create(
                    user=self.request.user,
                    feedback_text=feedback_text,
                    source_url=self.request.META.get('HTTP_REFERER', 'unknown')
                )
            
            # 4. Analytics & Success
            bus = EventBus(self.request)
            bus.push_event('Lead')

            self.object = review
            return redirect(self.get_success_url())

        # --- PATH B: ANONYMOUS (The "Draft" Flow) ---
        else:
            # --- PATH B: ANONYMOUS ---
            # 1. Save Unit
            unit = unit_form.save(commit=False)
            unit.property = self.property
            unit.save()

            # 2. Save Review
            review = review_form.save(commit=False)
            review.unit = unit
            review.author = None
            review.status = ReviewStatus.PENDING_SIGNUP
            review.save()
            
            # 3. Handle Feedback & Get ID
            feedback_id = None # Initialize
            feedback_text = review_form.cleaned_data.get('platform_feedback')
            
            if feedback_text and feedback_text.strip():
                feedback = PlatformFeedback.objects.create(
                    user=None,
                    feedback_text=feedback_text,
                    source_url="pending_signup_flow_unit_review"
                )
                feedback_id = feedback.pk # <--- CAPTURE ID

            # 4. Store IDs in Session
            pending_data = {
                'review_id': review.pk,
                'feedback_id': feedback_id, # <--- STORE ID
                'type': 'unit_and_review' 
            }
            self.request.session['pending_review_submission'] = pending_data
            
            # 5. Redirect
            login_url = reverse_lazy('account_login')
            handler_url = reverse_lazy('reviews:process-pending-review')
            messages.info(self.request, _("Unit added and review saved! Please log in or sign up to verify it."))
            return redirect(f'{login_url}?next={handler_url}')

    def forms_invalid(self, unit_form, review_form):
        return self.render_to_response(
            self.get_context_data(unit_form=unit_form, review_form=review_form)
        )

    def get_success_url(self):
        return reverse_lazy('reviews:review_success', kwargs={'review_pk': self.object.pk})

class AddReviewView(CreateView):
    """
    Handles the creation of a new Review for a specific PropertyUnit.
    Refactored to support "Lazy Registration" using the "Draft Pattern".
    """
    model = Review
    form_class = ReviewForm
    template_name = 'reviews/add_review_to_unit.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        self.unit = get_object_or_404(PropertyUnit, pk=self.kwargs['unit_pk'])
        context['unit'] = self.unit
        context['property'] = self.unit.property
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        return kwargs

    def form_valid(self, form):
        self.unit = get_object_or_404(PropertyUnit, pk=self.kwargs['unit_pk'])

        # --- PATH A: LOGGED IN (Standard Flow) ---
        if self.request.user.is_authenticated:
            
            # 1. Process the Review
            review = form.save(commit=False)
            review.unit = self.unit
            review.author = self.request.user
            review.status = ReviewStatus.PENDING_CONTENT_REVIEW
            review.save()
            self.object = review 

            # 2. Process Optional Feedback
            feedback_text = form.cleaned_data.get('platform_feedback')
            if feedback_text and feedback_text.strip():
                PlatformFeedback.objects.create(
                    user=self.request.user,
                    feedback_text=feedback_text,
                    source_url=self.request.META.get('HTTP_REFERER', 'unknown')
                )
            
            # 3. Analytics (Matches your GTM Custom Event Trigger)
            bus = EventBus(self.request)
            bus.push_event('Lead')
            
            return redirect(self.get_success_url())

        # --- PATH B: ANONYMOUS (The "Draft" Flow) ---
        else:
            # 1. SAVE to Database as Draft (Capture the Data)
            review = form.save(commit=False)
            review.unit = self.unit
            review.author = None 
            review.status = ReviewStatus.PENDING_SIGNUP
            review.save()
            
            # 2. Capture Feedback & Get ID
            feedback_id = None # Initialize
            feedback_text = form.cleaned_data.get('platform_feedback')
            
            if feedback_text and feedback_text.strip():
                feedback = PlatformFeedback.objects.create(
                    user=None,
                    feedback_text=feedback_text,
                    source_url="pending_signup_flow"
                )
                feedback_id = feedback.pk # <--- CAPTURE ID

            # 3. Store IDs in session
            pending_data = {
                'review_id': review.pk, 
                'feedback_id': feedback_id, # <--- STORE ID
                'type': 'review_only'
            }
            
            self.request.session['pending_review_submission'] = pending_data
            
            # 4. Redirect
            login_url = reverse_lazy('account_login')
            handler_url = reverse_lazy('reviews:process-pending-review')
            messages.info(self.request, _("Your review has been saved! Please log in or sign up to verify it and make it live."))
            return redirect(f'{login_url}?next={handler_url}')

    def get_success_url(self):
        return reverse_lazy('reviews:review_success', kwargs={'review_pk': self.object.pk})
    
class ProcessPendingReviewView(LoginRequiredMixin, View):
    """
    Handles the post-login redirection for reviews.
    Includes Trusted Handoff logic (Stealing from Typo User) and Status Promotion.
    """
    def get(self, request, *args, **kwargs):
        # 1. Try to get ID from Session
        pending_data = request.session.get('pending_review_submission')
        review_id = pending_data.get('review_id') if pending_data else None

        review = None

        # 2. Strategy A: Look up by ID (if session survived)
        if review_id:
            try:
                review = Review.objects.get(pk=review_id)
            except Review.DoesNotExist:
                pass

        # 3. Strategy B: Database Fallback (if session died)
        if not review:
            recent_time = timezone.now() - timedelta(minutes=30)
            review = Review.objects.filter(
                author=request.user, 
                created_at__gte=recent_time
            ).order_by('-created_at').first()

        # 4. Final Validation
        if not review:
            request.session['lazy_flow_completed'] = True
            return redirect('home')

        # --- CONVERGENCE POINT ---
        
        # 5. Ownership Enforcement (Trusted Handoff)
        # If we have the session ID (or found it via DB fallback), we enforce ownership.
        # This fixes the "Typo User" case. We steal it back.
        if review.author != request.user:
            review.author = request.user

        # 6. Status Promotion (The "Go Live" Step)
        # We ensure the review is moved out of the "Pending Signup" limbo.
        # This runs even if the Signal already claimed it, ensuring consistency.
        if review.status == ReviewStatus.PENDING_SIGNUP:
            if review.unit.property.status == PropertyStatus.APPROVED:
                review.status = ReviewStatus.PENDING_CONTENT_REVIEW
            else:
                review.status = ReviewStatus.PENDING_PROPERTY_APPROVAL

        # 7. Sync Verification
        if request.user.is_phone_verified and not review.is_author_phone_verified:
            review.is_author_phone_verified = True
            
        review.save()

        # 8. Analytics (Conversion Event)
        bus = EventBus(request)
        bus.push_event('submit_review') 

        # 9. Cleanup Session
        if 'pending_review_submission' in request.session:
            del request.session['pending_review_submission']

        # 10. Mark Flow Complete (Stop Middleware)
        request.session['lazy_flow_completed'] = True

        return redirect('reviews:review_success', review_pk=review.pk)
    
class SkipLazyFlow(LoginRequiredMixin, View):
    """
    Marks the lazy registration flow as complete and redirects to Home.
    """
    def get(self, request, *args, **kwargs):
        user = request.user
        
        if not user.lazy_registration_complete:
            user.lazy_registration_complete = True
            user.save(update_fields=['lazy_registration_complete'])

        # messages.info(request, _("You can verify your account later from your Profile."))
        return redirect('reviews:home') # Redirect to Home, not property-list (simpler)
    
class StartVerificationFromLazyFlow(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        # 1. Mark flow as complete (so middleware stops intercepting)
        request.user.lazy_registration_complete = True
        request.user.save(update_fields=['lazy_registration_complete'])
        
        # 2. Redirect to Phone Add
        return redirect('phone_add')
        
class HomePageView(TemplateView):
    """
    Renders the static homepage. The search form is added to the context
    via the global context processor.
    """
    template_name = 'reviews/home.html'


def vote_on_review(request, review_pk):
    # --- THE FIX ---
    # Fetch the review object ONCE at the very top, and ALWAYS annotate it
    # with the current vote counts. This ensures the 'review' variable
    # has the .helpful_votes and .unhelpful_votes attributes available
    # for all logic paths below (logged-in or not).
    
    # We use a subquery to get the object and its counts in one go.
    annotated_reviews = Review.objects.annotate(
        helpful_votes=Count('votes', filter=Q(votes__value=1)),
        unhelpful_votes=Count('votes', filter=Q(votes__value=-1))
    )
    review = get_object_or_404(annotated_reviews, pk=review_pk)

    # --- Path 1: User is NOT logged in ---
    if not request.user.is_authenticated:
        # Now, the 'review' object we pass to the template already has the
        # correct vote counts attached to it.
        return render(request, 'reviews/partials/_login_to_vote.html', {'review': review})

    # --- Path 2: User IS logged in (original logic continues) ---
    vote_type = request.POST.get('vote_type')
    vote_value = 1 if vote_type == 'helpful' else -1

    existing_vote = Vote.objects.filter(review=review, user=request.user).first()

    if existing_vote:
        if existing_vote.value == vote_value:
            existing_vote.delete()
        else:
            existing_vote.value = vote_value
            existing_vote.save()
    else:
        Vote.objects.create(review=review, user=request.user, value=vote_value)

    # --- IMPORTANT: Re-render the main partial after a successful vote ---
    # We must re-calculate the vote counts and user's vote status *after*
    # the vote has been saved to get the most up-to-date information.
    
    helpful_votes = review.votes.filter(value=1).count()
    unhelpful_votes = review.votes.filter(value=-1).count()
    
    current_user_vote = review.votes.filter(user=request.user).first()
    user_vote_value = current_user_vote.value if current_user_vote else None

    context = {
        'review': review,
        'helpful_votes': helpful_votes,
        'unhelpful_votes': unhelpful_votes,
        'user_vote_value': user_vote_value,
    }
    
    return render(request, 'reviews/partials/_vote_buttons.html', context)



class ReviewSuccessView(LoginRequiredMixin, DetailView):
    model = Review
    template_name = 'reviews/review_success_campaign.html'
    context_object_name = 'review' # The object will be available as 'review' in the template
    pk_url_kwarg = 'review_pk' # Tells the DetailView to get the object using 'review_pk' from the URL



class RequestReviewComingSoonView(CreateView):
    model = FeatureInterest
    form_class = FeatureInterestForm
    template_name = 'reviews/coming_soon_taproot.html'
    success_url = reverse_lazy('reviews:coming_soon_success')

    def form_valid(self, form):
        # We explicitly set the feature name on the backend.
        form.instance.feature_name = "The Taproot"
        return super().form_valid(form)
    

def search_units_htmx(request, property_pk):
    """
    A dedicated HTMX view that returns ONLY the list of filtered units
    for the dropdown. This is our "scalpel".
    """
    property_obj = get_object_or_404(Property, pk=property_pk)
    unit_query = request.GET.get('unit_q', '')
    
    # We start with all units and filter if there's a query.
    units = PropertyUnit.objects.filter(property=property_obj)
    if unit_query:
        units = units.filter(unit_identifier__icontains=unit_query)
    
    # We also need to know which unit is currently active to highlight it.
    active_unit_pk = request.GET.get('active_unit_pk')
    
    context = {
        'property': property_obj,
        'unit_dropdown_items': units, # We only need the list for the dropdown
        'active_unit_pk': int(active_unit_pk) if active_unit_pk else None,
    }
    
    # Render a new, tiny partial template.
    return render(request, 'reviews/partials/_unit_dropdown_list.html', context)

def get_unit_dropdown_content(request, property_pk):
    """
    An HTMX-powered view that returns an HTML fragment containing the
    ENTIRE content for the "More Units" dropdown, ensuring it is always reset.
    """
    property_obj = get_object_or_404(Property, pk=property_pk)
    all_units = PropertyUnit.objects.filter(property=property_obj)
    
    # Get the currently active unit to pass down for highlighting
    active_unit_pk = request.GET.get('active_unit_pk')
    
    context = {
        'property': property_obj,
        'unit_buttons': all_units[:UNIT_BUTTON_DISPLAY_COUNT],
        'unit_dropdown_items': all_units[UNIT_BUTTON_DISPLAY_COUNT:],
        'active_unit_pk': int(active_unit_pk) if active_unit_pk else None,
        'unit_query': '', # The search query is always reset
    }
    
    # Render a new, larger partial template for the dropdown content.
    return render(request, 'reviews/partials/_unit_dropdown_content.html', context)