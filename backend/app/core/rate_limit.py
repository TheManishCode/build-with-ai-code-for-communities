"""Per-IP rate limiting for the API's one public write path (POST /submissions). Read-only
GET routes are unlimited -- there's nothing to abuse there beyond ordinary load."""

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
