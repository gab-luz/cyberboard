from django.utils.deprecation import MiddlewareMixin
from django.conf import settings

class GridOpsSecurityMiddleware(MiddlewareMixin):
    def process_response(self, request, response):
        # Add security headers
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'

        # In a real scenario, strict CSP
        # response['Content-Security-Policy'] = "default-src 'self'"

        return response
