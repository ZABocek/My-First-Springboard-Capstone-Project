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
        ingredients = response.json().get('drinks', [])
        sorted_ingredients = sorted(ingredients, key=lambda x: x['strIngredient1'])
        return {"drinks": sorted_ingredients}
    else:
        return None

def lookup_cocktail(cocktail_id):
    url = f"{BASE_URL}/lookup.php"
    response = requests.get(url, params={"i": cocktail_id})
    
    if response.status_code == 200:
        return response.json()
    else:
        return None
    
def get_cocktails_list():
    ingredients_list = list_ingredients()
    if not ingredients_list:
        return []
    cocktails = set()
    for ingredient in ingredients_list.get('drinks', []):
        ingredient_name = ingredient['strIngredient1']
        response = requests.get(BASE_URL + f'/filter.php?i={ingredient_name}')
        if response.status_code == 200:
            drinks = response.json().get('drinks', [])
            for drink in drinks:
                cocktails.add((drink['idDrink'], drink['strDrink']))
    # Sort the list of cocktails by their names before returning
    return sorted(list(cocktails), key=lambda x: x[1])

def get_cocktail_detail(cocktail_id):
    url = f"{BASE_URL}/lookup.php?i={cocktail_id}"  # Fixed URL
    response = requests.get(url)
    if response.status_code == 200:
        return response.json().get('drinks', [])[0]  # Assuming that details will always be present for a valid id.
    return None
