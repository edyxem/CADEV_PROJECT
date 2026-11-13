"""Sérialiseurs du compte. Aucun champ privilégié n'est inscriptible."""

from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from .models import User, normalize_email
from .validators import username_format_validator, validate_username_not_reserved


class AccountSerializer(serializers.ModelSerializer):
    """Vue « propriétaire » du compte : seule représentation qui expose l'e-mail."""

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "role",
            "email_verified",
            "is_active",
            "date_joined",
        ]
        read_only_fields = [
            "id",
            "username",
            "email",
            "role",
            "email_verified",
            "is_active",
            "date_joined",
        ]


class RegisterSerializer(serializers.Serializer):
    username = serializers.CharField(
        max_length=30,
        validators=[
            username_format_validator,
            validate_username_not_reserved,
            UniqueValidator(
                User.objects.all(),
                lookup="iexact",
                message="Ce nom d'utilisateur est déjà utilisé.",
            ),
        ],
    )
    email = serializers.EmailField(
        validators=[
            UniqueValidator(
                User.objects.all(),
                lookup="iexact",
                message="Un compte existe déjà avec cette adresse e-mail.",
            )
        ]
    )
    password = serializers.CharField(write_only=True, style={"input_type": "password"})
    first_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)

    def validate_email(self, value: str) -> str:
        return normalize_email(value)


class LoginSerializer(serializers.Serializer):
    identifier = serializers.CharField(help_text="Adresse e-mail ou nom d'utilisateur.")
    password = serializers.CharField(write_only=True, style={"input_type": "password"})


class AuthResponseSerializer(serializers.Serializer):
    access = serializers.CharField(help_text="Jeton d'accès à courte durée de vie.")
    user = AccountSerializer()


class AccessTokenSerializer(serializers.Serializer):
    access = serializers.CharField()


class PasswordChangeSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(write_only=True)


class EmailVerifySerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()


class EmailChangeRequestSerializer(serializers.Serializer):
    new_email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


class EmailChangeConfirmSerializer(serializers.Serializer):
    token = serializers.CharField()


class PasswordConfirmSerializer(serializers.Serializer):
    password = serializers.CharField(write_only=True)


class DetailSerializer(serializers.Serializer):
    detail = serializers.CharField()
