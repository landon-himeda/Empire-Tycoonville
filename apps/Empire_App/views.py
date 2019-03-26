from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.messages import get_messages
from .models import *
import bcrypt

def index(request):
    return render(request, "Empire_App/index.html")

def dashboard(request):
    return render(request, "Empire_App/dashboard.html")

def business(request):
    return render(request, "Empire_App/business.html")