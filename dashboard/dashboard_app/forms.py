from django import forms
from .models import SystemSettings

class OnboardingForm(forms.ModelForm):
    admin_username = forms.CharField(max_length=150)
    admin_password = forms.CharField(widget=forms.PasswordInput)
    admin_password_confirm = forms.CharField(widget=forms.PasswordInput)

    class Meta:
        model = SystemSettings
        fields = ['domain', 'email', 'public_dashboard']

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get("admin_password")
        p2 = cleaned_data.get("admin_password_confirm")
        if p1 != p2:
            raise forms.ValidationError("Passwords do not match")
        return cleaned_data
