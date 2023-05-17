import requests
import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from bs4 import BeautifulSoup
from operator import itemgetter
from ebaysdk.finding import Connection as Finding
from ebaysdk.exception import ConnectionError


def setup_driver(url):
    driver = webdriver.Chrome()
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

        if g3d_mark < 30000:
            break

        data.append(row_data)

    return data


def fetch_gpu_from_ebay(api, data):
    ebay_results = []
    for row in data:
        keyword = row['name']
        payload = {
            'keywords': keyword,
            'categoryId': '27386',
            'itemFilter': [
                {'name': 'ListingType', 'value': 'FixedPrice'},
            ],
            'paginationInput': {
                'entriesPerPage': 10,
                'pageNumber': 1,
            },
            'sortOrder': 'PricePlusShippingLowest',
        }

        response = api.execute('findItemsAdvanced', payload)
        items = response.reply.searchResult.item if response.reply.searchResult._count != '0' else []

        first_valid_item = next((item for item in items if 'box' not in item.title.lower()), None)

        if first_valid_item:
            title = first_valid_item.title
            price = first_valid_item.sellingStatus.currentPrice.value
            listing_url = first_valid_item.viewItemURL
        else:
            title = 'N/A'
            price = 'N/A'
            listing_url = 'N/A'

        result = {'name': keyword, 'title': title, 'price': price, 'url': listing_url}
        ebay_results.append(result)

    return ebay_results


def main():
    url = "https://www.videocardbenchmark.net/GPU_mega_page.html"
    driver = setup_driver(url)
    click_buttons(driver)
    data = get_gpu_data(driver)
    api = Finding(siteid='EBAY-GB', appid=APP_ID, config_file=None)
    ebay_results = fetch_gpu_from_ebay(api, data)

    for row in data:
        print(row)

    for result in ebay_results:
        print(result)

    input("Press Enter to close the browser...")


if __name__ == "__main__":
    main()


# Close the browser when you're done


# video_card_data = []
# for item in data:
#     video_card_data.append([
#         item['name'],
#         item['g3d_mark'],
#         item['price'],
#         item['value'],
#         item['tdp_watts'],
#         item['power_perf'],
#         item['test_date']
#     ])

# columns = ['Name', 'G3D_Mark', 'Price', 'Value', 'TDP_Watts', 'Power_Perf', 'Test_Date']
# df = pd.DataFrame(video_card_data, columns=columns)
# df.to_csv('video_card_data.csv', index=False)


# # Sort GPUs by value to performance ratio
# sorted_gpu_deals = sorted(gpu_deals.values(), key=itemgetter("ratio"), reverse=True)

# # Print top 10 deals
# for deal in sorted_gpu_deals[:10]:
#     print(f"Name: {deal['name']}\nPrice: ${deal['price']}\nURL: {deal['url']}\nValue to Performance Ratio: {deal['ratio']}\n")
