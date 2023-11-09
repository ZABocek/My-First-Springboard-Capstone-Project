# cocktaildb_api.py
import requests
import httpx
import asyncio
import backoff

BASE_URL = "https://www.thecocktaildb.com/api/json/v1/1"

def search_ingredient(ingredient_name):
    url = f"{BASE_URL}/search.php"
    response = requests.get(url, params={"i": ingredient_name})
    
    if response.status_code == 200:
        return response.json()
    else:
        return None

async def list_ingredients():
    url = f"{BASE_URL}/list.php?i=list"
    try:
        # Use httpx.AsyncClient to send a GET request asynchronously
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            response.raise_for_status()  # This will raise an exception for 4XX/5XX responses
            
            ingredients = response.json().get('drinks', [])
            sorted_ingredients = sorted(ingredients, key=lambda x: x['strIngredient1'])
            return {"drinks": sorted_ingredients}
    except httpx.RequestError as exc:
        print(f"An error occurred while requesting {exc.request.url!r}.")
        # You might want to log the error or handle it differently in your application context
        return None
    except httpx.HTTPStatusError as exc:
        print(f"Error response {exc.response.status_code} while requesting {exc.request.url!r}.")
        # Similar to the above, handle or log the error as appropriate for your application
        return None
    
async def get_cocktails_by_first_letter(letter):
    url = f"{BASE_URL}/search.php?f={letter}"
    try:
        # Define a timeout for the request
        timeout = httpx.Timeout(10.0, connect=5.0)
        
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(url)
            response.raise_for_status()
            
            # Extract the cocktail data from the response
            cocktails = response.json().get('drinks', [])
            return cocktails

    except httpx.RequestError as exc:
        print(f"An error occurred while requesting {exc.request.url!r}.")
        return None
    except httpx.HTTPStatusError as exc:
        print(f"Error response {exc.response.status_code} while requesting {exc.request.url!r}.")
        return None

def lookup_cocktail(cocktail_id):
    url = f"{BASE_URL}/lookup.php"
    response = requests.get(url, params={"i": cocktail_id})
    
    if response.status_code == 200:
        return response.json()
    else:
        return None


async def get_combined_cocktails_list():
    # Choose the letters you want to query for. You can expand this range as needed.
    letters = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', 'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z']  # Add more letters based on your requirement
    # Limit the number of concurrent tasks if necessary
    semaphore = asyncio.Semaphore(10)  # adjust the number as needed

    async def limited_get_cocktails_by_first_letter(l):
        async with semaphore:
            return await get_cocktails_by_first_letter(l)

    tasks = [limited_get_cocktails_by_first_letter(letter) for letter in letters]
    cocktail_lists = await asyncio.gather(*tasks)


    # Combine all cocktail lists into a single list, excluding None values
    combined_cocktails = [cocktail for cocktail_list in cocktail_lists if cocktail_list for cocktail in cocktail_list]

    for cocktail_list in cocktail_lists:
        if cocktail_list:  # If the request was successful and we have a list
            combined_cocktails.extend(cocktail_list)

    # Now, you can create a distinct list of cocktails based on your needs, e.g., names
    distinct_cocktails = {(cocktail['idDrink'], cocktail['strDrink']) for cocktail in combined_cocktails}

    return sorted(list(distinct_cocktails), key=lambda x: x[1])  # Sort by cocktail name

async def fetch_and_prepare_cocktails():
    # Assuming get_combined_cocktails_list is defined in this script as well
    cocktails = await get_combined_cocktails_list()
    # You can further process the list here if needed before returning it
    return cocktails
def get_cocktail_detail(cocktail_id):
    url = f"{BASE_URL}/lookup.php?i={cocktail_id}"  # Fixed URL
    response = requests.get(url)
    if response.status_code == 200:
        return response.json().get('drinks', [])[0]  # Assuming that details will always be present for a valid id.
    return None

def get_random_cocktail():
    endpoint = "https://www.thecocktaildb.com/api/json/v1/1/random.php"
    response = requests.get(endpoint)
    data = response.json()
    
    if data and 'drinks' in data and data['drinks']:
        return data['drinks'][0]
    else:
        return None