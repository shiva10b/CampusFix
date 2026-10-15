from functools import wraps

from django.contrib.auth.decorators import login_required
from django.shortcuts import render


def role_required(*allowed_roles):
    """Require login and one of the supplied CampusFix roles."""

    def decorator(view_func):
        @login_required
        @wraps(view_func)
        def wrapped(request, *args, **kwargs):
            if request.user.role not in allowed_roles:
                return render(request, "403.html", status=403)
            return view_func(request, *args, **kwargs)

        return wrapped

    return decorator


def management_roles():
    """Roles allowed to manage complaints, from department to institution level."""
    from .models import User

    return (
        User.Role.COORDINATOR,
        User.Role.DEAN,
        User.Role.ADMIN,
        User.Role.SUPERADMIN,
    )
