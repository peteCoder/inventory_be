from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone
from django.contrib.auth import get_user_model

from django.db.models.signals import post_save
from django.conf import settings



from rest_framework.authtoken.models import Token


# User model
User = settings.AUTH_USER_MODEL


class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email, password, **extra_fields)

class CustomUser(AbstractBaseUser, PermissionsMixin):
	USER_ROLE = [('manager', 'manager'), ('cashier', 'cashier')]

	email = models.EmailField(unique=True)
	first_name = models.CharField(max_length=30, blank=True)
	last_name = models.CharField(max_length=30, blank=True)
	is_staff = models.BooleanField(default=False)
	is_active = models.BooleanField(default=True)
	date_joined = models.DateTimeField(default=timezone.now)
	role = models.CharField(choices=USER_ROLE, max_length=10, default="cashier", verbose_name="Who Am I?")

	code = models.IntegerField(blank=True, null=True)
	is_verified = models.BooleanField(default=False)

	
	objects = CustomUserManager()

	USERNAME_FIELD = 'email'
	REQUIRED_FIELDS = ['first_name', 'last_name']

	def __str__(self):
		return self.email


class Profile(models.Model):
	GENDER_CHOICE = [('male', 'Male'), ('female', 'Female')]
	
	user = models.OneToOneField(User, on_delete=models.CASCADE)
	first_name = models.CharField(max_length=100, blank=True)
	last_name = models.CharField(max_length=100, blank=True)
	phone_number = models.CharField(max_length=100, null=True, blank=True)
	address = models.CharField(max_length=100, blank=True)
	gender = models.CharField(max_length=6, choices=GENDER_CHOICE, blank=True, default='male')
	
	birth_date = models.DateField(null=True, blank=True)
	image = models.TextField(null=False, blank=True)
	bio = models.TextField(blank=True, null=True)


	@property
	def birth_date_format(self):
		date = self.birth_date.strftime("%d/%m/%Y")
		return date



	@property
	def getFullName(self):
		return self.first_name.title() + " " + self.last_name.title()
	
	# In case User instance does not upload an image. 
	# These are the default images that will be uploaded if user is either male or female.
	@property
	def image_url(self):
		try:
			url = self.image
		except:
			if self.gender == 'female':
				url = 'https://res.cloudinary.com/daf9tr3lf/image/upload/v1725024479/undraw_profile_female_dtvvym.svg'
			else:
				url = 'https://res.cloudinary.com/daf9tr3lf/image/upload/v1725024497/undraw_profile_male_oovdba.svg'
		return url

	def __str__(self):
		return self.user.email


	


# Profile will be automatically created when user is created

def create_user_profile(sender, instance, created, **kwargs):
	if created:
		Profile.objects.create(user=instance, first_name=instance.first_name, last_name=instance.last_name)

def save_user_profile(sender, instance, **kwargs):
	instance.profile.save()


def create_token(sender, instance=None, created=False, **kwargs):
    if created:
        Token.objects.create(user=instance)

post_save.connect(create_user_profile, sender=User)
post_save.connect(save_user_profile, sender=User)
post_save.connect(create_token, sender=User)


