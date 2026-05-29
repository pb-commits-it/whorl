"""Magic-link auth + signed JWT session cookies."""

from whorl.auth.deps import SESSION_COOKIE, current_user, current_user_with_org
from whorl.auth.jwt import issue_session_token, verify_session_token
from whorl.auth.magic import create_magic_token, redeem_magic_token

__all__ = [
    "SESSION_COOKIE",
    "create_magic_token",
    "current_user",
    "current_user_with_org",
    "issue_session_token",
    "redeem_magic_token",
    "verify_session_token",
]
