"""
Shared slowapi Limiter instance. Lives in its own module (rather than
app.main) so endpoint modules can import it for per-route limits
(e.g. `@limiter.limit(...)` on /auth/login) without a circular import
back into app.main, which itself imports the API router.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import settings

limiter = Limiter(key_func=get_remote_address, default_limits=[f"{settings.RATE_LIMIT_PER_MINUTE}/minute"])
