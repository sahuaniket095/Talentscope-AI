
import os
import PyPDF2
from google.generativeai import GenerativeModel, list_models, configure
from google.api_core.exceptions import ResourceExhausted, NotFound
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
import logging
import re
import json
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# Configure logging
logger = logging.getLogger(__name__)

# Configure Google API key once
configure(api_key=settings.GOOGLE_API_KEY)

# Common stop words to ignore in matching
STOP_WORDS = {
    'a', 'an', 'and', 'are', 'as', 'at', 'be', 'by', 'for', 'from', 'has', 'he',
    'in', 'is', 'it', 'its', 'of', 'on', 'that', 'the', 'to', 'was', 'were',
    'will', 'with', 'skills', 'experience', 'education', 'certifications'
}

# Keyword lists for matching
JD_SKILLS = [
    'siem', 'firewalls', 'intrusion detection', 'network security', 'encryption',
    'penetration testing', 'vulnerability assessment', 'ethical hacking', 'risk assessment',
    'security monitoring', 'cryptography', 'security analytics'
]
RELATED_SKILLS = [
    'aws', 'python', 'java', 'docker', 'kubernetes', 'cloud security', 'security tools',
    'sql', 'networking', 'linux', 'windows', 'scripting'
]
CYBERSECURITY_ROLES = [
    'cybersecurity', 'security analyst', 'penetration tester', 'ethical hacker',
    'security engineer', 'information security', 'network security'
]
TECHNICAL_ROLES = [
    'software engineer', 'data scientist', 'product manager', 'developer',
    'systems administrator', 'network engineer'
]

class QuotaExceededError(Exception):
    pass

retry_on_quota_exhausted = retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    retry=retry_if_exception_type(QuotaExceededError)
)

def validate_api_key():
    """Validate Google API key configuration."""
    try:
        models = list_models()
        logger.debug(f"Available models: {[m.name for m in models if 'generateContent' in m.supported_generation_methods]}")
        return True
    except Exception as e:
        logger.error(f"Invalid Google API key or connectivity issue: {str(e)}")
        return False

def get_available_model():
    """Fetch an available Gemini model for content generation."""
    try:
        models = list_models()
        preferred_model = 'gemini-2.0-flash'  # Set to desired model
        fallback_model = 'gemini-1.5-flash'   # Fallback if gemini-2.0-flash is unavailable
        available_models = [m.name.split('/')[-1] for m in models if 'generateContent' in m.supported_generation_methods]
        logger.debug(f"Available models: {available_models}")
        
        if preferred_model in available_models:
            logger.debug(f"Selected model: {preferred_model}")
            return preferred_model
        
        logger.warning(f"Preferred model {preferred_model} not available. Falling back to {fallback_model}")
        if fallback_model in available_models:
            logger.debug(f"Selected fallback model: {fallback_model}")
            return fallback_model
        
        if available_models:
            model = available_models[0]
            logger.debug(f"Fallback to first available model: {model}")
            return model
        
        logger.error("No models supporting generateContent found")
        return None
    except Exception as e:
        logger.error(f"Error listing models: {str(e)}")
        return None

