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
            # In demo mode, treat a superuser as present so onboarding isn't forced
            from django.conf import settings
            if getattr(settings, "DEMO_MODE", False):
                has_super = True
            else:
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


class DemoModeMiddleware:
    """When DEMO_MODE is enabled, grant admin-like attributes to users.

    This does not persist changes to the database; it only mutates the
    `request.user` object for the duration of the request so templates
    and simple permission checks (e.g., `user.is_staff`) reflect admin
    access in demo mode.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            from django.conf import settings
            if getattr(settings, "DEMO_MODE", False):
                if hasattr(request, "user") and getattr(request.user, "is_authenticated", False):
                    # Mutate in-memory attributes only; do not save.
                    request.user.is_staff = True
                    request.user.is_superuser = True
        except Exception:
            # Be resilient to settings/db not being available
            pass

        return self.get_response(request)
