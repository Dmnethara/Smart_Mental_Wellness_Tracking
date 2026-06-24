from functools import wraps
from flask import abort
from flask_login import current_user

def role_required(*roles):
    """
    Decorator to restrict route access to specific user roles.
    Raises an HTTP 403 Forbidden error if the user does not have the required role.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Check if user is authenticated
            if not current_user.is_authenticated:
                abort(401)  # Unauthorized
                
            # Check if user has one of the required roles
            if current_user.role not in roles:
                abort(403)  # Forbidden
                
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def admin_required(f):
    """Decorator to restrict access to admin users only."""
    return role_required('admin')(f)

def counselor_required(f):
    """Decorator to restrict access to counselor users only."""
    return role_required('counselor')(f)
