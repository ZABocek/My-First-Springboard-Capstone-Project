import requests
from api_keys import KEY  # Import the API key from secrets.py

BASE_URL = "https://www.thecocktaildb.com/api/json/v2"

def get_cocktail_by_name(cocktail_name):
    url = f"{BASE_URL}/{KEY}/search.php?s={cocktail_name}"  # Include the API key in the URL
    response = requests.get(url)
    
    if response.status_code == 200:
        return response.json()
    else:
        return None
