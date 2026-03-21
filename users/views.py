from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView

from .models import OTPCode, User


def _user_payload(user):
	return {
		"id": str(user.id),
		"email": user.email,
		"full_name": user.full_name,
		"phone": user.phone,
		"role": user.role,
		"is_active": user.is_active,
	}


def _auth_payload(user):
	refresh = RefreshToken.for_user(user)
	return {
		"access": str(refresh.access_token),
		"refresh": str(refresh),
		"user": _user_payload(user),
	}


class RegisterView(APIView):
	permission_classes = [permissions.AllowAny]

	def post(self, request):
		data = request.data
		required_fields = ["email", "full_name", "password", "role"]
		missing = [field for field in required_fields if not data.get(field)]
		if missing:
			return Response(
				{field: ["This field is required."] for field in missing},
				status=status.HTTP_400_BAD_REQUEST,
			)

		if User.objects.filter(email__iexact=data["email"]).exists():
			return Response(
				{"email": ["A user with this email already exists."]},
				status=status.HTTP_400_BAD_REQUEST,
			)

		user = User.objects.create_user(
			email=data["email"],
			password=data["password"],
			full_name=data.get("full_name", ""),
			phone=data.get("phone", ""),
			role=data.get("role", User.Role.TENANT),
			is_active=True,
		)
		otp = OTPCode.create_for_user(user, OTPCode.Purpose.REGISTRATION)

		payload = {
			"message": "Registration successful. Verify your OTP to continue.",
			"user": _user_payload(user),
		}
		if request.user.is_staff if request.user.is_authenticated else True:
			payload["otp_debug"] = otp.code
		return Response(payload, status=status.HTTP_201_CREATED)


class LoginView(APIView):
	permission_classes = [permissions.AllowAny]

	def post(self, request):
		email = request.data.get("email", "")
		password = request.data.get("password", "")
		user = authenticate(request, email=email, password=password)
		if not user:
			return Response(
				{"detail": "Invalid email or password."},
				status=status.HTTP_401_UNAUTHORIZED,
			)
		return Response(_auth_payload(user))


class VerifyOTPView(APIView):
	permission_classes = [permissions.AllowAny]

	def post(self, request):
		email = request.data.get("email")
		code = request.data.get("otp")
		if not email or not code:
			return Response(
				{"detail": "Email and OTP are required."},
				status=status.HTTP_400_BAD_REQUEST,
			)

		user = User.objects.filter(email__iexact=email).first()
		if not user:
			return Response(
				{"detail": "User not found."},
				status=status.HTTP_404_NOT_FOUND,
			)

		otp = OTPCode.objects.filter(user=user, code=code, is_used=False).first()
		if not otp or not otp.is_valid():
			return Response(
				{"detail": "Invalid or expired OTP."},
				status=status.HTTP_400_BAD_REQUEST,
			)

		user.is_email_verified = True
		user.save(update_fields=["is_email_verified", "updated_at"])
		return Response(_auth_payload(user))


class ResendOTPView(APIView):
	permission_classes = [permissions.AllowAny]

	def post(self, request):
		email = request.data.get("email")
		user = User.objects.filter(email__iexact=email).first()
		if not user:
			return Response({"message": "If account exists, OTP was resent."})

		otp = OTPCode.create_for_user(user, OTPCode.Purpose.REGISTRATION)
		payload = {"message": "OTP resent successfully."}
		if request.user.is_staff if request.user.is_authenticated else True:
			payload["otp_debug"] = otp.code
		return Response(payload)


class SetPasswordView(APIView):
	permission_classes = [permissions.AllowAny]

	def post(self, request):
		email = request.data.get("email")
		code = request.data.get("otp")
		password = request.data.get("password") or request.data.get("new_password")

		if not email or not code or not password:
			return Response(
				{"detail": "Email, OTP and password are required."},
				status=status.HTTP_400_BAD_REQUEST,
			)

		user = User.objects.filter(email__iexact=email).first()
		if not user:
			return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)

		otp = OTPCode.objects.filter(user=user, code=code, is_used=False).first()
		if not otp or not otp.is_valid():
			return Response(
				{"detail": "Invalid or expired OTP."},
				status=status.HTTP_400_BAD_REQUEST,
			)

		try:
			validate_password(password, user=user)
		except Exception as exc:
			return Response({"password": [str(exc)]}, status=status.HTTP_400_BAD_REQUEST)

		user.set_password(password)
		user.is_active = True
		user.is_email_verified = True
		user.save(update_fields=["password", "is_active", "is_email_verified", "updated_at"])

		otp.is_used = True
		otp.save(update_fields=["is_used"])
		return Response({"success": True})


