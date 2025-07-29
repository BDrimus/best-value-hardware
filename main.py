import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.firefox.options import Options

import time
import base64
import requests
import sys

import config
from models import GPUData, EbayResult

# --- Constants ---
# Find scores on this site: https://www.videocardbenchmark.net/GPU_mega_page.html
MIN_G3D_MARK = 14000
BENCHMARK_URL = "https://www.videocardbenchmark.net/GPU_mega_page.html"
# Keywords to exclude from eBay titles to avoid accessories/parts
EXCLUDE_KEYWORDS = [
    "only", 'faulty', "box", "fan", "bios chip", "no gpu", "heatsink only", "cooler", "packaging", "cooling system", "water cooled block", "sticker", "holder", "bracket", "backplate", "headset", "monitor", "cable", "badge", "magnet", "blender", "mod",
    "alphacool", "adapter", "water block", "nvlink", "connector", "keychain", "accessory", "stouchi", "displayport", "mount", "battery", "waterblock", "ekwb", "replacement", "charger", "mouse mat", "pad", "power supply", "mousemat", "memory mesh",
    "heatsink", "power supply", "alienware", 
]
BASE_URL = "https://api.ebay.com/buy/browse/v1/item_summary/search"

desired_condition_ids = [1000, 3000]  # New, Used

condition_ids_values = "|".join(map(str, desired_condition_ids))

filter_params = f"conditionIds:{{{condition_ids_values}}},itemLocationCountry:GB"
# filter_params = f"conditionIds:{{{condition_ids_values}}},itemLocationCountry:GB,deliveryCountry:GB"

def setup_driver(url):
    firefox_options = Options()
    firefox_options.add_argument("--headless")
    driver = webdriver.Firefox(options=firefox_options)
    driver.get(url)
    return driver


def click_buttons(driver):
    wait = WebDriverWait(driver, 20)
    button = wait.until(EC.element_to_be_clickable(
        (By.XPATH, '//*[@id="qc-cmp2-ui"]/div[2]/div/button[2]')))
    button.click()

    button = wait.until(EC.element_to_be_clickable(
        (By.XPATH, '//*[@id="cputable_length"]/label/select/option[4]')))
    button.click()

    button = wait.until(EC.element_to_be_clickable(
        (By.XPATH, '//*[@id="cputable"]/thead/tr/th[3]')))
    button.click()
    button.click()


def get_gpu_data(driver):
    table = driver.find_element(By.XPATH, '//*[@id="cputable"]/tbody')
    rows = table.find_elements(By.TAG_NAME, 'tr')
    data = []
    for row in rows:
        cells = row.find_elements(By.TAG_NAME, 'td')
        row_data = GPUData(
            name=cells[1].text,
            g3d_mark=cells[2].text,
        )

        g3d_mark = int(row_data.g3d_mark.replace(',', ''))

        if g3d_mark < MIN_G3D_MARK:
            break

        data.append(row_data)

    return data


def is_gpu_model_in_title(gpu_model, title):
    """
    Checks if all the essential parts of the GPU model name are present as whole words
    in the listing title, while ignoring common brand prefixes.
    """
    model_parts = gpu_model.lower().split()
    title_lower = title.lower()

    # Define brand prefixes that are often omitted by sellers
    prefixes_to_ignore = ['geforce', 'radeon', 'intel', 'arc']
    
    # Create a list of only the essential keywords we must find
    essential_parts = [part for part in model_parts if part not in prefixes_to_ignore]

    # Check if ALL essential parts exist as whole words in the title
    try:
        return all(re.search(r'\b' + re.escape(part) + r'\b', title_lower) for part in essential_parts)
    except re.error:
        # Fallback for edge cases where a part might be empty or invalid
        return False
    

