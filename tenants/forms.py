from django import forms
from .models import TenantDocument

class TenantDocumentForm(forms.ModelForm):
    class Meta:
        model = TenantDocument
        fields = ['document_name', 'document_file']
        widgets = {
            'document_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter document name (e.g. NBI Clearance, Valid ID)'}),
            'document_file': forms.FileInput(attrs={'class': 'form-control'}),
        }
