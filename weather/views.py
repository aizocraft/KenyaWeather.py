import os
import requests
from django.shortcuts import render, redirect  # Added redirect here
from dotenv import load_dotenv
from geopy.geocoders import Nominatim
from datetime import datetime
import json
from django.http import JsonResponse

load_dotenv()

# Kenyan cities data for autocomplete
with open(os.path.join(os.path.dirname(__file__), 'data/kenyan_cities.json')) as f:
    KENYAN_CITIES = json.load(f)

def get_location(request):
    """Enhanced location detection with multiple fallbacks"""
    # Try browser geolocation first
    lat = request.GET.get('lat')
    lon = request.GET.get('lon')
    if lat and lon:
        try:
            locator = Nominatim(user_agent="kenyaweather")
            location = locator.reverse(f"{lat}, {lon}")
            address = location.raw.get('address', {})
            return {
                'lat': lat,
                'lon': lon,
                'city': address.get('city') or address.get('town') or address.get('village') or "Your Location",
                'country': address.get('country', '')
            }
        except Exception as e:
            print(f"Geolocation error: {e}")

    # Fallback to Nairobi
    return {
        'lat': -1.286389,
        'lon': 36.817223,
        'city': "Nairobi",
        'country': "Kenya"
    }

def get_weather_data(lat, lon):
    """Fetch weather data from OpenWeather API"""
    api_key = os.getenv("OPENWEATHER_API_KEY")
    url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={api_key}&units=metric"
    response = requests.get(url)
    return response.json()

def get_forecast_data(lat, lon):
    """Fetch 5-day forecast data"""
    api_key = os.getenv("OPENWEATHER_API_KEY")
    url = f"https://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={api_key}&units=metric"
    response = requests.get(url)
    return response.json()

def home(request):
    """Main view with current weather and forecast"""
    location = get_location(request)
    weather_data = get_weather_data(location['lat'], location['lon'])
    forecast_data = get_forecast_data(location['lat'], location['lon'])
    
    # Process forecast data
    daily_forecast = {}
    for item in forecast_data['list']:
        date = item['dt_txt'].split()[0]
        if date not in daily_forecast:
            daily_forecast[date] = {
                'temps': [],
                'icons': [],
                'descriptions': set()
            }
        daily_forecast[date]['temps'].append(item['main']['temp'])
        daily_forecast[date]['icons'].append(item['weather'][0]['icon'])
        daily_forecast[date]['descriptions'].add(item['weather'][0]['description'])
    
    # Get next 5 days forecast
    sorted_dates = sorted(daily_forecast.keys())[:5]
    forecast = []
    for date in sorted_dates:
        day_data = daily_forecast[date]
        forecast.append({
            'date': datetime.strptime(date, "%Y-%m-%d").strftime("%a, %b %d"),
            'min_temp': min(day_data['temps']),
            'max_temp': max(day_data['temps']),
            'icon': max(set(day_data['icons']), key=day_data['icons'].count),
            'description': ', '.join(day_data['descriptions'])
        })
    
    context = {
        'city': weather_data.get('name', location['city']),
        'country': location.get('country', 'Kenya'),
        'current_temp': weather_data['main']['temp'],
        'feels_like': weather_data['main']['feels_like'],
        'humidity': weather_data['main']['humidity'],
        'wind_speed': weather_data['wind']['speed'],
        'wind_direction': weather_data['wind'].get('deg', 0),
        'pressure': weather_data['main']['pressure'],
        'visibility': weather_data.get('visibility', 0) / 1000 if weather_data.get('visibility') else 0,
        'sunrise': datetime.fromtimestamp(weather_data['sys']['sunrise']).strftime("%H:%M"),
        'sunset': datetime.fromtimestamp(weather_data['sys']['sunset']).strftime("%H:%M"),
        'description': weather_data['weather'][0]['description'],
        'icon': weather_data['weather'][0]['icon'],
        'forecast': forecast,
        'kenyan_cities': KENYAN_CITIES,
        'last_updated': datetime.now().strftime("%H:%M %p")
    }
    return render(request, 'weather/index.html', context)

def city_search(request):
    """Handle city search requests"""
    if request.method == 'POST':
        city = request.POST.get('city')
        
        # First try to find in our predefined Kenyan cities
        for loc in KENYAN_CITIES:
            if city.lower() == loc['name'].lower():
                return redirect(f"/?lat={loc['lat']}&lon={loc['lon']}")
        
        # If not found in our list, try geocoding
        try:
            locator = Nominatim(user_agent="kenyaweather")
            location = locator.geocode(f"{city}, Kenya")
            if location:
                return redirect(f"/?lat={location.latitude}&lon={location.longitude}")
            else:
                # If geocoding fails, redirect to Nairobi
                return redirect('/')
        except Exception as e:
            print(f"Search error: {e}")
            return redirect('/')
    
    return redirect('home')

def autocomplete(request):
    """Provide autocomplete suggestions"""
    term = request.GET.get('term', '')
    suggestions = [loc['name'] for loc in KENYAN_CITIES if term.lower() in loc['name'].lower()]
    return JsonResponse(suggestions, safe=False)