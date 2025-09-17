from django.db import models

# Create your models here.
class DiningHall(models.Model):
    name = models.CharField(max_length=200)
    scrape_url = models.URLField()
    
    def __str__(self):
        return self.name

class Day(models.Model):
    date = models.DateField()
    day_name = models.CharField(max_length=20, default="")
    open_time = models.TimeField()
    close_time = models.TimeField()
    dining_hall = models.ForeignKey(DiningHall, on_delete=models.CASCADE, related_name="days")

    def __str__(self):
        return f"{self.date} ({self.open_time.strftime('%H:%M')} - {self.close_time.strftime('%H:%M')})"


class Period(models.Model):
    type = models.CharField(max_length=200)
    vendor_id = models.CharField(max_length=10) # something like 1423
    start_time = models.TimeField()
    end_time = models.TimeField()
    day = models.ForeignKey(Day, on_delete=models.CASCADE, related_name="periods")

    def __str__(self):
        return f"{self.type} ({self.start_time.strftime('%H:%M')} - {self.end_time.strftime('%H:%M')})"


class Station(models.Model):
    name = models.CharField(max_length=100)
    number = models.CharField(max_length=10) # something like 22683
    period = models.ForeignKey(Period, on_delete=models.CASCADE, related_name="stations")

    def __str__(self):
        return self.name


class Allergen(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name
    
class MenuItem(models.Model):
    station = models.ForeignKey(Station, on_delete=models.CASCADE, related_name="menu_items")
    allergens = models.ManyToManyField(Allergen, related_name="menu_items", blank=True)
    is_gluten = models.BooleanField(default=False)
    is_vegan = models.BooleanField(default=False)
    is_vegetarian = models.BooleanField(default=False)
    item_name = models.CharField(max_length=200)
    item_description = models.TextField(blank=True, null=True)
    ingredients = models.ManyToManyField("Ingredient", related_name="menu_items", blank=True)
    item_category = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return self.item_name


class Ingredient(models.Model):
    name = models.CharField(max_length=200, unique=True)

    def __str__(self):
        return self.name

class NutritionInfo(models.Model):
    calories = models.DecimalField(max_digits=6, decimal_places=2, blank=True, null=True)
    protein = models.DecimalField(max_digits=6, decimal_places=2, blank=True, null=True)
    carbs = models.DecimalField(max_digits=6, decimal_places=2, blank=True, null=True)
    trans_fat = models.DecimalField(max_digits=6, decimal_places=2, blank=True, null=True)
    saturated_fat = models.DecimalField(max_digits=6, decimal_places=2, blank=True, null=True)
    unsaturated_fat = models.DecimalField(max_digits=6, decimal_places=2, blank=True, null=True)
    sugar = models.DecimalField(max_digits=6, decimal_places=2, blank=True, null=True)
    fiber = models.DecimalField(max_digits=6, decimal_places=2, blank=True, null=True)
    sodium = models.DecimalField(max_digits=6, decimal_places=2, blank=True, null=True)
    menu_item = models.OneToOneField(MenuItem, on_delete=models.CASCADE, related_name="nutrition_info")


    def __str__(self):
        fields = []
        if self.calories is not None:
            fields.append(f"Calories: {self.calories}")
        if self.protein is not None:
            fields.append(f"Protein: {self.protein}g")
        if self.carbs is not None:
            fields.append(f"Carbs: {self.carbs}g")
        if self.trans_fat is not None:
            fields.append(f"Trans Fat: {self.trans_fat}g")
        if self.saturated_fat is not None:
            fields.append(f"Saturated Fat: {self.saturated_fat}g")
        if self.unsaturated_fat is not None:
            fields.append(f"Unsaturated Fat: {self.unsaturated_fat}g")
        if self.sugar is not None:
            fields.append(f"Sugar: {self.sugar}g")
        if self.fiber is not None:
            fields.append(f"Fiber: {self.fiber}g")
        if self.sodium is not None:
            fields.append(f"Sodium: {self.sodium}mg")

        return ", ".join(fields) if fields else "No nutrition info"
