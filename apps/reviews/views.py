from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.db.models import Avg, Count
from django.views.generic import TemplateView
from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector
from .models import Property, PropertyUnit, Review, PropertyStatus, ReviewStatus
from .forms import PropertyForm, PropertyUnitForm, ReviewForm, PropertySearchForm
from django.db.models import Q, F

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
        This method is extended to add the aggregated review summary to the context.
        """
        # First, get the base context from the superclass
        context = super().get_context_data(**kwargs)
        property = self.get_object()

        # --- "At a Glance" Summary Logic ---
        # Perform a single, efficient database query to get all averages and counts.
        summary_data = Review.objects.filter(
            unit__property=property,
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

        # Calculate a single overall average score from all category averages
        if summary_data['total_reviews'] > 0:
            averages = [
                v for v in [
                    summary_data['average_security'], summary_data['average_electricity'],
                    summary_data['average_water'], summary_data['average_management'],
                    summary_data['average_roads'], summary_data['average_mobile']
                ] if v is not None
            ]
            summary_data['overall_average'] = sum(averages) / len(averages) if averages else 0
        else:
            summary_data['overall_average'] = 0

        context['summary'] = summary_data
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
            return redirect('add-property-success', pk=property_instance.pk)
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
    """
    property_instance = get_object_or_404(Property, pk=property_pk)
    if request.method == 'POST':
        unit_form = PropertyUnitForm(request.POST)
        review_form = ReviewForm(request.POST)
        if unit_form.is_valid() and review_form.is_valid():
            unit = unit_form.save(commit=False)
            unit.property = property_instance
            unit.save()
            review = review_form.save(commit=False)
            review.unit = unit
            review.author = request.user
            if property_instance.status == PropertyStatus.APPROVED:
                review.status = ReviewStatus.PENDING_CONTENT_REVIEW
            else:
                review.status = ReviewStatus.PENDING_PROPERTY_APPROVAL
            review.save()
            messages.success(request, _("Thank you! Your review has been submitted and will be published after moderation."))
            return redirect('property-detail', pk=property_instance.pk)
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
    """
    unit_instance = get_object_or_404(PropertyUnit, pk=unit_pk)
    property_instance = unit_instance.property

    if request.method == 'POST':
        review_form = ReviewForm(request.POST)
        if review_form.is_valid():
            review = review_form.save(commit=False)
            review.unit = unit_instance
            review.author = request.user
            # The parent property must be approved to reach this view.
            review.status = ReviewStatus.PENDING_CONTENT_REVIEW
            review.save()
            messages.success(request, _("Thank you! Your review has been submitted and will be published after moderation."))
            return redirect('property-detail', pk=property_instance.pk)
    else:
        review_form = ReviewForm()

    return render(request, 'reviews/add_review_to_unit.html', {
        'unit': unit_instance,
        'property': property_instance,
        'review_form': review_form
    })