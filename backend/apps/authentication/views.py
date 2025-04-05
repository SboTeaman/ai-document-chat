import logging

from django.contrib.auth import get_user_model
from django_ratelimit.decorators import ratelimit
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from common.exceptions import ServiceError

from . import serializers, services

logger = logging.getLogger(__name__)
User = get_user_model()


class RegisterView(APIView):
    permission_classes = [AllowAny]

    @ratelimit(key="ip", rate="10/h", method="POST", block=True)
    def post(self, request):
        """Register a new user and return their profile with a JWT pair."""
        serializer = serializers.RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        tokens = services._generate_tokens(user)
        logger.info("New user registered", extra={"user_id": user.id})
        return Response(
            {"data": {"user": serializers.UserSerializer(user).data, **tokens}},
            status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    permission_classes = [AllowAny]

    @ratelimit(key="ip", rate="5/15m", method="POST", block=True)
    def post(self, request):
        """Authenticate credentials and return the user with a JWT pair."""
        serializer = serializers.LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            result = services.login_user(
                email=serializer.validated_data["email"],
                password=serializer.validated_data["password"],
            )
        except ServiceError as exc:
            # Single generic message regardless of root cause (unknown user,
            # bad password, disabled account) to avoid user enumeration. The
            # message comes from the service so there is one canonical string.
            return Response(
                {
                    "errors": [
                        {
                            "code": exc.code,
                            "message": exc.message,
                            "field": None,
                        }
                    ]
                },
                status=status.HTTP_401_UNAUTHORIZED,
            )
        return Response(
            {
                "data": {
                    "user": serializers.UserSerializer(result["user"]).data,
                    "access_token": result["access_token"],
                    "refresh_token": result["refresh_token"],
                }
            }
        )


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Blacklist the caller's refresh token (idempotent)."""
        refresh_token = request.data.get("refresh_token", "")
        services.logout_user(refresh_token, user=request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)


class TokenRefreshView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        """Exchange a refresh token for a rotated access + refresh pair."""
        refresh_token = request.data.get("refresh_token", "")
        try:
            tokens = services.refresh_access_token(refresh_token)
        except ServiceError as exc:
            return Response(
                {"errors": [{"code": exc.code, "message": exc.message, "field": None}]},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        return Response({"data": tokens})


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Return the authenticated user's own profile."""
        return Response({"data": serializers.UserSerializer(request.user).data})


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Change the caller's password and revoke their other sessions."""
        serializer = serializers.ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            services.change_password(
                request.user,
                serializer.validated_data["current_password"],
                serializer.validated_data["new_password"],
            )
        except ServiceError as exc:
            return Response(
                {"errors": [{"code": exc.code, "message": exc.message, "field": "current_password"}]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)
