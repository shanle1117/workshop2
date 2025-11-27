from django.urls import path
from . import views

urlpatterns = [
    path('', views.chatbot_view, name='chatbot_home'),
    path('api/', views.chatbot_api, name='chatbot_api'),
]
