from django.urls import path

from . import views

urlpatterns = [
    path("auth/register/", views.RegisterView.as_view(), name="auth-register"),
    path("auth/login/", views.LoginView.as_view(), name="auth-login"),
    path("auth/token/refresh/", views.TokenRefreshView.as_view(), name="auth-token-refresh"),
    path("auth/logout/", views.LogoutView.as_view(), name="auth-logout"),
    path("auth/me/", views.MeView.as_view(), name="auth-me"),
    path("auth/me/deactivate/", views.DeactivateAccountView.as_view(), name="auth-deactivate"),
    path("auth/password/change/", views.PasswordChangeView.as_view(), name="auth-password-change"),
    path(
        "auth/password/reset/",
        views.PasswordResetRequestView.as_view(),
        name="auth-password-reset",
    ),
    path(
        "auth/password/reset/confirm/",
        views.PasswordResetConfirmView.as_view(),
        name="auth-password-reset-confirm",
    ),
    path("auth/email/verify/", views.EmailVerifyView.as_view(), name="auth-email-verify"),
    path(
        "auth/email/verify/resend/",
        views.EmailVerifyResendView.as_view(),
        name="auth-email-verify-resend",
    ),
    path("auth/email/change/", views.EmailChangeRequestView.as_view(), name="auth-email-change"),
    path(
        "auth/email/change/confirm/",
        views.EmailChangeConfirmView.as_view(),
        name="auth-email-change-confirm",
    ),
]
