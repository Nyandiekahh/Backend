from django.urls import path

from .views import (
    AuthTokenRefreshView,
    ChangePasswordView,
    ForgotPasswordView,
    LoginView,
    ProfileView,
    RegisterView,
    ResendOTPView,
    ResetPasswordView,
    SetPasswordView,
    VerifyOTPView,
)

urlpatterns = [
    path("register/", RegisterView.as_view()),
    path("login/", LoginView.as_view()),
    path("verify-otp/", VerifyOTPView.as_view()),
    path("resend-otp/", ResendOTPView.as_view()),
    path("set-password/", SetPasswordView.as_view()),
    path("forgot-password/", ForgotPasswordView.as_view()),
    path("reset-password/", ResetPasswordView.as_view()),
    path("profile/", ProfileView.as_view()),
    path("change-password/", ChangePasswordView.as_view()),
    path("token/refresh/", AuthTokenRefreshView.as_view()),
]
