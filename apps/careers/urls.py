# In apps/careers/urls.py
from django.urls import path
from .views import JobPostingListView, JobPostingDetailView

app_name = 'careers'

urlpatterns = [
    path('', JobPostingListView.as_view(), name='job_list'),
    path('<slug:slug>/', JobPostingDetailView.as_view(), name='job_detail'),
]