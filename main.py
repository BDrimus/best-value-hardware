import pandas as pd
import re
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options

from bs4 import BeautifulSoup
from operator import itemgetter
from ebaysdk.finding import Connection as Finding
from ebaysdk.exception import ConnectionError

def setup_driver(url):
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    driver = webdriver.Chrome(options=chrome_options)
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
        row_data = {
            'name': cells[1].text,
            'g3d-mark': cells[2].text,
        }
        g3d_mark = int(row_data['g3d-mark'].replace(',', ''))

        if g3d_mark < 14000:
            break

        data.append(row_data)

    return data


def is_gpu_model_in_title(gpu_model, title):
    pattern = re.compile(r'\b' + re.escape(gpu_model.lower()) + r'\b')
    return bool(pattern.search(title.lower()))


def fetch_gpu_from_ebay(api, data, exclude=[]):
    ebay_results = []
    for row in data:
        keyword = row['name']
        payload = {
            'keywords': keyword,
            'categoryId': '27386',
            'itemFilter': [
                {'name': 'ListingType', 'value': 'FixedPrice'},
                {'name': 'Condition', 'value': ['1000', '3000']},
            ],
            'paginationInput': {
                'entriesPerPage': 10,
                'pageNumber': 1,
            },
            'sortOrder': 'PricePlusShippingLowest',
        }

        response = api.execute('findItemsAdvanced', payload)
        items = response.reply.searchResult.item if response.reply.searchResult._count != '0' else []

        first_valid_item = None
        for item in items:
            if any(ex in item.title.lower() for ex in exclude) or not is_gpu_model_in_title(keyword, item.title):
                continue
            else:
                first_valid_item = item
                break

        if first_valid_item:
            title = first_valid_item.title
            price = float(first_valid_item.sellingStatus.currentPrice.value)
            shipping_cost = float(first_valid_item.shippingInfo.shippingServiceCost.value) if hasattr(
                first_valid_item.shippingInfo, 'shippingServiceCost') else 0
            total_price = price + shipping_cost
            listing_url = first_valid_item.viewItemURL
        else:
            title = 'N/A'
            total_price = 'N/A'
            shipping_cost = 'N/A'
            listing_url = 'N/A'

        result = {'name': keyword, 'title': title, 'price': total_price,
                  'shipping_cost': shipping_cost, 'url': listing_url}
        ebay_results.append(result)

    return ebay_results


def calculate_performance_to_price_ratio(ebay_results, data):
    for result, row_data in zip(ebay_results, data):
        if result['price'] != 'N/A' and result['shipping_cost'] != 'N/A':
            g3d_mark = int(row_data['g3d-mark'].replace(',', ''))
            price = float(result['price'])
            shipping_cost = float(result['shipping_cost'])
            total_price = price + shipping_cost
            result['performance_to_price_ratio'] = g3d_mark / total_price
        else:
            result['performance_to_price_ratio'] = 0

    return ebay_results



def display_top_deals(ebay_results, data, n=10):
    sorted_results = sorted(
        ebay_results, key=lambda x: x['performance_to_price_ratio'], reverse=True)
    top_deals = sorted_results[:n]

    print(f"\nTop {n} best deals:")
    for rank, deal in enumerate(top_deals, start=1):
        gpu_data = next((d for d in data if d["name"] == deal["name"]), None)
        g3d_mark = gpu_data["g3d-mark"] if gpu_data else "N/A"
        print(f"{rank}. {deal['name']} - {deal['title']}")
        print(
            f"   Price: {deal['price']} - Shipping Cost: {deal['shipping_cost']} - Performance-to-Price Ratio: {deal['performance_to_price_ratio']:.2f} - G3D Mark: {g3d_mark}")
        print(f"   URL: {deal['url']}\n")


def main():
    start_time = time.time()

    print("Starting the script...")
    url = "https://www.videocardbenchmark.net/GPU_mega_page.html"
    driver = setup_driver(url)

    print("Clicking buttons...")
    click_buttons(driver)

    print("Fetching GPU data...")
    data = get_gpu_data(driver)

    print("Fetching GPU deals from eBay...")
    api = Finding(siteid='EBAY-GB', appid=APP_ID, config_file=None)

    # Add any exclusion keywords here
    exclude = ['faulty', 'box', 'cover', 'plate', 'bracket', 'fan', 'bridge', 'cooler',
               'mat', 'chip', 'block', 'bezel', 'cable', 'mod', 'FDC10M12S9-C']

    ebay_results = fetch_gpu_from_ebay(api, data, exclude=exclude)

    print("Calculating performance-to-price ratios...")
    ebay_results = calculate_performance_to_price_ratio(ebay_results, data)

    print("\nGPU data:")
    for row in data:
        print(row)

    print("\neBay results:")
    for result in ebay_results:
        print(result)

    display_top_deals(ebay_results, data, n=10)

    end_time = time.time()
    elapsed_time = end_time - start_time
    print(f"\nThe script took {elapsed_time:.2f} seconds to complete.")

    # input("Press Enter to close the browser...") # For debugging


if __name__ == "__main__":
    main()
