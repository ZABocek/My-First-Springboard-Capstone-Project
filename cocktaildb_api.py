# cocktaildb_api.py

# Import necessary libraries
import requests  # For synchronous HTTP requests
import httpx  # For asynchronous HTTP requests
import asyncio  # For asynchronous programming
import backoff  # For handling retries with exponential backoff

# Define the base URL for the cocktail API
BASE_URL = "https://www.thecocktaildb.com/api/json/v1/1"

# Function to search for an ingredient by name
def search_ingredient(ingredient_name):
    # Define the API endpoint for searching ingredients
    url = f"{BASE_URL}/search.php"
    # Send a GET request to the API with the ingredient name as a parameter
    response = requests.get(url, params={"i": ingredient_name})
    
    # Check if the response status code is 200 (OK)
    if response.status_code == 200:
        # Return the JSON content of the response
        return response.json()
    else:
        # Return None if the request was not successful
        return None

# Asynchronous function to list all ingredients from the API
async def list_ingredients():
    # Define the API endpoint for listing ingredients
    url = f"{BASE_URL}/list.php?i=list"
    try:
        # Use httpx.AsyncClient to send a GET request asynchronously
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            # Raise an exception for 4XX/5XX responses
            response.raise_for_status()
            
            # Extract the list of ingredients from the response JSON
            ingredients = response.json().get('drinks', [])
            # Sort the ingredients alphabetically by their name
            sorted_ingredients = sorted(ingredients, key=lambda x: x['strIngredient1'])
            # Return the sorted list of ingredients
            return {"drinks": sorted_ingredients}
    except httpx.RequestError as exc:
        print(f"An error occurred while requesting {exc.request.url!r}.")
        # Handle the error or log it as appropriate
        return None
    except httpx.HTTPStatusError as exc:
        print(f"Error response {exc.response.status_code} while requesting {exc.request.url!r}.")
        # Handle the error or log it as appropriate
        return None

# Asynchronous function to get cocktails by their first letter from the API
async def get_cocktails_by_first_letter(letter):
    # Define the API endpoint for searching cocktails by first letter
    url = f"{BASE_URL}/search.php?f={letter}"
    try:
        # Define a timeout for the request
        timeout = httpx.Timeout(10.0, connect=5.0)
        
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(url)
            # Raise an exception for 4XX/5XX responses
            response.raise_for_status()
            
            # Extract the list of cocktails from the response JSON
            cocktails = response.json().get('drinks', [])
            return cocktails

    except httpx.RequestError as exc:
        print(f"An error occurred while requesting {exc.request.url!r}.")
        # Handle the error or log it as appropriate
        return None
    except httpx.HTTPStatusError as exc:
        print(f"Error response {exc.response.status_code} while requesting {exc.request.url!r}.")
        # Handle the error or log it as appropriate
        return None

# Function to look up a cocktail by its ID
def lookup_cocktail(cocktail_id):
    # Define the API endpoint for looking up a cocktail by ID
    url = f"{BASE_URL}/lookup.php"
    # Send a GET request to the API with the cocktail ID as a parameter
    response = requests.get(url, params={"i": cocktail_id})
    
    # Check if the response status code is 200 (OK)
    if response.status_code == 200:
        # Return the JSON content of the response
        return response.json()
    else:
        # Return None if the request was not successful
        return None

# Asynchronous function to get a combined list of cocktails by querying multiple letters
async def get_combined_cocktails_list():
    # Define the letters to query for cocktails
    letters = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', 'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z']
    # Limit the number of concurrent tasks using a semaphore
    semaphore = asyncio.Semaphore(10)

    # Define a helper function to limit concurrent requests
    async def limited_get_cocktails_by_first_letter(l):
        async with semaphore:
            return await get_cocktails_by_first_letter(l)

    # Create a list of tasks for each letter
    tasks = [limited_get_cocktails_by_first_letter(letter) for letter in letters]
    # Run the tasks concurrently and gather the results
    cocktail_lists = await asyncio.gather(*tasks)

    # Combine all cocktail lists into a single list, excluding None values
    combined_cocktails = [cocktail for cocktail_list in cocktail_lists if cocktail_list for cocktail in cocktail_list]

    for cocktail_list in cocktail_lists:
        if cocktail_list:
            combined_cocktails.extend(cocktail_list)

    # Create a distinct list of cocktails based on their IDs and names
    distinct_cocktails = {(cocktail['idDrink'], cocktail['strDrink']) for cocktail in combined_cocktails}

    # Return the sorted list of distinct cocktails by their names
    return sorted(list(distinct_cocktails), key=lambda x: x[1])

# Asynchronous function to fetch and prepare the list of cocktails
async def fetch_and_prepare_cocktails():
    # Get the combined list of cocktails
    cocktails = await get_combined_cocktails_list()
    # Further process the list if needed before returning it
    return cocktails

# Function to get the details of a cocktail by its ID
def get_cocktail_detail(cocktail_id):
    # Define the API endpoint for looking up a cocktail by ID
    url = f"{BASE_URL}/lookup.php?i={cocktail_id}"
    # Send a GET request to the API
    response = requests.get(url)
    # Check if the response status code is 200 (OK)
    if response.status_code == 200:
        # Return the first drink in the 'drinks' list from the response JSON
        return response.json().get('drinks', [])[0]
    return None

# Function to get a random cocktail from the API
def get_random_cocktail():
    # Define the endpoint URL for getting a random cocktail
    endpoint = "https://www.thecocktaildb.com/api/json/v1/1/random.php"
    # Send a GET request to the API
    response = requests.get(endpoint)
    # Parse the JSON response data
    data = response.json()
    
    # Check if the response contains the 'drinks' key with data
    if data and 'drinks' in data and data['drinks']:
        # Return the first drink in the 'drinks' list
        return data['drinks'][0]
    else:
        # Return None if no drinks are found
        return None
