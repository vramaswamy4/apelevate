"""Role checks for views.

Every view requires a signed-in user by default (``LoginRequiredMiddleware``); public views opt
out with ``login_not_required``. These decorators add the role on top. A signed-out visitor is
sent to the login page; a signed-in user without the role gets a real 403, not a 200 with an error
message.

Roles are derived from data, not from auth groups:
- student: any signed-in user (mentors can enrol in other mentors' classes too)
- mentor: has a ``MentorProfile``, which only an accepted application creates
- staff: ``is_staff``, the same flag that opens the Django admin
"""

from functools import wraps

from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied


def _role_required(check):
    def decorator(view):
        @wraps(view)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect_to_login(request.get_full_path())
            if not check(request.user):
                raise PermissionDenied
            return view(request, *args, **kwargs)

        return wrapper

    return decorator


mentor_required = _role_required(lambda user: user.is_mentor)
staff_required = _role_required(lambda user: user.is_staff)
