
import logging
import os
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.views import LoginView
from django.http import HttpResponseRedirect, HttpResponse
from django.urls import reverse
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from .forms import UploadFileForm
from .utils import extract_cv_data, summarize_jd, calculate_match_score, send_custom_email
from .models import Candidate

logger = logging.getLogger(__name__)

def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data.get('username')
            messages.success(request, f'Account created for {username}!')
            return redirect('recruitment:login')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = UserCreationForm()
    return render(request, 'recruitment/register.html', {'form': form})

class CustomLoginView(LoginView):
    def form_invalid(self, form):
        logger.info(f"Login failed: Invalid credentials")
        messages.error(self.request, 'Invalid username or password.')
        return super().form_invalid(form)

@login_required
def user_logout(request):
    logout(request)
    messages.success(request, 'You have been logged out.')
    return redirect('recruitment:login')

@login_required
def upload(request):
    if request.method == 'POST':
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            jd_file = request.FILES['jd_file']
            cv_files = request.FILES.getlist('cv_files')
            logger.debug(f"Processing JD: {jd_file.name}, CVs: {[cv.name for cv in cv_files]}")
            
            if len(cv_files) > 80:
                messages.error(request, 'You can upload up to 80 CVs at a time.')
                return render(request, 'recruitment/upload.html', {'form': form})
            
            jd_result = summarize_jd(jd_file)
            if not jd_result or 'summary' not in jd_result or not jd_result.get('summary'):
                logger.warning("Empty JD summary")
                messages.error(request, 'Failed to process job description.')
                return render(request, 'recruitment/upload.html', {'form': form})
            
            candidates = []
            failed_cvs = []
            fs = FileSystemStorage(location=os.path.join(settings.MEDIA_ROOT, 'cvs'))
            for cv_file in cv_files:
                try:
                    # Save CV file
                    cv_filename = fs.save(cv_file.name, cv_file)
                    cv_path = os.path.join(settings.MEDIA_ROOT, 'cvs', cv_filename)
                    
                    with open(cv_path, 'rb') as cv_f:
                        cv_data = extract_cv_data(cv_f)
                    if not cv_data or not cv_data.get('email') or not cv_data.get('name'):
                        logger.warning(f"No valid data extracted from CV: {cv_file.name}")
                        failed_cvs.append(cv_file.name)
                        fs.delete(cv_filename)
                        continue
                    
                    match_score = calculate_match_score(cv_data, jd_result)
                    email = cv_data.get('email')
                    name = cv_data.get('name', 'Unknown')
                    
                    # Check for existing candidate
                    candidate, created = Candidate.objects.get_or_create(
                        email=email,
                        defaults={
                            'name': name,
                            'match_score': match_score,
                            'cv_data': cv_data,
                            'job_title': jd_result.get('job_title', 'Unknown'),
                            'cv_file': f'cvs/{cv_filename}'
                        }
                    )
                    if not created:
                        # Update existing candidate
                        candidate.name = name
                        candidate.match_score = match_score
                        candidate.cv_data = cv_data
                        candidate.job_title = jd_result.get('job_title', 'Unknown')
                        candidate.cv_file = f'cvs/{cv_filename}'
                        candidate.save()
                        logger.info(f"Updated existing candidate: {email}")
                    else:
                        logger.info(f"Created new candidate: {email}")
                    
                    candidates.append({
                        'name': candidate.name,
                        'email': candidate.email,
                        'match_score': candidate.match_score,
                        'cv_data': candidate.cv_data,
                        'cv_file': candidate.cv_file
                    })
                except Exception as e:
                    logger.error(f"Error processing CV {cv_file.name}: {str(e)}")
                    failed_cvs.append(cv_file.name)
                    fs.delete(cv_filename) if os.path.exists(cv_path) else None
            
            if failed_cvs:
                messages.warning(request, f"Failed to process {len(failed_cvs)} CV(s): {', '.join(failed_cvs)}. Check logs for details.")
            if not candidates:
                messages.error(request, 'No valid CVs processed. All CVs failed due to missing email, name, or unreadable content.')
                return render(request, 'recruitment/upload.html', {'form': form})
            
            request.session['candidates'] = candidates
            request.session['job_title'] = jd_result.get('job_title', 'Unknown')
            return HttpResponseRedirect(reverse('recruitment:shortlisted_candidates'))
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = UploadFileForm()
    return render(request, 'recruitment/upload.html', {'form': form})

@login_required
def shortlisted_candidates(request):
    candidates = request.session.get('candidates', [])
    job_title = request.session.get('job_title', 'Unknown')
    if not candidates:
        messages.error(request, 'No candidates found. Please upload files first.')
        return redirect('recruitment:upload')
    
    # Filter candidates with match_score >= 70
    shortlisted_candidates = [c for c in candidates if c['match_score'] >= 70]
    
    if not shortlisted_candidates:
        messages.warning(request, 'No candidates met the 70% match score threshold.')
        logger.info("No candidates shortlisted")
    
    return render(request, 'recruitment/shortlisted.html', {
        'candidates': shortlisted_candidates,
        'job_title': job_title,
    })

@login_required
def send_candidate_email(request):
    if request.method == 'POST':
        candidate_email = request.POST.get('candidate_email')
        candidate_name = request.POST.get('candidate_name', 'Candidate')
        subject = request.POST.get('subject')
        message = request.POST.get('message')
        
        logger.debug(f"Sending email to {candidate_email} with subject: {subject}")
        try:
            success = send_custom_email(
                candidate_email=candidate_email,
                candidate_name=candidate_name,
                subject=subject,
                message=message,
            )
            if success:
                messages.success(request, f'Email successfully sent to {candidate_email}')
            else:
                messages.error(request, f'Failed to send email to {candidate_email}: No emails sent')
        except Exception as e:
            messages.error(request, f'Failed to send email to {candidate_email}: {str(e)}')
            logger.error(f"View-level error sending email to {candidate_email}: {str(e)}")
        
        return redirect('recruitment:shortlisted_candidates')
    
    candidates = request.session.get('candidates', [])
    logger.debug(f"Candidates in session: {candidates}")
    return render(request, 'recruitment/send_email.html', {'candidates': candidates})

@login_required
def download_cv(request, cv_path):
    file_path = os.path.join(settings.MEDIA_ROOT, cv_path)
    if os.path.exists(file_path):
        with open(file_path, 'rb') as fh:
            response = HttpResponse(fh.read(), content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename={os.path.basename(file_path)}'
            return response
    logger.error(f"CV file not found: {file_path}")
    messages.error(request, 'CV file not found.')
    return redirect('recruitment:shortlisted_candidates')
