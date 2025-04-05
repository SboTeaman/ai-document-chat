from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from django.contrib.auth import authenticate, get_user_model

if TYPE_CHECKING:
    from django.contrib.auth.base_user import AbstractBaseUser
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.settings import api_settings as jwt_settings
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken
from rest_framework_simplejwt.tokens import RefreshToken

from common.exceptions import ServiceError

logger = logging.getLogger(__name__)
User = get_user_model()


def login_user(email: str, password: str) -> dict:
    """Authenticate credentials and return the user plus a fresh JWT pair.

    Raises ``ServiceError`` with a single generic message for unknown users and
    disabled accounts alike, to prevent account enumeration.
    """
    user = authenticate(username=email, password=password)
    # Treat unknown user and disabled account identically to avoid exposing
    # which emails are registered through the public login endpoint.
    if user is None or not user.is_active:
        raise ServiceError("Invalid credentials.", code="invalid_credentials")

    tokens = _generate_tokens(user)
    logger.info("User logged in", extra={"user_id": user.id})
    return {"user": user, **tokens}


def logout_user(refresh_token: str, user: AbstractBaseUser | None = None) -> None:
    """Blacklist a refresh token, but only if it belongs to ``user``.

    Invalid/expired tokens are treated as a successful (idempotent) logout.
    """
    try:
        token = RefreshToken(refresh_token)
    except TokenError as exc:
        # Token already expired/blacklisted/malformed — still a successful logout
        # from the client's perspective, but worth a breadcrumb.
        logger.info("Logout with invalid token", extra={"error": str(exc)})
        return

    # Only the token's owner may blacklist it. Without this check an
    # authenticated user could revoke another user's refresh token (DoS) by
    # posting a token they happened to capture.
    if user is not None:
        token_user_id = token.payload.get(jwt_settings.USER_ID_CLAIM)
        if str(token_user_id) != str(user.id):
            logger.warning("Logout token/user mismatch", extra={"user_id": user.id})
            return

    token.blacklist()


def refresh_access_token(refresh_token: str) -> dict:
    """Rotate a refresh token: revoke the presented one and issue a new pair.

    Raises ``ServiceError`` if the token is invalid, expired, already rotated,
    or belongs to a user that no longer exists.
    """
    try:
        token = RefreshToken(refresh_token)
    except TokenError as exc:
        raise ServiceError("Invalid or expired refresh token.", code="token_invalid") from exc

    # Rotate the refresh token: blacklist the one just presented and mint a fresh
    # pair. The custom endpoint replaces SimpleJWT's TokenRefreshView, so we must
    # apply ROTATE_REFRESH_TOKENS / BLACKLIST_AFTER_ROTATION ourselves — otherwise
    # a captured refresh token stays valid for its full lifetime.
    token.blacklist()

    user_id = token.payload.get(jwt_settings.USER_ID_CLAIM)
    try:
        user = User.objects.get(**{jwt_settings.USER_ID_FIELD: user_id})
    except User.DoesNotExist as exc:
        raise ServiceError("Invalid or expired refresh token.", code="token_invalid") from exc

    new_refresh = RefreshToken.for_user(user)
    return {
        "access_token": str(new_refresh.access_token),
        "refresh_token": str(new_refresh),
    }


def change_password(user: AbstractBaseUser, current_password: str, new_password: str) -> None:
    """Set a new password after verifying the current one, then revoke all
    existing refresh tokens so other sessions are forced to re-authenticate."""
    if not user.check_password(current_password):
        raise ServiceError("Current password is incorrect.", code="wrong_password")
    user.set_password(new_password)
    user.save(update_fields=["password", "updated_at"])
    logout_all_sessions(user)
    logger.info("Password changed", extra={"user_id": user.id})


def logout_all_sessions(user: AbstractBaseUser) -> None:
    """Blacklist every outstanding refresh token for the user (best-effort)."""
    tokens = OutstandingToken.objects.filter(user=user)
    for token in tokens:
        try:
            RefreshToken(token.token).blacklist()
        except TokenError as exc:
            logger.warning(
                "Failed to blacklist token",
                extra={"user_id": user.id, "token_id": token.id, "error": str(exc)},
            )


def _generate_tokens(user: AbstractBaseUser) -> dict[str, str]:
    refresh = RefreshToken.for_user(user)
    return {
        "access_token": str(refresh.access_token),
        "refresh_token": str(refresh),
    }