def clean_json_response(text):
    """Remove Markdown code block wrappers and fix JSON syntax issues, handling invalid escapes and truncated JSON."""
    text = text.strip()
    # Remove markdown wrappers
    if text.startswith("```json") and text.endswith("```"):
        text = text[7:-3].strip()
    elif text.startswith("```") and text.endswith("```"):
        text = text[3:-3].strip()
    
    # Fix common JSON syntax issues
    text = re.sub(r'[\.,;]\s*}$', '}', text)  # Remove trailing commas
    text = re.sub(r',(\s*[}\]])', r'\1', text)  # Remove trailing commas before closing brackets
    text = text.replace("’", "'").replace("‘", "'").replace("“", "\"").replace("”", "\"")  # Normalize quotes
    
    # Fix invalid escape sequences
    text = re.sub(r'\\{2,}\'', r'\'', text)  # Replace multiple backslashes before single quote
    text = re.sub(r'\\{2,}\"', r'\"', text)  # Replace multiple backslashes before double quote
    text = text.replace("Bachelor\\\'s", "Bachelor\'s")  # Specific fix for common issue
    text = text.replace("\\\'", "\'")  # Fix escaped single quotes
    text = re.sub(r'\\+', r'\\', text)  # Reduce multiple backslashes to single
    
    # Handle truncated JSON by ensuring proper closure
    if not text.endswith('}'):
        text = text.rsplit(',', 1)[0] + '}' if ',' in text else text + '}'
    
    try:
        parsed = json.loads(text)
        if 'summary' in parsed and isinstance(parsed['summary'], dict):
            logger.warning(f"Summary is a dictionary: {parsed['summary']}. Converting to string.")
            parsed['summary'] = '; '.join([f"{k}: {v}" for k, v in parsed['summary'].items()])
        cleaned = json.dumps(parsed, ensure_ascii=False)
        logger.debug(f"Cleaned JSON response: {cleaned[:100]}...")
        return cleaned
    except json.JSONDecodeError as e:
        logger.warning(f"Initial JSON parse failed: {str(e)}. Attempting manual cleanup.")
        # Manual cleanup for special characters
        def escape_special_chars(match):
            content = match.group(1)
            content = (
                content.replace('\\', '\\\\')
                       .replace('"', '\\"')
                       .replace("'", "\\'")
                       .replace('\n', '\\n')
                       .replace('\r', '\\r')
                       .replace('\t', '\\t')
            )
            return f'"{content}"'
        text = re.sub(r'"([^"]*)"', escape_special_chars, text)
        # Fix unclosed strings or objects
        text = re.sub(r'("[^"]*?)\s*$', r'\1"', text)  # Close unclosed strings
        if not text.endswith('}'):
            text += '}'
        try:
            parsed = json.loads(text)
            if 'summary' in parsed and isinstance(parsed['summary'], dict):
                parsed['summary'] = '; '.join([f"{k}: {v}" for k, v in parsed['summary'].items()])
            cleaned = json.dumps(parsed, ensure_ascii=False)
            logger.debug(f"Manually cleaned JSON: {cleaned[:100]}...")
            return cleaned
        except json.JSONDecodeError as e:
            logger.error(f"Manual JSON cleanup failed: {str(e)}. Raw text: {text[:200]}...")
            # Fallback: Extract partial JSON
            try:
                # Extract job_title and partial summary
                match = re.search(r'\{[\s\S]*?"job_title":\s*"([^"]+)"[\s\S]*?"summary":\s*"([^"]+)', text)
                if match:
                    partial = {
                        "job_title": match.group(1),
                        "summary": match.group(2)
                    }
                    cleaned = json.dumps(partial, ensure_ascii=False)
                    logger.debug(f"Extracted partial JSON: {cleaned[:100]}...")
                    return cleaned
                else:
                    logger.error("Could not extract partial JSON")
                    return None
            except Exception as e:
                logger.error(f"Partial JSON extraction failed: {str(e)}")
                return None

