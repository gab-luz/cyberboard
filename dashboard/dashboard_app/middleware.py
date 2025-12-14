from django.shortcuts import redirect
from django.urls import reverse
from .models import SystemSettings

class OnboardingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Exclude static/media/admin
        if request.path.startswith('/static/') or request.path.startswith('/admin/'):
            return self.get_response(request)

        settings_exist = SystemSettings.objects.exists()

        if not settings_exist and request.path != reverse('onboarding'):
            return redirect('onboarding')

        if settings_exist and request.path == reverse('onboarding'):
             return redirect('overview')

        response = self.get_response(request)
        return response
