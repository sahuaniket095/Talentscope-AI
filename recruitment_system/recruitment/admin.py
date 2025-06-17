
from django.contrib import admin
from django.utils.html import format_html
from .models import Candidate

@admin.register(Candidate)
class CandidateAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'match_score', 'job_title', 'cv_download_link']
    readonly_fields = ['match_score','cv_file']
    list_filter = ['job_title']
    search_fields = ['name', 'email']

    def cv_download_link(self, obj):
        """Provide a download link for the CV file."""
        if obj.cv_file:
            return format_html('<a href="/media/{}" class="text-blue-600 hover:underline" download>Download CV</a>', obj.cv_file)
        return 'No CV file'
    cv_download_link.short_description = 'CV File'

