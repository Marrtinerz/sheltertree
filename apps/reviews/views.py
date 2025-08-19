from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.db.models import Avg, Count, Sum, OuterRef, Subquery, Case, When, IntegerField
from django.views.generic import TemplateView
from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector
from .models import Property, PropertyUnit, Review, PropertyStatus, ReviewStatus, Vote
from .forms import PropertyForm, PropertyUnitForm, ReviewForm, PropertySearchForm
from django.db.models import Q, F
from django.template.loader import render_to_string
from django.http import HttpResponse
from collections import defaultdict
from django.contrib.auth.mixins import LoginRequiredMixin

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
    Performs a hybrid search.
    1. A high-relevance, ranked search using PostgreSQL FTS.
    2. A broad, "catch-all" substring search using Q objects.
    
    The results are combined, with ranked results appearing first.
    """
    if not query_string or len(query_string) < 3:
        return []

    # === Method 1: High-Relevance FTS Search ===
    # This search finds whole words and ranks them.
    query = SearchQuery(query_string, search_type='websearch')
    
    fts_results = Property.objects.annotate(
        rank=SearchRank(F('search_vector'), query)
    ).filter(
        search_vector=query,
        status=PropertyStatus.APPROVED
    ).order_by('-rank')
    
    # Get the IDs of the high-relevance results to avoid duplicates
    fts_result_ids = {p.id for p in fts_results}

    # === Method 2: Broad Substring Search (`icontains`) ===
    # This search is our "catch-all" for partial matches.
    substring_query = Q(name__icontains=query_string) | \
                      Q(address__icontains=query_string) | \
                      Q(city__icontains=query_string) | \
                      Q(state__name__icontains=query_string) | \
                      Q(country__name__icontains=query_string)

    substring_results = Property.objects.filter(
        substring_query,
        status=PropertyStatus.APPROVED
    ).exclude(
        id__in=fts_result_ids # Exclude results we already found
    ).distinct()

    # === Combine the Results ===
    # Convert querysets to lists and combine them. The ranked FTS results are first.
    final_results = list(fts_results) + list(substring_results)
    
    return final_results


class SearchView(TemplateView):
    """
    Handles the main search page request after a form submission.
    """
    template_name = 'reviews/search_results.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        form = PropertySearchForm(self.request.GET or None)
        
        if form.is_valid():
            query = form.cleaned_data.get('q')
            context['results'] = find_properties(query)
        
        context['form'] = form
        context['query'] = self.request.GET.get('q', '')
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
    """
    Displays a list of all publicly visible properties.
    KEY CHANGE: We override get_queryset to only show APPROVED properties.
    """
    model = Property
    template_name = 'reviews/property_list.html'
    context_object_name = 'properties'
    paginate_by = 12

    def get_queryset(self):
        """
        Only return properties that have been approved by an admin.
        This is a critical security and data quality measure.
        """
        return Property.objects.filter(status=PropertyStatus.APPROVED).order_by('-created_at')


class PropertyDetailView(DetailView):
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

@login_required
def add_property(request):
    """
    View for Stage 1: Submitting a new property for admin approval.
    """
    if request.method == 'POST':
        form = PropertyForm(request.POST)
        if form.is_valid():
            property_instance = form.save(commit=False)
            property_instance.status = PropertyStatus.PENDING_APPROVAL
            property_instance.added_by = request.user
            property_instance.save()
            messages.success(request, _("Property submitted for review! Now, please add your unit and review."))
            return redirect('reviews:add-property-success', pk=property_instance.pk)
    else:
        form = PropertyForm()
    return render(request, 'reviews/add_property.html', {'form': form})


@login_required
def add_property_success(request, pk):
    """
    A success page shown after a property is submitted.
    It guides the user to Stage 2: adding their unit and review.
    """
    property_instance = get_object_or_404(Property, pk=pk)
    return render(request, 'reviews/add_property_success.html', {'property': property_instance})


@login_required
def add_unit_and_review(request, property_pk):
    """
    View for Flow 2: Adding a new unit AND a review for a given property.
    Now redirects to the review success page.
    """
    property_instance = get_object_or_404(Property, pk=property_pk)

    if request.method == 'POST':
        unit_form = PropertyUnitForm(request.POST)
        review_form = ReviewForm(request.POST)

        if unit_form.is_valid() and review_form.is_valid():
            # Save the unit first
            unit = unit_form.save(commit=False)
            unit.property = property_instance
            unit.save()

            # Now save the review, linking it to the new unit and the user
            review = review_form.save(commit=False)
            review.unit = unit
            review.author = request.user
            
            # Set review status based on parent property's status
            if property_instance.status == PropertyStatus.APPROVED:
                review.status = ReviewStatus.PENDING_CONTENT_REVIEW
            else:
                review.status = ReviewStatus.PENDING_PROPERTY_APPROVAL
            
            # The save() method on the Review model will automatically handle
            # setting the is_author_phone_verified flag.
            review.save()

            # --- THE CRITICAL CHANGE ---
            # Instead of a generic message, we redirect to the success page.
            # The success page will handle displaying the congratulations and the verification incentive.
            return redirect('reviews:review_success', review_pk=review.pk)

    else:
        unit_form = PropertyUnitForm()
        review_form = ReviewForm()

    return render(request, 'reviews/add_unit_and_review.html', {
        'property': property_instance,
        'unit_form': unit_form,
        'review_form': review_form
    })


@login_required
def add_review_to_unit(request, unit_pk):
    """
    View for Flow 3: Adding a review to an EXISTING unit.
    Now redirects to the review success page.
    """
    unit_instance = get_object_or_404(PropertyUnit, pk=unit_pk)
    property_instance = unit_instance.property

    if request.method == 'POST':
        review_form = ReviewForm(request.POST)
        if review_form.is_valid():
            review = review_form.save(commit=False)
            review.unit = unit_instance
            review.author = request.user
            review.status = ReviewStatus.PENDING_CONTENT_REVIEW
            
            # The save() method on the Review model will automatically handle
            # setting the is_author_phone_verified flag.
            review.save()

            # --- THE CRITICAL CHANGE ---
            # Redirect to the success page with the new review's PK.
            # This triggers the "Get Verified" incentive flow.
            return redirect('reviews:review_success', review_pk=review.pk)

    else:
        review_form = ReviewForm()

    return render(request, 'reviews/add_review_to_unit.html', {
        'unit': unit_instance,
        'property': property_instance,
        'review_form': review_form
    })
    

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



