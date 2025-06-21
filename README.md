# Talentscope AI

Talentscope AI is an AI-powered job application screening system that automates corporate recruitment processes.It uses artificial intelligence to summarize job descriptions (JDs), parse candidate CVs, match qualifications, shortlist candidates, and schedule interviews with personalized email notifications. By minimizing manual effort and errors, Talentscope AI streamlines talent acquisition with efficiency and precision.

## Project Overview

The recruitment process often involves manually reviewing numerous job descriptions (JDs) and CVs, which can be time-consuming and prone to human error. The goal of this project is to develop AI system that can automatically read and summarize job descriptions (JDs), match candidate qualifications with the JD, shortlist candidates, and send interview requests based on the match.

- **Job Description Summarizer**: Extracts and summarizes key elements from JDs, such as required skills, experience, and responsibilities.
- **CV Parsing and Relevance Scoring**: Extracts data from CVs (e.g., education, work experience, skills) using AI and calculates a match score against the summarized JD.
- **Shortlisting Candidates**: Automatically shortlists candidates exceeding a match threshold (e.g., 80%) for interviews.
- **Interview Scheduler**: Sends personalized interview requests to shortlisted candidates via email, including proposed dates, times, and interview format.

## Table of Contents
- [Features](#features)
- [Technologies](#technologies)
- [Installation](#installation)
  - [Windows](#windows)
  - [macOS](#macos)
- [Configuration](#configuration)
- [Usage](#usage)
- [Contributing](#contributing)
- [License](#license)
- [Contact](#contact)

## Features
- **JD Summarization**: AI-driven extraction of key JD requirements.
- **CV Parsing**: Extracts education, experience, and skills from CVs using `PyPDF2` and `google-generativeai`.
- **Candidate Matching**: Scores CVs against JDs to identify top matches.
- **Automated Shortlisting**: Shortlists candidates based on a customizable match threshold.
- **Email Notifications**: Sends personalized interview invitations via Gmail’s SMTP server.
- **Admin Dashboard**: Manages candidate profiles, CVs, and recruitment progress.
- **Responsive Design**: Accessible across devices with a clean interface.

## Technologies
- **Backend**: Django 4.2 (Python 3.10+)
- **Frontend**: HTML, Tailwind CSS
- **Database**: PostgreSQL (via `psycopg2-binary`, SQLite supported)
- **Environment Management**: `python-decouple`, `python-dotenv`
- **Email Service**: Gmail SMTP for notifications
- **AI Libraries**: `PyPDF2` (PDF parsing), `google-generativeai` (NLP tasks), `tenacity` (retry logic)
- **File Storage**: Django’s media storage for CV uploads

## Installation

### Prerequisites
- Python 3.10 or higher
- `pip` (Python package manager)
- Git
- PostgreSQL (installed and running)
- A Gmail account with an App Password for SMTP configuration
- A Google API key for `google-generativeai`

### Windows

1. **Clone the Repository**:
   ```powershell
   git clone https://github.com/sahuaniket095/Talentscope-AI.git
   cd Talentscope-AI\recruitment_system
   ```

2. **Create a Virtual Environment**:
   ```powershell
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   ```

3. **Install Dependencies**:
   - Ensure `requirements.txt` is in `recruitment_system` with:
     ```
     Django>=4.2
     python-decouple>=3.8
     PyPDF2>=3.0.1
     google-generativeai>=0.8.3
     tenacity>=8.2.3
     psycopg2-binary>=2.9.9
     ```
   - Run:
     ```powershell
     pip install -r requirements.txt
     ```

4. **Set Up Environment Variables**:
   - Create a `.env` file in `recruitment_system` (e.g., `Talentscope-AI\recruitment_system\.env`):
     ```env
     SECRET_KEY=your_django_secret_key
     DEBUG=True
     ALLOWED_HOSTS=127.0.0.1,localhost
     DB_NAME=your_db_name
     DB_USER=your_db_user
     DB_PASSWORD=your_db_password
     DB_HOST=localhost
     DB_PORT=5432
     EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
     EMAIL_HOST=smtp.gmail.com
     EMAIL_PORT=587
     EMAIL_USE_TLS=True
     EMAIL_HOST_USER=your_gmail_id
     EMAIL_HOST_PASSWORD=your_gmail_app_password
     DEFAULT_FROM_EMAIL=your_gmail_id
     GOOGLE_API_KEY=your_google_api_key
     ```
   - Replace `your_django_secret_key` with a secure key (e.g., use `django.utils.crypto.get_random_string()`).
   - Set `DB_NAME`, `DB_USER`, `DB_PASSWORD` for your PostgreSQL database.
   - Replace `your_gmail_app_password` with a Gmail App Password:
     - Log in to Gmail > Google Account > Security > 2-Step Verification > App Passwords.
     - Generate a password for “Mail”.
   - Replace `your_google_api_key` with your Google API key.
   - Save as UTF-8 in Notepad (File > Save As > Encoding: UTF-8).

5. **Set Up PostgreSQL**:
   - Create a database:
     ```sql
     CREATE DATABASE your_db_name;
     ```
   - Update `settings.py`:
     ```python
     from decouple import config
     DATABASES = {
         'default': {
             'ENGINE': 'django.db.backends.postgresql',
             'NAME': config('DB_NAME'),
             'USER': config('DB_USER'),
             'PASSWORD': config('DB_PASSWORD'),
             'HOST': config('DB_HOST'),
             'PORT': config('DB_PORT'),
         }
     }
     ```

6. **Apply Migrations**:
   ```powershell
   python manage.py makemigrations
   python manage.py migrate
   ```

7. **Create a Superuser**:
   ```powershell
   python manage.py createsuperuser
   ```

8. **Run the Development Server**:
   ```powershell
   python manage.py runserver
   ```
   Access at `http://127.0.0.1:8000`.

### macOS

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/sahuaniket095/Talentscope-AI.git
   cd Talentscope-AI/recruitment_system
   ```

2. **Create a Virtual Environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install Dependencies**:
   - Ensure `requirements.txt` is as above.
   - Run:
     ```bash
     pip install -r requirements.txt
     ```

4. **Set Up Environment Variables**:
   - Create a `.env` file in `recruitment_system`:
     ```env
     DEBUG=True
     ALLOWED_HOSTS=127.0.0.1,localhost
     DB_NAME=your_db_name
     DB_USER=your_db_user
     DB_PASSWORD=your_db_password
     DB_HOST=localhost
     DB_PORT=5432
     EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
     EMAIL_HOST=smtp.gmail.com
     EMAIL_PORT=587
     EMAIL_USE_TLS=True
     EMAIL_HOST_USER=your_gmail_id
     EMAIL_HOST_PASSWORD=your_gmail_app_password
     DEFAULT_FROM_EMAIL=your_gmail_id
     GOOGLE_API_KEY=your_google_api_key
     ```
   - Replace placeholders as described in the Windows section.
   - Save with UTF-8 encoding (e.g., in TextEdit, Format > Make Plain Text, save as `.env`).

5. **Set Up PostgreSQL**:
   - Create a database as above.
   - Update `settings.py` as shown in the Windows section.

6. **Apply Migrations**:
   ```bash
   python3 manage.py makemigrations
   python3 manage.py migrate
   ```

7. **Create a Superuser**:
   ```bash
   python3 manage.py createsuperuser
   ```

8. **Run the Development Server**:
   ```bash
   python3 manage.py runserver
   ```
   Access at `http://127.0.0.1:8000`.

## Configuration
- **Email Setup**:
   - If emails print to the console (e.g., `Content-Type: text/plain`), ensure `.env` has valid `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, and `DEFAULT_FROM_EMAIL`. Empty values trigger `console.EmailBackend`.
   - Update `.env` with:
     ```env
     EMAIL_HOST_USER=your_gmail_id
     EMAIL_HOST_PASSWORD=your_gmail_app_password
     DEFAULT_FROM_EMAIL=your_gmail_id
     ```
   - Test email sending in the Django shell:
     ```python
     from django.core.mail import send_mail
     try:
         result = send_mail(
             'Test Subject',
             'Test Message',
             'your_gmail_id',
             ['candidate_gmail_id'],
             fail_silently=False,
         )
         print(f"Emails sent: {result}")
     except Exception as e:
         print(f"Error: {str(e)}")
     ```
   - Verify the Gmail App Password (e.g., `phtk vbyx ncbw ymkg`) at Google Account > Security > 2-Step Verification > App Passwords.
   - Check Google Account > Security > Recent activity for blocks.
   - Test port 587:
     - **Windows**:
       ```powershell
       Test-NetConnection -ComputerName smtp.gmail.com -Port 587
       ```
     - **macOS**:
       ```bash
       nc -zv smtp.gmail.com 587
       ```

- **Media Storage**:
   - Configure in `settings.py`:
     ```python
     MEDIA_URL = '/media/'
     MEDIA_ROOT = BASE_DIR / 'media'
     ```

- **AI Components**:
   - Set `GOOGLE_API_KEY` in `.env` for `google-generativeai`.
   - Ensure `PyPDF2` supports your CV PDF formats.

- **Database**:
   - PostgreSQL is configured via `.env`. For SQLite, update `settings.py`:
     ```python
     DATABASES = {
         'default': {
             'ENGINE': 'django.db.backends.sqlite3',
             'NAME': BASE_DIR / 'db.sqlite3',
         }
     }
     ```

## Usage
1. **Admin Access**:
   - Log in at `http://127.0.0.1:8000/admin` to manage candidates, CVs, and JDs.

2. **JD and CV Processing**:
   - Upload JDs and CVs to trigger AI summarization and matching.

3. **Shortlisting**:
   - View shortlisted candidates at `http://127.0.0.1:8000/recruitment/shortlisted/`.

4. **Send Interview Emails**:
   - Use `http://127.0.0.1:8000/recruitment/send_email/` for automated interview invitations.

## Contact
Contact the maintainer, Aniket Sahu, at [sahuaniket095@gmail.com](mailto:sahuaniket095@gmail.com) or open an issue on [GitHub](https://github.com/sahuaniket095/Talentscope-AI/issues).

---
