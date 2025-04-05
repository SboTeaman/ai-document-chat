from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

User = get_user_model()

COMMON_PASSWORDS = {"password", "password1", "12345678", "qwerty123", "letmein1"}


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ["email", "full_name", "password"]

    def validate_password(self, value: str) -> str:
        """Run Django's validators plus a small extra deny-list of common passwords."""
        validate_password(value)
        if value.lower() in COMMON_PASSWORDS:
            raise serializers.ValidationError("This password is too common.")
        return value

    def validate_email(self, value: str) -> str:
        """Reject already-registered emails (case-insensitive) and normalise to lowercase."""
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value.lower()

    def create(self, validated_data: dict) -> User:
        """Create the user via the manager so the password is properly hashed."""
        return User.objects.create_user(**validated_data)


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "email", "full_name", "created_at"]
        read_only_fields = fields


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8)

    def validate_new_password(self, value: str) -> str:
        """Enforce Django's password-strength validators on the new password."""
        validate_password(value)
        return value
