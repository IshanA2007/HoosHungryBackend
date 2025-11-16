from django.urls import path
from . import views

urlpatterns = [
    path('hello/', views.hello_world, name='hello_world'),
    path('menu_info/', views.menu_info, name='menu_info'),
    path('available_periods/', views.available_periods, name='available_periods'),
]