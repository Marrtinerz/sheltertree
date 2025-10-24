# In apps/careers/views.py
from django.views.generic import ListView, DetailView
from .models import JobPosting

class JobPostingListView(ListView):
    model = JobPosting
    template_name = 'careers/job_posting_list.html'
    context_object_name = 'job_postings'

    def get_queryset(self):
        # It's non-negotiable that we only show active postings.
        return JobPosting.objects.filter(is_active=True)

class JobPostingDetailView(DetailView):
    model = JobPosting
    template_name = 'careers/job_posting_detail.html'
    context_object_name = 'job'

    def get_queryset(self):
        # Also filter by active here to prevent access to direct links of inactive jobs.
        return JobPosting.objects.filter(is_active=True)