def fetch_gpu_from_ebay(data, access_token, exclude=[], Marketplace_ID="EBAY_GB"):

    headers = {
        'Authorization': f"Bearer {access_token}",
        'X-EBAY-C-MARKETPLACE-ID': Marketplace_ID
    }

    ebay_results = []
    batch_size = 5  # Process GPUs in batches to reduce API calls

    for i in range(0, len(data), batch_size):
        batch = data[i:i + batch_size]

        for row in batch:
            title = 'N/A'
            price = 'N/A'
            shipping_cost = 'N/A'
            listing_url = 'N/A'
            total_price = float('inf') # Use infinity for sorting purposes if needed

            keyword = row.name
            url = (f"https://api.ebay.com/buy/browse/v1/item_summary/search"
               f"?q={keyword}"
            #    f"&category_ids=27386"
               f"&limit=50"
               f"&filter={filter_params}"
               f"&sort=price")

            max_retries = 5
            retry_delay = 5

            for attempt in range(max_retries):
                try:
                    response = requests.get(url, headers=headers)
                    response.raise_for_status()
                    items = response.json().get('itemSummaries', [])
                    break
                except requests.exceptions.RequestException as e:
                    print(f"API call failed (attempt {attempt + 1}/{max_retries}): {e}")
                    time.sleep(retry_delay * (2 ** attempt))  # Exponential backoff
            else:
                print("Max retries reached. Skipping this keyword.")
                continue

            first_valid_item = None
            for item in items:
                if any(ex in item['title'].lower() for ex in exclude) or not is_gpu_model_in_title(keyword, item['title']):
                    continue
                else:
                    first_valid_item = item
                    break

            if first_valid_item:
                title = first_valid_item['title']
                price = float(first_valid_item['price']['value'])  # Update price if first_valid_item is found
                shipping_cost = 0
                if 'shippingOptions' in first_valid_item and first_valid_item['shippingOptions']:
                    shipping_option = first_valid_item['shippingOptions'][0]
                    shipping_cost = float(shipping_option['shippingCost']['value']) if 'shippingCost' in shipping_option else 0
                total_price = price + shipping_cost
                listing_url = first_valid_item['itemWebUrl']

            result = EbayResult(
                name=keyword,
                title=title,
                price=price,
                shipping_cost=shipping_cost,
                url=listing_url,
            )
            ebay_results.append(result)



        print(f"Processed batch {i // batch_size + 1}/{-(-len(data) // batch_size)}")
        time.sleep(1)  # Longer delay between batches

    return ebay_results


def calculate_performance_to_price_ratio(ebay_results, data):
    for result, row_data in zip(ebay_results, data):
        if result.price != 'N/A' and result.shipping_cost != 'N/A':
            g3d_mark = int(row_data.g3d_mark.replace(',', ''))
            price = result.price
            shipping_cost = result.shipping_cost
            total_price = price + shipping_cost
            result.performance_to_price_ratio = g3d_mark / total_price
        else:
            result.performance_to_price_ratio = 0
    return ebay_results


def display_top_deals(ebay_results, data, n=10):
    sorted_results = sorted(
        ebay_results, key=lambda x: x.performance_to_price_ratio, reverse=True)
    top_deals = sorted_results[:n]

    print(f"\nTop {n} best deals:")
    for rank, deal in enumerate(top_deals, start=1):
        gpu_data = next((d for d in data if d.name == deal.name), None)
        g3d_mark = gpu_data.g3d_mark if gpu_data else "N/A"
        print(f"{rank}. {deal.name} - {deal.title}")
        print(
            f"   Price: {deal.price} - Shipping Cost: {deal.shipping_cost} - Performance-to-Price Ratio: {deal.performance_to_price_ratio:.2f} - G3D Mark: {g3d_mark}")
        print(f"   URL: {deal.url}\n")


def get_ebay_access_token():
    """
    Retrieves the eBay API access token.
    """
    print("Getting eBay API access token...")
    credentials = f"{config.EBAY_APP_ID}:{config.EBAY_CERT_ID}"
    encoded_credentials = base64.b64encode(credentials.encode()).decode()

    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": f"Basic {encoded_credentials}"
    }

    data = {
        "grant_type": "client_credentials",
        "scope": "https://api.ebay.com/oauth/api_scope"
    }

    try:
        response = requests.post("https://api.ebay.com/identity/v1/oauth2/token", headers=headers, data=data)
        response.raise_for_status()  # This will raise an exception for HTTP error codes
        token_response = response.json()
        access_token = token_response.get("access_token")

        if not access_token:
            print("Failed to retrieve access token: 'access_token' key not found in response.")
            sys.exit(1) # Exit the script if no token
        
        print("Successfully obtained access token.")
        return access_token

    except requests.exceptions.RequestException as e:
        print(f"Failed to retrieve access token. Error: {e}")
        print(f"Response body: {response.text}")
        sys.exit(1) # Exit the script on error


def main():
    start_time = time.time()

    print("Starting the script...")
    url = "https://www.videocardbenchmark.net/GPU_mega_page.html"
    driver = setup_driver(url)

    print("Clicking buttons...")
    click_buttons(driver)

    print("Fetching GPU data...")
    gpu_data = get_gpu_data(driver)

    print("Fetching GPU deals from eBay...")

    ebay_access_token = get_ebay_access_token()

    print("ebay_access_token", ebay_access_token)

    ebay_results = fetch_gpu_from_ebay(gpu_data, ebay_access_token, exclude=EXCLUDE_KEYWORDS)

    print("Calculating performance-to-price ratios...")
    ebay_results = calculate_performance_to_price_ratio(ebay_results, gpu_data)

    print("\nGPU data:")
    for row in gpu_data:
        print(row)

    print("\neBay results:")
    for result in ebay_results:
        print(result)

    display_top_deals(ebay_results, gpu_data, n=10)

    end_time = time.time()
    elapsed_time = end_time - start_time
    print(f"\nThe script took {elapsed_time:.2f} seconds to complete.")

    # input("Press Enter to close the browser...") # For debugging


if __name__ == "__main__":
    main()
