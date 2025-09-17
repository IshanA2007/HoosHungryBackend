from django.utils.dateparse import parse_date
from django.utils.dateparse import parse_time
from .models import DiningHall, Day, Period, Station, Allergen, MenuItem, Ingredient, NutritionInfo

def load_menu_data(data):
    # 1. DiningHall
    dining_hall, _ = DiningHall.objects.update_or_create(
        name="Observatory Hill Dining Room",
        defaults={"scrape_url": data["base_url"]}
    )

    # 2. Day
    date_str = data["date"]
    day_obj = Day.objects.create(
        date=parse_date(date_str),
        day_name="",  # You can set this if you have the day name
        open_time="07:00",  # Set appropriately if you have this info
        close_time="22:00",  # Set appropriately if you have this info
        dining_hall=dining_hall
    )

    # 3. Periods
    period_objs = {}
    for period_id, period_info in data["periods"].items():
        period_objs[period_id] = Period.objects.create(
            type=period_info["name"],
            vendor_id=period_id,
            start_time="07:00",  # Set appropriately if you have this info
            end_time="10:00",    # Set appropriately if you have this info
            day=day_obj
        )

    # 4. Stations
    station_objs = {}
    for station in data["base_model_raw"]["Menu"]["MenuStations"]:
        station_objs[station["StationId"]] = Station.objects.create(
            name=station["StationName"],
            number=station["StationId"],
            period=period_objs.get(data["base_model_raw"]["SelectedPeriodId"])  # You may want to map stations to periods more accurately
        )

    # 5. Allergens
    allergen_objs = {}
    for allergen in data["base_model_raw"]["Menu"]["Allergens"]:
        allergen_objs[allergen["Name"]] = Allergen.objects.get_or_create(name=allergen["Name"])[0]

    # 6. MenuItems
    for product in data["base_model_raw"]["Menu"]["MenuProducts"]:
        prod = product["Product"]
        menu_item = MenuItem.objects.create(
            station=station_objs.get(product["StationId"]),
            item_name=prod["ProductName"],
            item_description=prod.get("Description", ""),
            item_category=prod.get("Category", ""),
            is_gluten=prod.get("IsGlutenFree", False),
            is_vegan=prod.get("IsVegan", False),
            is_vegetarian=prod.get("IsVegetarian", False)
        )
        # Allergens
        for allergen in prod.get("Allergens", []):
            if allergen_objs.get(allergen["Name"]):
                menu_item.allergens.add(allergen_objs[allergen["Name"]])
        # Ingredients
        for ing_name in prod.get("Ingredients", []):
            ingredient, _ = Ingredient.objects.get_or_create(name=ing_name)
            menu_item.ingredients.add(ingredient)
        # Nutrition Info
        NutritionInfo.objects.create(
            menu_item=menu_item,
            calories=prod.get("Calories"),
            protein=prod.get("Protein"),
            carbs=prod.get("Carbs"),
            trans_fat=prod.get("TransFat"),
            saturated_fat=prod.get("SaturatedFat"),
            unsaturated_fat=prod.get("UnsaturatedFat"),
            sugar=prod.get("Sugar"),
            fiber=prod.get("Fiber"),
            sodium=prod.get("Sodium"),
        )