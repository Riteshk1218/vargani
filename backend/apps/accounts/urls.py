from django.urls import path

from . import views

urlpatterns = [
    path("auth/register/", views.RegisterView.as_view(), name="auth-register"),
    path("auth/verify/", views.VerifyView.as_view(), name="auth-verify"),
    path("auth/verify/resend/", views.ResendVerificationView.as_view(), name="auth-verify-resend"),
    path("auth/login/", views.LoginView.as_view(), name="auth-login"),
    path("auth/refresh/", views.RefreshView.as_view(), name="auth-refresh"),
    path("auth/logout/", views.LogoutView.as_view(), name="auth-logout"),
    path("auth/password/forgot/", views.ForgotPasswordView.as_view(), name="auth-password-forgot"),
    path("auth/password/reset/", views.ResetPasswordView.as_view(), name="auth-password-reset"),
    path("auth/password/change/", views.ChangePasswordView.as_view(), name="auth-password-change"),
    path("me/", views.MeView.as_view(), name="me"),
]
