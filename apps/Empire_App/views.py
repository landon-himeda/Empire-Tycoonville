from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.messages import get_messages
from .models import *
import bcrypt
from timeloop import Timeloop
from datetime import timedelta
import random
from decimal import Decimal

# Set up Timeloop
tl = Timeloop()

# Update market multipliers every 10 seconds
@tl.job(interval=timedelta(seconds=10))
def market_updater():
    # Update every market row in DB
    for market in Market.objects.all():
        # If someone has bought one of the businesses
        if market.started == True:

            # Set range of change depending on volatility and growth rate
            low = float(Decimal.from_float(-.1)*market.volatility)
            high = float(market.growth_rate*market.volatility)

            # Randomly generate the market change
            change = Decimal.from_float(random.uniform(low, high))
            market.current_multiplier += change

            # print(f"Market = {market.name}, Change = {change}, Market_multiplier = {market.current_multiplier} Num businesses = {market.num_businesses}")

            # Save new current_multiplier to market in DB
            market.save()

# Update user balance every 5 seconds
@tl.job(interval=timedelta(seconds=5))
def balance_updater():
    # For every user in DB
    for user in User.objects.all():
        # Add revenue from each business to their balance
        for business in user.businesses.all():
            revenue = (business.revenue_per_minute/12)
            user.balance += revenue
            user.save()
            print(f"User = {user.first_name}, Revenue per min = {revenue * 12}, Balance = {user.balance}")

# Start all Timeloop functions
tl.start()

def index(request):
    return render(request, "Empire_App/index.html")

def process_register(request):
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

        # Create lemonade stand for new user
        first_business_type = Business_Type.objects.get(name = "Lemonade Stand")
        related_market = first_business_type.market
        first_lemonade_stand = Business.objects.create(name = first_business_type.name, bought_for = 0.00, value = 100.00, revenue_per_minute = first_business_type.revenue_per_minute, user = created_user, market = related_market, business_type = first_business_type)

        # Increment num_businesses of Lemonade Market
        related_market.num_businesses += 1
        related_market.save()

        # Start the lemonade market autoupdate if it hasn't been started
        if related_market.started == False:
            related_market.started = True
            related_market.save()

        # Log in user (store user data in session)
        request.session['logged_in_user_id'] = created_user.id
        request.session["logged_in_username"] = created_user.username
        request.session["logged_in"] = True

        return redirect("/dashboard")
    return redirect("/")

def process_login(request):

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

def process_buy_business(request):
    if "logged_in" in request.session:
        logged_in_user = User.objects.get(id=request.session["logged_in_user_id"])
        selected_business_type = Business_Type.objects.get(id=request.POST["business_type_id"])
        related_market = selected_business_type.market

        # Subtract business cost (including market multiplier) from user balance
        bought_price = selected_business_type.default_value*related_market.current_multiplier
        logged_in_user.balance -= bought_price
        logged_in_user.save()

        # Increment number of businesses associated with market
        related_market.num_businesses += 1
        related_market.save()

        # Start the market autoupdate if it hasn't been started
        if related_market.started == False:
            related_market.started = True
            related_market.save()

        # Create DB row
        created_business = Business.objects.create(name = selected_business_type.name, bought_for = bought_price, value = bought_price, revenue_per_minute = selected_business_type.revenue_per_minute, user = logged_in_user, market = related_market, business_type = selected_business_type)
        return redirect(f"/business/{created_business.id}")
    else:
        return redirect("/")

def process_buy_addon(request):
    if "logged_in" in request.session:
        logged_in_user = User.objects.get(id=request.session["logged_in_user_id"])
        selected_addon_type = Addon_Type.objects.get(id=request.POST["addon_type_id"])
        selected_business = Business.objects.get(id=request.POST["business_id"])

        # Subtract addon cost from user balance
        logged_in_user.balance -= selected_addon_type.cost
        logged_in_user.save()

        # Increase business value by addon cost
        selected_business.value += selected_addon_type.cost
        selected_business.save()

        # Create DB row
        created_addon = Addon.objects.create(name = selected_addon_type.name, revenue_per_minute = selected_addon_type.revenue_per_minute, business = selected_business, addon_type = selected_addon_type)
        return redirect(f"/business/{selected_business.id}")
    else:
        return redirect("/")

def process_sell_business(request):
    if "logged_in" in request.session:
        logged_in_user = User.objects.get(id=request.session["logged_in_user_id"])
        selected_business = Business.objects.get(id=request.POST["business_id"])
        related_market = selected_business.market

        # Add business value to user balance (get income from the sale)
        logged_in_user.balance += selected_business.value
        logged_in_user.save()

        # Drop market multiplier
        related_market.current_multiplier -= related_market.volatility * 2

        # Decrement number of businesses associated with market
        related_market.num_businesses -= 1
        related_market.save()

        # Delete business
        selected_business.delete()
        return redirect("/dashboard")
    else:
        return redirect("/")

def buy_business(request, id):
    if "logged_in" in request.session:
        context = {
            "new_business" : Business_Type.objects.get(id = id)
        }
        return render(request, "Empire_App/buy_business.html", context)
    else:
        return redirect("/")

def market(request):
    if "logged_in" in request.session:
        return render(request, "Empire_App/market.html")
    else:
        return redirect("/")

def process_log_out(request):
    if "logged_in" in request.session:
        del request.session["logged_in_username"]
        del request.session["logged_in_user_id"]
        del request.session["logged_in"]
        return redirect("/")
    else:
        return redirect("/")

# The following code is necessary for Timeloop
if __name__ == "__main__":
    tl.start(block=True)