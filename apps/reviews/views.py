from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.db.models import Avg, Count, Sum, OuterRef, Subquery, Case, When, IntegerField
from django.views.generic import TemplateView, CreateView
from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector
from .models import Property, PropertyUnit, Review, PropertyStatus, ReviewStatus, Vote, PropertyManager
from .forms import PropertyForm, PropertyUnitForm, ReviewForm, PropertySearchForm
from django.db.models import Q, F
from django.template.loader import render_to_string
from django.http import HttpResponse
from collections import defaultdict
from django.contrib.auth.mixins import LoginRequiredMixin
from apps.users.forms import FeatureInterestForm
from apps.users.models import FeatureInterest
from django.db.models.functions import Coalesce

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
            queryset = find_properties(query)
        else:
            # If there is no search, just show the latest approved properties.
            queryset = Property.objects.filter(status=PropertyStatus.APPROVED).order_by('-created_at')

        # --- THE FIX ---
        # Replace the manual annotation with the manager method.
        # This guarantees that only APPROVED reviews are counted and averaged.
        return queryset.with_reputation_data()

    def get_context_data(self, **kwargs):
        """
        Pass the search query back to the template for display.
        """
        context = super().get_context_data(**kwargs)
        context['query'] = self.request.GET.get('q', '')
        return context


class PropertyDetailView(LoginRequiredMixin, DetailView):
    """
    Displays the details of a single property and its reviews.
    KEY CHANGE: This view now calculates an "At a Glance" summary for the property.
    """
    model = Property
    template_name = 'reviews/property_detail.html'
    context_object_name = 'property'

    def get_queryset(self):
        """
        Ensures that non-approved properties cannot be accessed via a direct URL guess.
        """
        return Property.objects.filter(status=PropertyStatus.APPROVED)

    def get_context_data(self, **kwargs):
        """
        Extends the context to add an aggregated review summary and to efficiently
        pre-calculate vote counts and the current user's vote for each review.
        """
        context = super().get_context_data(**kwargs)
        property_instance = self.get_object()

        # --- 1. Summary Calculation (This part remains unchanged and is correct) ---
        summary_data = Review.objects.filter(
            unit__property=property_instance,
            status=ReviewStatus.APPROVED
        ).aggregate(
            average_security=Avg('security_rating'),
            average_electricity=Avg('electricity_rating'),
            average_water=Avg('water_rating'),
            average_management=Avg('management_rating'),
            average_roads=Avg('road_network_rating'),
            average_mobile=Avg('mobile_network_rating'),
            total_reviews=Count('id')
        )
        if summary_data['total_reviews'] > 0:
            averages = [v for v in summary_data.values() if isinstance(v, float)]
            summary_data['overall_average'] = sum(averages) / len(averages) if averages else 0
        else:
            summary_data['overall_average'] = 0
        context['summary'] = summary_data


        # --- 2. THE FIX: Fetch annotated reviews and group them by unit ---

        # First, get all approved reviews for the property, with vote counts annotated.
        # This is the single source of truth for our reviews.
        all_reviews_for_property = Review.objects.filter(
            unit__property=property_instance,
            status=ReviewStatus.APPROVED
        ).annotate(
            helpful_votes=Count('votes', filter=Q(votes__value=1)),
            unhelpful_votes=Count('votes', filter=Q(votes__value=-1))
        ).order_by('-created_at')

        # Get the user's vote for each of these reviews
        if self.request.user.is_authenticated:
            user_votes = Vote.objects.filter(
                review__in=all_reviews_for_property,
                user=self.request.user
            ).values('review_id', 'value')
            user_votes_map = {vote['review_id']: vote['value'] for vote in user_votes}
        else:
            user_votes_map = {}
        
        # Attach the user's vote to each review object
        for review in all_reviews_for_property:
            review.user_vote_value = user_votes_map.get(review.id)

        # Now, group these fully-prepared reviews by their unit.
        # This prevents the template from making new, un-annotated DB queries.
        reviews_by_unit = defaultdict(list)
        for review in all_reviews_for_property:
            reviews_by_unit[review.unit].append(review)
            
        # Add the grouped data to the context. The key is the Unit object itself.
        context['reviews_by_unit'] = dict(reviews_by_unit)
        
        return context


# --- WRITE VIEWS (for logged-in users, protected by @login_required) ---

class AddPropertyView(LoginRequiredMixin, CreateView):
    model = Property
    form_class = PropertyForm
    template_name = 'reviews/add_property.html'
    
    def form_valid(self, form):
        """
        This is the corrected implementation. We modify the form's instance
        and then let the parent class handle the save operation.
        """
        # Set the fields that are not on the form
        form.instance.status = PropertyStatus.PENDING_APPROVAL
        form.instance.added_by = self.request.user
        
        messages.success(self.request, _("Property submitted for review! Now, please add your unit and review."))
        
        # DO NOT save here. Let the parent class do it.
        # The super().form_valid(form) call will save the instance and set self.object.
        return super().form_valid(form)

    def get_success_url(self):
        """
        This method will work correctly because the super().form_valid() call
        in the corrected code above will set self.object before this is called.
        """
        return reverse_lazy('reviews:add-property-success', kwargs={'pk': self.object.pk})


