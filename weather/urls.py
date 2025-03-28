from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('search/', views.city_search, name='city_search'),
    path('autocomplete/', views.autocomplete, name='autocomplete'),
]