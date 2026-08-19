"""Shared extension instances, initialized in the app factory."""
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Rate limiter keyed by client IP (bonus). Limits are applied per-route and
# initialized against the app in create_app().
limiter = Limiter(key_func=get_remote_address)
