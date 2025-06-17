
from django import forms

class UploadFileForm(forms.Form):
    jd_file = forms.FileField(
        label='Job Description (PDF)',
        required=True,
        widget=forms.FileInput(attrs={
            'accept': '.pdf',
            'class': 'mt-1 block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100'
        })
    )
    cv_files = forms.FileField(
        label='Candidate CVs (PDF, up to 80)',
        required=True,
        widget=forms.FileInput(attrs={
            'accept': '.pdf',
            'multiple': True,
            'class': 'mt-1 block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100'
        })
    )

    def clean_cv_files(self):
        cv_files = self.files.getlist('cv_files')
        if len(cv_files) > 80:
            raise forms.ValidationError('You can upload up to 80 CVs at a time.')
        for cv_file in cv_files:
            if not cv_file.name.lower().endswith('.pdf'):
                raise forms.ValidationError('All CV files must be in PDF format.')
        return cv_files

    def clean_jd_file(self):
        jd_file = self.cleaned_data['jd_file']
        if not jd_file.name.lower().endswith('.pdf'):
            raise forms.ValidationError('Job description must be in PDF format.')
        return jd_file
