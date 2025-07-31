from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, TemplateView
from django.contrib.auth.decorators import login_required
from django.utils.translation import gettext_lazy as _
from .models import Property, PropertyUnit, Review, PropertyStatus, ReviewStatus
from .forms import PropertyForm, PropertyUnitForm, ReviewForm

# --- READ-ONLY VIEWS (for the public) ---

class PropertyListView(ListView):
    """
    Displays a list of all publicly visible properties.
    KEY CHANGE: We override get_queryset to only show APPROVED properties.
    """
    model = Property
    template_name = 'reviews/property_list.html'
    context_object_name = 'properties'
    paginate_by = 10

    def get_queryset(self):
        """
        Only return properties that have been approved by an admin.
        This is a critical security and data quality measure.
        """
        return Property.objects.filter(status=PropertyStatus.APPROVED).order_by('-created_at')


class PropertyDetailView(DetailView):
    """
    Displays the details of a single publicly visible property and its reviews.
    KEY CHANGE: A user can only view a property if it is APPROVED.
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
        Add the approved reviews to the context.
        """
        context = super().get_context_data(**kwargs)
        # Get the property object
        property = self.get_object()
        # Filter reviews to only show those that are approved
        context['approved_reviews'] = Review.objects.filter(
            unit__property=property,
            status=ReviewStatus.APPROVED
        )
        return context


# --- WRITE VIEWS (for logged-in users) ---

@login_required
def add_property(request):
    """
    View for Stage 1: Submitting a new property for admin approval.
    """
    if request.method == 'POST':
        form = PropertyForm(request.POST)
        if form.is_valid():
            property_instance = form.save(commit=False)
            # Set the initial status to PENDING_APPROVAL
            property_instance.status = PropertyStatus.PENDING_APPROVAL
            property_instance.added_by = request.user
            property_instance.save()
            # Redirect to the success page, passing the new property's ID
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
    # Get the property that was just created to pass to the template
    property_instance = get_object_or_404(Property, pk=pk)
    return render(request, 'reviews/add_property_success.html', {'property': property_instance})


@login_required
def add_unit_and_review(request, property_pk):
    """
    View for Stage 2: Adding a specific unit and a review for a given property.
    The property could have just been added, or it could be an existing, approved one.
    """
    property_instance = get_object_or_404(Property, pk=property_pk)
    
    if request.method == 'POST':
        unit_form = PropertyUnitForm(request.POST)
        review_form = ReviewForm(request.POST)
        
        if unit_form.is_valid() and review_form.is_valid():
            # Create the unit linked to the parent property
            unit = unit_form.save(commit=False)
            unit.property = property_instance
            unit.save()
            
            # Create the review linked to the new unit and the logged-in user
            review = review_form.save(commit=False)
            review.unit = unit
            review.author = request.user
            
            # --- CRITICAL LOGIC ---
            # If the parent property is already approved, the review goes into the content
            # moderation queue. Otherwise, it waits for the property to be approved first.
            if property_instance.status == PropertyStatus.APPROVED:
                review.status = ReviewStatus.PENDING_CONTENT_REVIEW
            else:
                review.status = ReviewStatus.PENDING_PROPERTY_APPROVAL
            
            review.save()
            
            # For now, redirect to a generic success page or the property detail page
            # A dedicated "review submitted" page would be a good future enhancement.
            return redirect('property-detail', pk=property_instance.pk)
            
    else:
        unit_form = PropertyUnitForm()
        review_form = ReviewForm()

    return render(request, 'reviews/add_unit_and_review.html', {
        'property': property_instance,
        'unit_form': unit_form,
        'review_form': review_form
    })