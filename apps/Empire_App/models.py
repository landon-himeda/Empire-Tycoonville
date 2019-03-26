from django.db import models
from django.contrib import messages
import bcrypt
import re
from datetime import datetime, timedelta

EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9.+_-]+@[a-zA-Z0-9._-]+\.[a-zA-Z]+$')
NAME_REGEX = re.compile(r'^[a-zA-Z]+$')
PASSWORD_REGEX_CHECK = '^(?=.*[A-Z])(?=.*\d)'

class UserManager(models.Manager):
    def validate_registration(self, request, postData):
        # First Name Validation
        if len(request.POST["first_name"]) < 2:
            messages.error(request, "First name must be at least 2 characters", extra_tags="first_name")
        if not NAME_REGEX.match(request.POST["first_name"]):
            messages.error(request, "First name must only contain letters", extra_tags="first_name")

        # Last Name Validation
        if len(request.POST["last_name"]) < 2:
            messages.error(request, "Last name must be at least 2 characters", extra_tags="last_name")
        if not NAME_REGEX.match(request.POST["last_name"]):
            messages.error(request, "Last name must only contain letters", extra_tags="last_name")

        # Username Validation
        same_username_list = User.objects.filter(username = request.POST["username"])
        if len(same_username_list) != 0:
            messages.error(request, "Username is already registered", extra_tags="username")
        if len(request.POST["username"]) < 3:
            messages.error(request, "Username must be at least 3 characters long", extra_tags="username")

        # Email Validation
        same_email_list = User.objects.filter(email = request.POST["email"])
        if len(same_email_list) != 0:
            messages.error(request, "Email is already registered", extra_tags="email")
        if not EMAIL_REGEX.match(request.POST["email"]):
            messages.error(request, "Email is not valid", extra_tags="email")

        # Password Validation
        if not re.match(PASSWORD_REGEX_CHECK, request.POST["password"]):
            messages.error(request, "Password must contain one number and one uppercase letter", extra_tags="password")
        if len(request.POST["password"]) < 8:
            messages.error(request, "Password must be at least 8 characters long", extra_tags="password")
        if request.POST["password"] != request.POST["confirm_password"]:
            messages.error(request, "Password and confirm password do not match", extra_tags="password")
        return

    def validate_login(self, request, postData):
        # Username or email in DB validation
        if (len(User.objects.filter(username = postData["email_or_username"])) == 0) and (len(User.objects.filter(email = postData["email_or_username"])) == 0):
            messages.error(request, "Login credentials do not match our database", extra_tags="login")
            return
        else:
            try:
                # In the case that the user entered their email
                logging_in_user = User.objects.get(email = postData["email_or_username"])
                # Password validation
                if not bcrypt.checkpw(postData["password"].encode(), logging_in_user.password.encode()):
                    messages.error(request, "Login credentials do not match our database", extra_tags="login")
                return logging_in_user
            except:
                # In the case that the user entered their username
                logging_in_user = User.objects.get(username = postData["email_or_username"])
                # Password validation
                if not bcrypt.checkpw(postData["password"].encode(), logging_in_user.password.encode()):
                    messages.error(request, "Login credentials do not match our database", extra_tags="login")
                return logging_in_user

class User(models.Model):
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)
    username = models.CharField(max_length=255)
    email = models.CharField(max_length=255)
    password = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    objects = UserManager()