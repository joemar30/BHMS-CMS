from django import forms
from .models import TenantDocument

class TenantDocumentForm(forms.ModelForm):
    DOCUMENT_CHOICES = [
        ('', 'Select Document Type...'),
        ('PhilSys National ID', 'PhilSys National ID'),
        ('UMID', 'UMID'),
        ('Driver\'s License', 'Driver\'s License'),
        ('Passport', 'Passport'),
        ('PRC ID', 'PRC ID'),
        ('Postal ID', 'Postal ID'),
        ('NBI Clearance', 'NBI Clearance'),
        ('SSS ID', 'SSS ID'),
        ('Pag-IBIG ID', 'Pag-IBIG ID'),
        ('PhilHealth ID', 'PhilHealth ID'),
        ('TIN ID', 'TIN ID'),
        ('Voter\'s ID', 'Voter\'s ID'),
        ('Student ID', 'Student ID'),
        ('Other', 'Other (Please specify in file)'),
    ]
    
    document_name = forms.ChoiceField(
        choices=DOCUMENT_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'document_name_select'})
    )

    class Meta:
        model = TenantDocument
        fields = ['document_name', 'document_file']
        widgets = {
            'document_file': forms.FileInput(attrs={'class': 'form-control'}),
        }
