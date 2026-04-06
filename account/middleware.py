from django.shortcuts import redirect
from django.contrib.auth.models import User
from django.conf import settings


class EnforceOnboardingMiddleware:
    """Redirect to onboarding page while there is no superuser.

    Allows access to a small set of whitelisted paths (admin, onboarding, account auth, static files).
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # If a superuser already exists, do nothing
        try:
            has_super = User.objects.filter(is_superuser=True).exists()
        except Exception:
            # If DB isn't ready yet (migrations not applied), do nothing
            return self.get_response(request)

        if not has_super:
            path = request.path
            allowed_prefixes = [
                '/admin/',
                '/account/onboarding',
                '/account/login',
                '/account/signup',
                settings.STATIC_URL,
                '/favicon.ico',
            ]
            if not any(path.startswith(p) for p in allowed_prefixes):
                return redirect('account:onboarding')

        return self.get_response(request)
