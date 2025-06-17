
from django.db import models
from django.contrib.auth.models import User

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=50, default='HR')

    def __str__(self):
        return f"{self.user.username} - {self.role}"

class Candidate(models.Model):
    name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    cv_data = models.JSONField(default=dict)
    match_score = models.FloatField(default=0.0)
    job_title = models.CharField(max_length=255, default='Unknown')
    cv_file = models.CharField(max_length=255, blank=True)  

    @property
    def is_shortlisted(self):
        """Return True if candidate's match_score is 70 or higher."""
        return self.match_score >= 70

    def __str__(self):
        return f"{self.name} ({self.email})"

