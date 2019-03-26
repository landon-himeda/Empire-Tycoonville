from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.messages import get_messages
from .models import *
import bcrypt

def index(request):
    return render(request, "Empire_App/index.html")

def register(request):
    # Clear stored user input from invalid submissions
    if 'form_input_placeholder' in request.session:
        del request.session["form_input_placeholder"]

    # Validate POST data (enter errors into messages within the validation method)
    User.objects.validate_registration(request, request.POST)

    # If there are errors in messages, redirect to index and show their previous inputs.
    if len(get_messages(request)) > 0:
        request.session["form_input_placeholder"] = request.POST
        return redirect("/")
    else:
        # Encrypt (hash) password
        encrypted_password = bcrypt.hashpw(request.POST["password"].encode(), bcrypt.gensalt())

        # Enter user into DB
        created_user = User.objects.create(first_name = request.POST["first_name"], last_name = request.POST["last_name"], username = request.POST["username"], email = request.POST["email"], password = encrypted_password)

        # Log in user (store user data in session)
        request.session['logged_in_user_id'] = created_user.id
        request.session["logged_in_username"] = created_user.username
        request.session["logged_in"] = True

        return redirect("/dashboard")
    return redirect("/")

def login(request):

    # Clear stored user input from invalid submissions
    if 'form_input_placeholder' in request.session:
        del request.session["form_input_placeholder"]

    # Validate login information (enter errors into messages within the validation method)
    logged_in_user = User.objects.validate_login(request, request.POST)

    # If there are errors in messages, redirect to index and show their previous inputs.
    if len(get_messages(request)) > 0:
        request.session["form_input_placeholder"] = request.POST
        return redirect("/")
    else:
        # Log in user (store user data in session)
        request.session['logged_in_user_id'] = logged_in_user.id
        request.session["logged_in_username"] = logged_in_user.username
        request.session["logged_in"] = True

        return redirect("/dashboard")
    return redirect("/")

def dashboard(request):
    if "logged_in" in request.session:
        return render(request, "Empire_App/dashboard.html")
    else:
        return redirect("/")

def business(request):
    if "logged_in" in request.session:
        return render(request, "Empire_App/business.html")
    else:
        return redirect("/")

def destroy_session(request):
    if "logged_in" in request.session:
        del request.session["logged_in_username"]
        del request.session["logged_in_user_id"]
        del request.session["logged_in"]
        return redirect("/")
    else:
        return redirect("/")