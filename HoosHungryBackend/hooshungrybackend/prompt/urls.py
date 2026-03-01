from django.urls import path
from . import views

urlpatterns = [
    path('chat/', views.ChatView.as_view(), name='prompt-chat'),
    path('history/', views.HistoryView.as_view(), name='prompt-history'),
]
