import os
import math
import requests
from django.shortcuts import render, redirect
from dotenv import load_dotenv
from datetime import datetime
import json
from django.http import JsonResponse, HttpResponse
from weather.data.cities import KENYAN_CITIES

load_dotenv()

def find_nearest_city(lat, lon, max_distance_km=100):
    """Find the nearest city from our Kenyan cities data"""
    nearest = None
    min_distance = float('inf')
    
    for city in KENYAN_CITIES:
        # Calculate distance using Haversine formula
        distance = haversine_distance(float(lat), float(lon), city['lat'], city['lon'])
        
        if distance < min_distance and distance <= max_distance_km:
            min_distance = distance
            nearest = city
    
    return nearest, min_distance

def haversine_distance(lat1, lon1, lat2, lon2):
    """Calculate distance between two points in kilometers"""
    R = 6371  # Earth's radius in kilometers
    
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    
    a = math.sin(delta_lat / 2) ** 2 + \
        math.cos(lat1_rad) * math.cos(lat2_rad) * \
        math.sin(delta_lon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    return R * c

def get_location(request):
    """Get location from request parameters or fallback to Nairobi"""
    lat = request.GET.get('lat')
    lon = request.GET.get('lon')
    
    if lat and lon:
        try:
            lat = float(lat)
            lon = float(lon)
            
            # Try to find nearest city
            nearest_city, distance = find_nearest_city(lat, lon)
            
            if nearest_city and distance < 50:  # Within 50km of known city
                return {
                    'lat': lat,
                    'lon': lon,
                    'city': nearest_city['name'],
                    'country': 'Kenya'
                }
            else:
                # Use coordinates as location name
                return {
                    'lat': lat,
                    'lon': lon,
                    'city': f"Location ({round(lat, 2)}°, {round(lon, 2)}°)",
                    'country': 'Kenya'
                }
        except (ValueError, TypeError) as e:
            print(f"Invalid coordinates: {e}")
    
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
    if not api_key:
        print("ERROR: OPENWEATHER_API_KEY not found in environment variables")
        return None
    
    url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={api_key}&units=metric"
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Weather API error: {e}")
        return None

def get_forecast_data(lat, lon):
    """Fetch 5-day forecast data"""
    api_key = os.getenv("OPENWEATHER_API_KEY")
    if not api_key:
        return None
    
    url = f"https://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={api_key}&units=metric"
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Forecast API error: {e}")
        return None

def home(request):
    """Main view with current weather and forecast"""
    location = get_location(request)
    
    # Get weather data
    weather_data = get_weather_data(location['lat'], location['lon'])
    forecast_data = get_forecast_data(location['lat'], location['lon'])
    
    # Handle API errors gracefully
    if not weather_data:
        return render(request, 'weather/error.html', {
            'message': 'Unable to fetch weather data. Please try again later.',
            'kenyan_cities': KENYAN_CITIES
        })
    
    # Process forecast data
    daily_forecast = {}
    if forecast_data and 'list' in forecast_data:
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
    forecast = []
    sorted_dates = sorted(daily_forecast.keys())[:5]
    for date in sorted_dates:
        day_data = daily_forecast[date]
        forecast.append({
            'date': datetime.strptime(date, "%Y-%m-%d").strftime("%a, %b %d"),
            'min_temp': round(min(day_data['temps'])),
            'max_temp': round(max(day_data['temps'])),
            'icon': max(set(day_data['icons']), key=day_data['icons'].count),
            'description': ', '.join(day_data['descriptions'])
        })
    
    context = {
        'city': weather_data.get('name', location['city']),
        'country': location.get('country', 'Kenya'),
        'current_temp': round(weather_data['main']['temp']),
        'feels_like': round(weather_data['main']['feels_like']),
        'humidity': weather_data['main']['humidity'],
        'wind_speed': round(weather_data['wind']['speed']),
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
        
        # Search in our predefined Kenyan cities
        for loc in KENYAN_CITIES:
            if city.lower() == loc['name'].lower():
                return redirect(f"/?lat={loc['lat']}&lon={loc['lon']}")
        
        # If not found, try partial match
        for loc in KENYAN_CITIES:
            if city.lower() in loc['name'].lower():
                return redirect(f"/?lat={loc['lat']}&lon={loc['lon']}")
        
        # If still not found, redirect to Nairobi
        return redirect('/')
    
    return redirect('home')

def autocomplete(request):
    """Provide autocomplete suggestions"""
    term = request.GET.get('term', '').lower()
    suggestions = [loc['name'] for loc in KENYAN_CITIES if term in loc['name'].lower()]
    return JsonResponse(suggestions[:10], safe=False)  # Limit to 10 suggestions

def health(request):
    """Health check endpoint"""
    return HttpResponse("OK", status=200)