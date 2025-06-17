from django.urls import path
from . import views
from .views import CustomLoginView

app_name = 'recruitment'
urlpatterns = [
    path('', views.upload, name='upload'),
    path('register/', views.register, name='register'),
    path('login/', CustomLoginView.as_view(template_name='recruitment/login.html'), name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('shortlisted/', views.shortlisted_candidates, name='shortlisted_candidates'),
    path('send-email/', views.send_candidate_email, name='send_candidate_email'),
    path('download-cv/<path:cv_path>/', views.download_cv, name='download_cv'),
]