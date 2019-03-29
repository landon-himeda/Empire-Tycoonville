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
            # print(f"User = {user.first_name}, Revenue per min = {revenue * 12}, Balance = {user.balance}")

# Update net worth every 5 seconds
@tl.job(interval=timedelta(seconds=5))
def net_worth_updater():
    # For every user in DB
    for user in User.objects.all():
        # Calculate their net worth by adding balance and the values of all their businesses
        user.net_worth = user.balance
        for business in user.businesses.all():
            user.net_worth += business.value
        user.save()

# Update market multipliers every 10 seconds, update business values in DB accordingly
@tl.job(interval=timedelta(seconds=10))
def market_and_business_value_updater():
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

            # Update all business values in DB
            for business in market.businesses.all():
                business.value = business.business_type.default_value*market.current_multiplier
                business.save()

# Save market snapshot every 2 minutes
@tl.job(interval=timedelta(seconds=120))
def market_snapshot():
    # Add snapshot for every market in DB
    for market in Market.objects.all():
        # If someone has bought one of the businesses
        if market.started == True:
            existing_snapshots = Market_Snapshot.objects.filter(market = market)
            # Add new snapshot and remove oldest snapshot if there are 20 snapshots for given market
            if len(existing_snapshots) >= 20:
                oldest_snapshot = existing_snapshots.first()
                oldest_snapshot.delete()
            new_snapshot = Market_Snapshot.objects.create(snapshot_multiplier = market.current_multiplier, market = market)

            # print(f"Snapshot taken of {market.name}")

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
        request.session["logged_in_user_id"] = logged_in_user.id
        request.session["logged_in_username"] = logged_in_user.username
        request.session["logged_in"] = True

        return redirect("/dashboard")
    return redirect("/")

def dashboard(request):
    if "logged_in" in request.session:
        context = {
            "logged_in_user": User.objects.get(id = request.session["logged_in_user_id"]),
            "all_business_types": Business_Type.objects.all(),
        }
        return render(request, "Empire_App/dashboard.html", context)
    else:
        return redirect("/")

def market(request):
    if "logged_in" in request.session:
        context = {
            "logged_in_user": User.objects.get(id = request.session["logged_in_user_id"]),
            "all_business_types": Business_Type.objects.all(),
            "all_markets": Market.objects.all(),
            "all_market_snapshots": Market_Snapshot.objects.all(),
        }
        return render(request, "Empire_App/market.html", context)
    else:
        return redirect("/")

def business(request, business_id):
    if "logged_in" in request.session:
        my_business = Business.objects.get(id = business_id)
        btype = Business_Type.objects.get(name = my_business.name)
        print("*"*50)
        print(btype.addon_types.all())

        context = {
            "all_business_types": Business_Type.objects.all(),
            "logged_in_user": User.objects.get(id = request.session["logged_in_user_id"]),
            "this_business": my_business,
            "this_business_addon_types": btype.addon_types.all(),
        }
        return render(request, "Empire_App/business.html", context)
    else:
        return redirect("/")

def process_buy_business(request, business_type_id):
    if "logged_in" in request.session:
        logged_in_user = User.objects.get(id=request.session["logged_in_user_id"])
        selected_business_type = Business_Type.objects.get(id=business_type_id)
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

def process_buy_addon(request, business_id, addon_type_id):
    if "logged_in" in request.session:
        logged_in_user = User.objects.get(id=request.session["logged_in_user_id"])
        selected_addon_type = Addon_Type.objects.get(id=addon_type_id)
        selected_business = Business.objects.get(id=business_id)

        if len(selected_business.addons.filter(addon_type = selected_addon_type)) == 0:
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

def process_sell_business(request, business_id):
    if "logged_in" in request.session:
        logged_in_user = User.objects.get(id=request.session["logged_in_user_id"])
        selected_business = Business.objects.get(id=business_id)
        related_market = selected_business.market

        # Add business value to user balance (get income from the sale)
        logged_in_user.balance += selected_business.value
        logged_in_user.save()

        # Drop market multiplier
        related_market.current_multiplier -= related_market.volatility * 2

        # Decrement number of businesses associated with market
        related_market.num_businesses -= 1
        related_market.save()

        # Add new market snapshot and remove oldest snapshot if there are 20 snapshots for given market
        existing_snapshots = Market_Snapshot.objects.filter(market = related_market)
        if len(existing_snapshots) >= 20:
            oldest_snapshot = existing_snapshots.first()
            oldest_snapshot.delete()
        new_snapshot = Market_Snapshot.objects.create(snapshot_multiplier = related_market.current_multiplier, market = related_market)

        # Delete business
        selected_business.delete()
        return redirect("/dashboard")
    else:
        return redirect("/")