@retry_on_quota_exhausted
def make_api_call(model, prompt):
    """Make an API call with retry logic for quota errors."""
    try:
        response = model.generate_content(prompt)
        return response
    except ResourceExhausted as e:
        logger.error(f"API quota exceeded: {str(e)}")
        raise QuotaExceededError(f"Quota exceeded: {str(e)}")
    except NotFound as e:
        logger.error(f"Model not found: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"API call failed: {str(e)}")
        raise

def extract_cv_data(cv_file):
    """Extract name, email, skills, experience, education, certifications, and summary from a CV PDF."""
    try:
        pdf_reader = PyPDF2.PdfReader(cv_file)
        text = ""
        for page in pdf_reader.pages:
            extracted = page.extract_text() or ""
            text += extracted + "\n"
        logger.debug(f"Extracted CV text (first 50 chars, len={len(text)}): {text[:50]}...")
        
        if not text.strip():
            logger.warning("No text extracted from CV. Possible scanned PDF or empty content.")
            return {}
        
        # Relaxed email regex to capture more formats
        email_match = re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text, re.IGNORECASE)
        candidate_email = email_match.group(0) if email_match else None
        if not candidate_email:
            logger.warning("No email address found in CV text.")
        
        if not validate_api_key():
            logger.error("API key validation failed")
            return {}
        
        model_name = get_available_model()
        if not model_name:
            logger.error("No available model found")
            return {}
        
        model = GenerativeModel(model_name)
        prompt = (
            "Extract the following from this CV in a structured format: "
            "Name, Email, Skills, Experience, Education, Certifications, and a Summary. "
            "The Summary must be a single string combining all key skills, experience, education, and certifications (e.g., 'Skills: Python, Cybersecurity; Experience: 3 years; Education: Bachelor\\'s in IT; Certifications: CEH'). "
            "Include all cybersecurity-related skills (e.g., penetration testing, SIEM, firewalls, ethical hacking) and certifications (e.g., CEH, CISSP) explicitly in both Skills and Summary. "
            "If no email is found, return an empty string for Email. "
            "Ensure the Summary is a string, not a nested object. "
            "Return as a valid JSON object without markdown wrappers. Use double quotes for all string values and properly escape single quotes (e.g., Bachelor\\'s). "
            "Example: "
            "{\"name\": \"John Doe\", \"email\": \"user@example.com\", \"skills\": [\"Python\", \"Cybersecurity\", \"Penetration Testing\"], \"experience\": [\"3 years as a developer\"], \"education\": [\"Bachelor\\'s in CS\"], \"certifications\": [\"CEH\"], \"summary\": \"Skills: Python, Cybersecurity, Penetration Testing; Experience: 3 years; Education: Bachelor\\'s in CS; Certifications: CEH\"} "
            f"CV: {text[:4000]}"
        )
        try:
            response = make_api_call(model, prompt)
            result = response.text.strip() if response.text else ''
            logger.debug(f"Raw CV API response: {result[:200]}...")
        except QuotaExceededError as e:
            logger.error(f"Failed to process CV due to API quota limit: {str(e)}")
            return {}
        except Exception as e:
            logger.error(f"Gemini API error in CV extraction: {str(e)}")
            return {}
        
        try:
            cleaned_result = clean_json_response(result)
            if cleaned_result is None:
                logger.error("Failed to clean JSON response")
                return {}
            try:
                data = json.loads(cleaned_result)
                logger.debug(f"Extracted CV data: {data}")
            except json.JSONDecodeError as e:
                logger.error(f"Cleaned JSON is invalid: {str(e)}. Cleaned response: {cleaned_result[:200]}...")
                logger.debug(f"Full raw CV response: {result[:200]}...")
                return {}
            if not data.get('email') and candidate_email:
                data['email'] = candidate_email
            if not data.get('email'):
                logger.warning("No email extracted from CV or API response")
                return {}
            if 'summary' in data and not isinstance(data['summary'], str):
                logger.warning(f"CV summary is not a string: {data['summary']}. Converting to string.")
                data['summary'] = str(data['summary'])
            if not data.get('name'):
                logger.warning("No name extracted from CV")
                return {}
            return data
        except Exception as e:
            logger.error(f"Error processing cleaned JSON: {str(e)}")
            return {}
    except Exception as e:
        logger.error(f"Error extracting CV data: {str(e)}")
        return {}

def summarize_jd(jd_file):
    """Summarize a job description PDF into key requirements and a job title."""
    try:
        pdf_reader = PyPDF2.PdfReader(jd_file)
        text = ""
        for page in pdf_reader.pages:
            extracted = page.extract_text() or ""
            text += ' ' + extracted + '\n'
        logger.debug(f"Extracted JD text (first 50 chars, len={len(text)}): {text[:50]}...")
        
        if not text.strip():
            logger.debug("No text extracted from JD")
            return {}
        
        if not validate_api_key():
            logger.error("API key validation failed")
            return {}
        
        model_name = get_available_model()
        if not model_name:
            logger.error(f"No available model found")
            return {}
        
        model = GenerativeModel(model_name)
        prompt = (
            "Summarize this job description into a concise string of key requirements and extract the job title. "
            "Include all skills (e.g., SIEM, firewalls, intrusion detection, ethical hacking), qualifications, certifications (e.g., CEH, CISSP), and responsibilities explicitly in the summary. "
            "Ensure the Summary is a single string, not a nested object. "
            "Return as a valid JSON object without markdown wrappers. Use double quotes for all string values and properly escape single quotes (e.g., Bachelor\\'s). "
            "Example: "
            "{\"job_title\": \"Cybersecurity Analyst\", \"summary\": \"Skills: SIEM, firewalls, intrusion detection, network security; Experience: Monitor networks, analyze incidents; Qualifications: Bachelor\\'s in Cybersecurity; Certifications: CEH, CISSP\"} "
            f"Job description: {text[:4000]}"
        )
        try:
            response = make_api_call(model, prompt)
            result = response.text.strip() if response.text else None
            logger.debug(f"Raw JD API response: {result[:100]}...")
        except Exception as e:
            logger.error(f"Gemini API error in JD summarization: {str(e)}")
            return {}
        
        try:
            cleaned_result = clean_json_response(result)
            if cleaned_result is None:
                logger.error("Failed to clean JD JSON response. Raw response: {result[:200]}...")
                return {}
            try:
                data = json.loads(cleaned_result)
                logger.debug(f"Extracted JD data: {data}")
            except json.JSONDecodeError as e:
                logger.error(f"Cleaned JSON is invalid: {cleaned_result}")
                logger.debug(f"Full raw JD response: {result}")
                return {}
            if 'summary' in data and not isinstance(data['summary'], str):
                logger.warning(f"JD summary is not a string: {data['summary']}. Converting to string.")
                data['summary'] = str(data['summary'])
            return data
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON JD response: {str(e)}. Raw response: {result}")
            return {}
    except Exception as e:
        logger.error(f"Error summarizing JD: {str(e)}")
        return {}

