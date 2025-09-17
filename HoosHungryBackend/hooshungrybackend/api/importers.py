from django.utils.dateparse import parse_date
from django.utils.dateparse import parse_time
from datetime import datetime
from .models import DiningHall, Day, Period, Station, Allergen, MenuItem, NutritionInfo
from decimal import Decimal, InvalidOperation

def load_menu_data(hall_name: str, data: dict, hours: dict):
    if hall_name not in ["ohill", "newcomb", "runk"]:
        raise ValueError("Invalid dining hall name")

    if hall_name == "ohill":
        hall, _ = DiningHall.objects.update_or_create(
        name="ohill",
        defaults={"scrape_url": "https://virginia.campusdish.com/en/locationsandmenus/observatoryhilldiningroom/"}
    )
    elif hall_name == "newcomb":
        hall, _ = DiningHall.objects.update_or_create(
        name="newcomb",
        defaults={"scrape_url": "https://virginia.campusdish.com/en/locationsandmenus/freshfoodcompany/"}
    )
    
    elif hall_name == "runk":
        hall, _ = DiningHall.objects.update_or_create(
        name="runk",
        defaults={"scrape_url": "https://virginia.campusdish.com/en/locationsandmenus/runk/"}
    )
    
    update_dining_hall(hall, data, hours)

def update_dining_hall(hall: DiningHall, data: dict, hours: dict):

    # Create a new day entry
    date_str = data["date"]  # e.g., "09/16/2024"
    date_obj = datetime.strptime(date_str, "%m/%d/%Y").date()
    day_name = date_obj.strftime("%A")
    day_obj = Day.objects.create(
        date=date_obj,
        day_name=day_name,
        open_time=hours["open_time"], 
        close_time=hours["close_time"], 
        dining_hall=hall
    )

    
    #Loop through periods and add them to Day

    for period_id, period_data in data["periods"].items():
        #{"1421": {"name": "Breakfast", "raw": {"Menu": {}}}}
        add_period_to_day(period_id, period_data, hours, day_obj)

def add_period_to_day(period_id, period_data: dict, hours: dict, day: Day):

    period_name = period_data["name"]
    vendor_id = period_id
    start_time = hours["periods"][period_id]["start_time"]
    end_time = hours["periods"][period_id]["end_time"]

    period_obj = Period.objects.create(
        name=period_name,
        vendor_id=vendor_id,
        start_time=parse_time(start_time),
        end_time=parse_time(end_time),
        day=day
    )

    station_data = period_data["raw"]["Menu"]["MenuStations"]
    product_data = period_data["raw"]["Menu"]["MenuProducts"]

    

    add_stations_to_period(station_data, product_data, period_id, period_data, period_obj)
    
def add_stations_to_period(station_data: list, product_data: list, period_id: str, data: dict, period_obj: Period):

    # Create all stations for this period
    station_objs = {}
    for station in station_data:
        if station["PeriodId"] == period_id:
            station_obj = Station.objects.create(
                name=station["Name"],
                number=station["StationId"],
                period=period_obj
            )
            station_objs[station["StationId"]] = station_obj
            
    add_menu_items_to_station(station_objs, product_data)

def add_menu_items_to_station(station_objs: dict, product_data: list):
            
    for product in product_data:
        station_id = product["StationId"]
        station_obj = station_objs.get(station_id)
        if not station_obj:
            continue  # Station not found, skip this product
        prod_info = product.get("Product")
        if not prod_info:
            continue  # No product info available, skip
        item_name = prod_info.get("MarketingName") or "Unnamed Item"
        item_description = prod_info.get("ShortDescription") or ""

        # Create MenuItem and link to Station
        menu_item = MenuItem.objects.create(
            item_name=item_name,
            item_description=item_description,
            station=station_obj
        )

        # Allergens from AvailableFilters (e.g., ContainsEggs)
        available_filters = prod_info.get("AvailableFilters", {})
        for filter_key, value in available_filters.items():
            if value is True and filter_key.startswith("Contains"):
                allergen_name = filter_key.replace("Contains", "")
                if allergen_name:
                    allergen_obj, _ = Allergen.objects.get_or_create(name=allergen_name)
                    menu_item.allergens.add(allergen_obj)
        if "information is not available" in prod_info.get("AllergenStatement"):
            allergen_obj, _ = Allergen.objects.get_or_create(name="Information Not Available")
            menu_item.allergens.add(allergen_obj)

        # Ingredients from IngredientStatement
        menu_item.ingredients = prod_info.get("IngredientStatement", "")
        menu_item.save()

        # NutritionInfo from NutritionalTree
        nutritional_tree = prod_info.get("NutritionalTree", [])
        nutrition_info = NutritionInfo.objects.create(menu_item=menu_item)
        def parse_nutrition(tree):
            for entry in tree:
                name = entry.get("Name")
                value = entry.get("Value")
                # Set as attribute if matches NutritionInfo fields
                if name and hasattr(nutrition_info, name.lower().replace(" ", "_")):
                    try:
                        setattr(nutrition_info, name.lower().replace(" ", "_"), Decimal(value))
                    except (InvalidOperation, ValueError, TypeError):
                        pass
                # Recursively parse sublists
                sublist = entry.get("SubList")
                if sublist: 
                    parse_nutrition(sublist)
        parse_nutrition(nutritional_tree)
        nutrition_info.save()
        
        

        

