# cocktaildb_api.py
import requests

BASE_URL = "https://www.thecocktaildb.com/api/json/v1/1"

def search_ingredient(ingredient_name):
    url = f"{BASE_URL}/search.php"
    response = requests.get(url, params={"i": ingredient_name})
    
    if response.status_code == 200:
        return response.json()
    else:
        return None

def list_ingredients():
    url = f"{BASE_URL}/list.php?i=list"
    response = requests.get(url)
    
    if response.status_code == 200:
        return response.json()
    else:
        return None

def lookup_cocktail(cocktail_id):
    url = f"{BASE_URL}/lookup.php"
    response = requests.get(url, params={"i": cocktail_id})
    
    if response.status_code == 200:
        return response.json()
    else:
        return None