@login_required
def add_property_success(request, pk):
    """
    A success page shown after a property is submitted.
    It guides the user to Stage 2: adding their unit and review.
    """
    property_instance = get_object_or_404(Property, pk=pk)
    return render(request, 'reviews/add_property_success.html', {'property': property_instance})


class AddUnitAndReviewView(LoginRequiredMixin, TemplateView):
    """
    Handles the creation of a new PropertyUnit and its associated Review.
    This view manages two forms simultaneously and provides a clean,
    class-based structure for the logic.
    """
    template_name = 'reviews/add_unit_and_review.html'
    
    def dispatch(self, request, *args, **kwargs):
        """
        This method runs first. It's the perfect place to fetch objects
        that are needed by both GET and POST requests.
        """
        # Fetch the parent property once and attach it to the view instance.
        self.property = get_object_or_404(Property, pk=self.kwargs['property_pk'])
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        """
        Populates the context dictionary for the template.
        """
        context = super().get_context_data(**kwargs)
        context['property'] = self.property
        # If forms aren't passed in kwargs (e.g., on initial GET), create empty ones.
        context.setdefault('unit_form', PropertyUnitForm(property=self.property))
        context.setdefault('review_form', ReviewForm())
        return context

    def get(self, request, *args, **kwargs):
        """
        Handles GET requests: displays the empty forms.
        """
        return self.render_to_response(self.get_context_data())

    def post(self, request, *args, **kwargs):
        """
        Handles POST requests: validates both forms and processes the data.
        """
        unit_form = PropertyUnitForm(request.POST, property=self.property)
        review_form = ReviewForm(request.POST)

        if unit_form.is_valid() and review_form.is_valid():
            return self.forms_valid(unit_form, review_form)
        else:
            return self.forms_invalid(unit_form, review_form)

    def forms_valid(self, unit_form, review_form):
        """
        This method is called when both forms are valid.
        It contains all the success logic from your original FBV.
        """
        # Save the unit, linking it to the property.
        unit = unit_form.save(commit=False)
        unit.property = self.property
        unit.save()

        # Save the review, linking it to the new unit and the user.
        review = review_form.save(commit=False)
        review.unit = unit
        review.author = self.request.user
        
        # Set the review's initial status based on the parent property's status.
        if self.property.status == PropertyStatus.APPROVED:
            review.status = ReviewStatus.PENDING_CONTENT_REVIEW
        else:
            review.status = ReviewStatus.PENDING_PROPERTY_APPROVAL
        
        # The Review's save() method handles the is_author_phone_verified snapshot.
        review.save()

        # Store the newly created review on the view instance so get_success_url can access it.
        self.object = review
        return redirect(self.get_success_url())

    def forms_invalid(self, unit_form, review_form):
        """
        This method is called when one or both forms are invalid.
        It re-renders the page with the forms containing the error messages.
        """
        return self.render_to_response(
            self.get_context_data(unit_form=unit_form, review_form=review_form)
        )

    def get_success_url(self):
        """
        Returns the URL to redirect to after a successful submission.
        """
        return reverse_lazy('reviews:review_success', kwargs={'review_pk': self.object.pk})


class AddReviewView(LoginRequiredMixin, CreateView):
    """
    Handles the creation of a new Review for a specific PropertyUnit.
    This is the modern, scalable, and professional "Review Composer" view.
    """
    model = Review
    form_class = ReviewForm
    template_name = 'reviews/add_review_to_unit.html' # The new premium template

    def get_context_data(self, **kwargs):
        """
        Passes the necessary unit and property context to the template.
        """
        context = super().get_context_data(**kwargs)
        self.unit = get_object_or_404(PropertyUnit, pk=self.kwargs['unit_pk'])
        context['unit'] = self.unit
        context['property'] = self.unit.property
        return context

    def get_form_kwargs(self):
        """
        Passes keyword arguments to the form. We could use this to pass
        'is_bounty' if we were handling that flow here.
        """
        kwargs = super().get_form_kwargs()
        # Example for the future:
        # unit = get_object_or_404(PropertyUnit, pk=self.kwargs['unit_pk'])
        # if unit.property.community_question:
        #     kwargs['is_bounty'] = True
        return kwargs

    def form_valid(self, form):
        """
        This method is called when the submitted form is valid.
        It's the perfect place to set fields before saving.
        """
        # Get the unit from the context we set up in get_context_data
        unit = get_object_or_404(PropertyUnit, pk=self.kwargs['unit_pk'])
        
        # Connect the review to the unit, author, and set its initial status
        form.instance.unit = unit
        form.instance.author = self.request.user
        form.instance.status = ReviewStatus.PENDING_CONTENT_REVIEW
        
        # The save() method on the Review model will handle the verification flag.
        # We need to save the object here to get its primary key (pk) for the redirect.
        self.object = form.save()
        
        # Let the parent class handle the final HTTP response (which will be a redirect)
        return super().form_valid(form)

    def get_success_url(self):
        """
        Returns the URL to redirect to after a successful submission.
        This is where we send the user to our "incentive" page.
        """
        return reverse_lazy('reviews:review_success', kwargs={'review_pk': self.object.pk})
    

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
    template_name = 'reviews/review_success.html'
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