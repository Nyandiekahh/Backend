import uuid
from datetime import timedelta

from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils import timezone


class UserManager(BaseUserManager):
	"""Custom user manager using email as the unique identifier."""

	def create_user(self, email, password=None, **extra_fields):
		if not email:
			raise ValueError("Email is required")
		email = self.normalize_email(email)
		user = self.model(email=email, **extra_fields)
		if password:
			user.set_password(password)
		else:
			user.set_unusable_password()
		user.save(using=self._db)
		return user

	def create_superuser(self, email, password, **extra_fields):
		extra_fields.setdefault("is_staff", True)
		extra_fields.setdefault("is_superuser", True)
		extra_fields.setdefault("is_active", True)
		extra_fields.setdefault("role", User.Role.ADMIN)
		return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
	class Role(models.TextChoices):
		OWNER = "owner", "Owner"
		TENANT = "tenant", "Tenant"
		ADMIN = "admin", "Admin"

	id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
	username = None
	email = models.EmailField(unique=True)
	full_name = models.CharField(max_length=255)
	phone = models.CharField(max_length=20, blank=True)
	role = models.CharField(max_length=20, choices=Role.choices, default=Role.TENANT)
	is_email_verified = models.BooleanField(default=False)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	USERNAME_FIELD = "email"
	REQUIRED_FIELDS = []

	objects = UserManager()

	def __str__(self):
		return self.email


class OTPCode(models.Model):
	class Purpose(models.TextChoices):
		REGISTRATION = "registration", "Registration"
		INVITATION = "invitation", "Invitation"
		PASSWORD_RESET = "password_reset", "Password Reset"

	id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
	user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="otp_codes")
	purpose = models.CharField(max_length=30, choices=Purpose.choices)
	code = models.CharField(max_length=6)
	expires_at = models.DateTimeField()
	is_used = models.BooleanField(default=False)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ["-created_at"]

	def is_valid(self):
		return not self.is_used and timezone.now() < self.expires_at

	@classmethod
	def create_for_user(cls, user, purpose):
		# Keep only one active OTP per purpose for predictable frontend behavior.
		cls.objects.filter(user=user, purpose=purpose, is_used=False).update(is_used=True)
		code = f"{uuid.uuid4().int % 1000000:06d}"
		return cls.objects.create(
			user=user,
			purpose=purpose,
			code=code,
			expires_at=timezone.now() + timedelta(minutes=10),
		)
