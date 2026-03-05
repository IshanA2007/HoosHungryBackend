from django.urls import path
from . import views

urlpatterns = [
    path('week/', views.get_week_plan, name='get_week_plan'),
    path('daily/', views.get_daily_plan, name='get_daily_plan'),
    path('add-item/', views.add_meal_item, name='add_meal_item'),
    path('item/<int:item_id>/', views.update_meal_item, name='update_meal_item'),
    path('item/<int:item_id>/delete/', views.delete_meal_item, name='delete_meal_item'),
    path('goals/', views.update_plan_goals, name='update_plan_goals'),
    path('history/', views.get_history, name='get_history'),
]