def buy_business(request, business_type_id):
    if "logged_in" in request.session:
        context = {
            "new_business" : Business_Type.objects.get(id = business_type_id),
            "all_add_ons" : Addon_Type.objects.filter(business_type_id = business_type_id),
        }
        return render(request, "Empire_App/buy_business.html", context)
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

def process_reset(request):
    # Reset changes in database
    if len(User.objects.all()) > 0:
        User.objects.all().delete()
    if len(Market.objects.all()) > 0:
        for market in Market.objects.all():
            market.started = False
            market.current_multiplier = 1
            market.num_businesses = 0
    if len(Market_Snapshot.objects.all()) > 0:
        Market_Snapshot.objects.all().delete()
    if len(Business.objects.all()) > 0:
        Business.objects.all().delete()
    if len(Addon.objects.all()) > 0:
        Addon.objects.all().delete()
    return redirect("/")

def process_create_database(request):
    # Create blueprints for businesses
    Business_Type.objects.create(name = "Lemonade Stand", default_value = 100.00, revenue_per_minute = 10.00, image_url = "/static/Empire_App/images/lemonade_stand.jpg")

    Business_Type.objects.create(name = "Ice Cream Stand", default_value = 500.00, revenue_per_minute = 40.00, image_url = "/static/Empire_App/images/ice_cream_stand.jpg")

    Business_Type.objects.create(name = "Pizza Restaurant", default_value = 6000.00, revenue_per_minute = 100.00, image_url = "/static/Empire_App/images/pizza_shop.png")

    Business_Type.objects.create(name = "Arcade", default_value = 15000.00, revenue_per_minute = 350.00, image_url = "/static/Empire_App/images/arcade.jpg")

    Business_Type.objects.create(name = "Ski Resort", default_value = 50000.00, revenue_per_minute = 900.00, image_url = "/static/Empire_App/images/ski_resort.png")

    Business_Type.objects.create(name = "Casino", default_value = 80000.00, revenue_per_minute = 1000.00, image_url = "/static/Empire_App/images/casino.png")

    # Create markets
    Market.objects.create(name = "Lemonade Stand Market", volatility = 0.10, growth_rate = 0.30, description = "Stable, with a solid growth rate. A great place to start!", color = "#ffc500", business_type = Business_Type.objects.get(name="Lemonade Stand"))

    Market.objects.create(name = "Ice Cream Stand Market", volatility = 0.50, growth_rate = 0.20, description = "Much more volatile than lemonade, with a similar growth rate.", color = "#00adaf", business_type = Business_Type.objects.get(name="Ice Cream Stand"))

    Market.objects.create(name = "Pizza Restaurant Market", volatility = 0.10, growth_rate = 0.40, description = "Dependable, with stable growth. People always like pizza!", color = "#ca1625", business_type = Business_Type.objects.get(name="Pizza Restaurant"))

    Market.objects.create(name = "Arcade Market", volatility = 0.10, growth_rate = 0.10, description = "Very stable, with little market growth.", color = "#99ca60", business_type = Business_Type.objects.get(name="Arcade"))

    Market.objects.create(name = "Ski Resort Market", volatility = 0.50, growth_rate = 0.03, description = "Very volatile market. Great revenue/cost ratio.", color = "#2196f3", business_type = Business_Type.objects.get(name="Ski Resort"))

    Market.objects.create(name = "Casino Market", volatility = 0.20, growth_rate = 0.10, description = "Very stable, low growth market. High revenue.", color = "#a716ff", business_type = Business_Type.objects.get(name="Casino"))

    # Create blueprints for addons
    Addon_Type.objects.create(name = "Blender", cost = 50.00, revenue_per_minute = 5.00, image_url = "/static/Empire_App/images/blender.jpg", description = "A must-have for every lemonade stand entrepreneur.", business_type = Business_Type.objects.get(name = "Lemonade Stand"))

    Addon_Type.objects.create(name = "Juicer", cost = 100.00, revenue_per_minute = 9.00, image_url = "/static/Empire_App/images/juicer.jpg", description = "Make your juice jucier!", business_type = Business_Type.objects.get(name = "Lemonade Stand"))

    Addon_Type.objects.create(name = "Ice Maker", cost = 150.00, revenue_per_minute = 12.00, image_url = "/static/Empire_App/images/icemaker.jpg", description = "Beats importing ice from Arendelle.", business_type = Business_Type.objects.get(name = "Lemonade Stand"))

    Addon_Type.objects.create(name = "Ice Cream Machine", cost = 150.00, revenue_per_minute = 15.00, image_url = "/static/Empire_App/images/ice_cream_machine.jpg", description = "Soft serve is great! It's much better than carpal tunnel syndrome.", business_type = Business_Type.objects.get(name = "Ice Cream Stand"))

    Addon_Type.objects.create(name = "Milkshake Machine", cost = 220.00, revenue_per_minute = 25.00, image_url = "/static/Empire_App/images/milkshake_machine.jpg", description = "Drink your ice cream!", business_type = Business_Type.objects.get(name = "Ice Cream Stand"))

    Addon_Type.objects.create(name = "Delivery", cost = 250.00, revenue_per_minute = 20.00, image_url = "/static/Empire_App/images/pizza_delivery.png", description = "Your customers are lazy. Enable them.", business_type = Business_Type.objects.get(name = "Pizza Restaurant"))

    Addon_Type.objects.create(name = "Pizza Oven", cost = 350.00, revenue_per_minute = 30.00, image_url = "/static/Empire_App/images/pizza_oven.png", description = "Stop using your mom's oven. An industrial-sized upgrade.", business_type = Business_Type.objects.get(name = "Pizza Restaurant"))

    Addon_Type.objects.create(name = "Beer", cost = 450.00, revenue_per_minute = 40.00, image_url = "/static/Empire_App/images/beer.png", description = "Ice-cold refreshment to whet appetites and earn Yelp ratings.", business_type = Business_Type.objects.get(name = "Pizza Restaurant"))

    Addon_Type.objects.create(name = "Air Hockey", cost = 250.00, revenue_per_minute = 40.00, image_url = "/static/Empire_App/images/air_hockey.png", description = "Challenge your friends to this classic game. Your customers can play too.", business_type = Business_Type.objects.get(name = "Arcade"))

    Addon_Type.objects.create(name = "Beer", cost = 450.00, revenue_per_minute = 60.00, image_url = "/static/Empire_App/images/beer.png", description = "Perfect for fun times and sticky joysticks.", business_type = Business_Type.objects.get(name = "Arcade"))

    Addon_Type.objects.create(name = "Vending Machine", cost = 700.00, revenue_per_minute = 100.00, image_url = "/static/Empire_App/images/vending_machine.jpg", description = "Be prepared to sweep chips from every corner.", business_type = Business_Type.objects.get(name = "Arcade"))

    Addon_Type.objects.create(name = "Gondola", cost = 1000.00, revenue_per_minute = 150.00, image_url = "/static/Empire_App/images/gondola.png", description = "The OG Lyft.", business_type = Business_Type.objects.get(name = "Ski Resort"))

    Addon_Type.objects.create(name = "Coffee Cart", cost = 2500.00, revenue_per_minute = 250.00, image_url = "/static/Empire_App/images/coffee_cart.jpg", description = "A warm Java oasis in a winter wonderland.", business_type = Business_Type.objects.get(name = "Ski Resort"))

    Addon_Type.objects.create(name = "Ski Shop", cost = 7000.00, revenue_per_minute = 400.00, image_url = "/static/Empire_App/images/ski_shop.png", description = "Selling ski gear and yeti stuffed-animals alike.", business_type = Business_Type.objects.get(name = "Ski Resort"))

    Addon_Type.objects.create(name = "Casino Sign", cost = 5000.00, revenue_per_minute = 300.00, image_url = "/static/Empire_App/images/casino_sign.jpg", description = "You Are Here. In case you didn't know.", business_type = Business_Type.objects.get(name = "Casino"))

    Addon_Type.objects.create(name = "Poker", cost = 10000.00, revenue_per_minute = 600.00, image_url = "/static/Empire_App/images/poker.jpg", description = "Raise your revenues and Check the market.", business_type = Business_Type.objects.get(name = "Casino"))

    Addon_Type.objects.create(name = "Hotel", cost = 30000.00, revenue_per_minute = 900.00, image_url = "/static/Empire_App/images/hotel.jpg", description = "Keep your customers close and your profits closer.", business_type = Business_Type.objects.get(name = "Casino"))

    return redirect("/")

# The following code is necessary for Timeloop
if __name__ == "__main__":
    tl.start(block=True)