def calculate_match_score(cv_data, jd_data):
    """Calculate a match score between CV data and JD summary, scoring only the degree mentioned in JD."""
    try:
        if not isinstance(cv_data, dict) or not isinstance(jd_data, dict):
            logger.error("CV data or JD data is not a dictionary")
            return 0.0
        
        logger.debug(f"Raw CV data: {cv_data}")
        logger.debug(f"Raw JD data: {jd_data}")
        
        # Initialize score and max possible score
        score = 0.0
        max_score = 0.0
        
        # Parse JD summary to identify mandatory and optional requirements
        jd_summary = jd_data.get('summary', '').lower()
        mandatory_skills = [s for s in JD_SKILLS if s in jd_summary and 'required' in jd_summary]
        optional_skills = [s for s in RELATED_SKILLS if s in jd_summary]
        
        # Extract required degree from JD summary
        degree_match = re.search(r"(?:bachelor\'s|master\'s|b\.s\.|m\.s\.)\s*(?:in)?\s*([\w\s]+)", jd_summary)
        required_degree = degree_match.group(1).strip().lower() if degree_match else None
        logger.debug(f"Required degree from JD: {required_degree}")
        
        # Points for mandatory skills (25 each)
        cv_skills = [s.lower() for s in cv_data.get('skills', [])]
        for skill in mandatory_skills:
            max_score += 25.0
            if any(skill in cv_skill for cv_skill in cv_skills):
                score += 25.0
                logger.debug(f"Matched mandatory skill: {skill}, +25 points")
        
        # Points for optional skills (7 each)
        for skill in optional_skills:
            max_score += 7.0
            if any(skill in cv_skill for cv_skill in cv_skills):
                score += 7.0
                logger.debug(f"Matched optional skill: {skill}, +7 points")
        
        # Points for experience (10 if matches JD years, 5 for roles)
        cv_experience = [e.lower() for e in cv_data.get('experience', [])]
        years_required = re.search(r'(\d+)\s*(?:year|years)', jd_summary)
        years_required = int(years_required.group(1)) if years_required else 0
        if years_required:
            max_score += 10.0
            for exp in cv_experience:
                years_match = re.search(r'(\d+)\s*(?:year|years)', exp)
                if years_match and int(years_match.group(1)) >= years_required:
                    score += 10.0
                    logger.debug(f"Matched experience years: {years_match.group(0)}, +10 points")
                    break
                if any(role in exp for role in CYBERSECURITY_ROLES):
                    score += 5.0
                    logger.debug(f"Matched cybersecurity role: {exp}, +5 points")
        
        # Points for education (10 if matches JD degree, 0 otherwise)
        if required_degree:
            max_score += 10.0
            cv_education = [e.lower() for e in cv_data.get('education', [])]
            for edu in cv_education:
                if required_degree in edu:
                    score += 10.0
                    logger.debug(f"Matched required degree: {edu}, +10 points")
                    break
        
        # Bonus for exceeding skill requirements
        if len(cv_skills) > len(mandatory_skills) + len(optional_skills):
            bonus = 10.0
            score += bonus
            max_score += bonus
            logger.debug(f"Bonus for extra skills: +{bonus} points")
        
        # Normalize score
        if max_score > 0:
            final_score = (score / max_score) * 100
        else:
            final_score = 0.0
            logger.warning("Max score is 0, no JD requirements identified")
        
        logger.debug(f"Final score: {final_score} (earned {score}/{max_score})")
        return round(final_score, 2)
    except Exception as e:
        logger.error(f"Error calculating match score: {str(e)}")
        return 0.0


def send_custom_email(candidate_email, candidate_name, subject, message):
    try:
        full_message = render_to_string('emails/custom_email.txt', {
            'candidate_name': candidate_name,
            'message': message,
        })
        logger.debug(f"Rendered email content for {candidate_email}: {full_message[:100]}...")
        result = send_mail(
            subject=subject,
            message=full_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[candidate_email],
            fail_silently=False,
        )
        if result == 1:
            logger.info(f"Custom email successfully sent to {candidate_email}")
            return True
        else:
            logger.error(f"Failed to send custom email to {candidate_email}: No emails sent")
            return False
    except Exception as e:
        logger.error(f"Failed to send custom email to {candidate_email}: {str(e)}")
        raise