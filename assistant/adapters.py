from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.contrib.auth.models import User
from allauth.account.utils import perform_login

class MySocialAccountAdapter(DefaultSocialAccountAdapter):
    def pre_social_login(self, request, sociallogin):
        # Skip if already logged in or social account already exists
        if sociallogin.is_existing:
            return

        # Check if a user with this email already exists
        email = sociallogin.user.email
        if email:
            try:
                user = User.objects.get(email=email)
                # Link the social account to the existing user
                sociallogin.connect(request, user)
            except User.DoesNotExist:
                pass
