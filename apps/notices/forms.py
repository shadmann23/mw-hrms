"""notices/forms.py"""
from django import forms
from apps.notices.models import Notice


class NoticeForm(forms.ModelForm):
    class Meta:
        model = Notice
        fields = ['title', 'content', 'priority', 'visibility', 'publish_date', 'expiry_date', 'attachment']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Notice title...'}),
            'content': forms.Textarea(attrs={'class': 'form-control', 'rows': 6}),
            'priority': forms.Select(attrs={'class': 'form-control'}),
            'visibility': forms.Select(attrs={'class': 'form-control'}),
            'publish_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'expiry_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'attachment': forms.FileInput(attrs={'class': 'form-control'}),
        }