class ForgotPasswordView(APIView):
	permission_classes = [permissions.AllowAny]

	def post(self, request):
		email = request.data.get("email")
		user = User.objects.filter(email__iexact=email).first()
		if not user:
			return Response({"message": "If account exists, reset details were sent."})

		otp = OTPCode.create_for_user(user, OTPCode.Purpose.PASSWORD_RESET)
		payload = {"message": "Reset details sent."}
		if request.user.is_staff if request.user.is_authenticated else True:
			payload["otp_debug"] = otp.code
			payload["uid"] = str(user.id)
			payload["token"] = otp.code
		return Response(payload)


class ResetPasswordView(APIView):
	permission_classes = [permissions.AllowAny]

	def post(self, request):
		token = request.data.get("token")
		uid = request.data.get("uid")
		password = request.data.get("password") or request.data.get("new_password")

		email = request.data.get("email")
		otp_value = request.data.get("otp")

		user = None
		otp = None

		if uid and token:
			try:
				# Support both UUID uid and base64 encoded uid for flexibility.
				user = User.objects.filter(id=uid).first()
				if not user:
					decoded_uid = force_str(urlsafe_base64_decode(uid))
					user = User.objects.filter(id=decoded_uid).first()
			except Exception:
				user = None
			if user:
				otp = OTPCode.objects.filter(
					user=user,
					code=token,
					purpose=OTPCode.Purpose.PASSWORD_RESET,
					is_used=False,
				).first()

		if not user and email and otp_value:
			user = User.objects.filter(email__iexact=email).first()
			if user:
				otp = OTPCode.objects.filter(
					user=user,
					code=otp_value,
					purpose=OTPCode.Purpose.PASSWORD_RESET,
					is_used=False,
				).first()

		if not user or not otp or not otp.is_valid():
			return Response(
				{"detail": "Invalid or expired reset token."},
				status=status.HTTP_400_BAD_REQUEST,
			)

		if not password:
			return Response({"detail": "Password is required."}, status=status.HTTP_400_BAD_REQUEST)

		try:
			validate_password(password, user=user)
		except Exception as exc:
			return Response({"password": [str(exc)]}, status=status.HTTP_400_BAD_REQUEST)

		user.set_password(password)
		user.save(update_fields=["password", "updated_at"])
		otp.is_used = True
		otp.save(update_fields=["is_used"])
		return Response({"success": True})


class ProfileView(APIView):
	permission_classes = [permissions.IsAuthenticated]

	def get(self, request):
		return Response(_user_payload(request.user))

	def patch(self, request):
		user = request.user
		updatable = ["full_name", "phone", "email"]
		for field in updatable:
			if field in request.data:
				setattr(user, field, request.data.get(field) or "")
		user.save(update_fields=[*updatable, "updated_at"])
		return Response(_user_payload(user))


class ChangePasswordView(APIView):
	permission_classes = [permissions.IsAuthenticated]

	def post(self, request):
		current_password = request.data.get("current_password")
		new_password = request.data.get("new_password")
		user = request.user

		if not user.check_password(current_password):
			return Response(
				{"detail": "Current password is incorrect."},
				status=status.HTTP_400_BAD_REQUEST,
			)

		try:
			validate_password(new_password, user=user)
		except Exception as exc:
			return Response({"new_password": [str(exc)]}, status=status.HTTP_400_BAD_REQUEST)

		user.set_password(new_password)
		user.save(update_fields=["password", "updated_at"])
		return Response({"success": True})


class AuthTokenRefreshView(TokenRefreshView):
	permission_classes = [permissions.AllowAny]
