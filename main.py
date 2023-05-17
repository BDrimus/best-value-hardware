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


# # Function to fetch GPUs from eBay API
# def fetch_gpus():
#     try:
#         api = Finding(siteid='EBAY-GB', appid=APP_ID, config_file=None)
#         payload = {
#             'keywords': 'gpu',
#             'itemFilter': [
#                 {'name': 'ListingType', 'value': 'FixedPrice'}
#             ]
#         }
#         response = api.execute('findItemsAdvanced', payload)
#         search_result = response.dict().get("searchResult")
#         if search_result is not None and "item" in search_result:
#             return search_result["item"]
#         else:
#             return None
#     except ConnectionError as e:
#         print(e)
#         print(e.response.dict())


# # Function to fetch GPU performance from UserBenchmark
# def fetch_gpu_performance(gpu_name):
#     with open("GPU_UserBenchmarks.csv", newline="") as csvfile:
#         reader = csv.DictReader(csvfile)
#         for row in reader:
#             if row["Type"] == "GPU" and row["Model"].lower() == gpu_name.lower():
#                 return float(row["Benchmark"])
#     return None

# def find_best_matching_model(gpu_name, gpu_models):
#     for model in gpu_models:
#         if model.lower() in gpu_name.lower():
#             return model
#     return None

# def get_brand(gpu_name):
#     with open("GPU_UserBenchmarks.csv", newline="") as csvfile:
#         reader = csv.DictReader(csvfile)
#         for row in reader:
#             if row["Type"] == "GPU" and row["Model"].lower() == gpu_name.lower():
#                 return row["Brand"]
#     return None

# def get_unique_gpu_models():
#     gpu_models = set()
#     with open("GPU_UserBenchmarks.csv", newline="") as csvfile:
#         reader = csv.DictReader(csvfile)
#         for row in reader:
#             if row["Type"] == "GPU" and row["Brand"] in ["Nvidia", "AMD"]:
#                 gpu_models.add(row["Model"])
#     return gpu_models

# # Fetch GPUs from eBay
# gpus = get_unique_gpu_models()

# gpu_deals = {}

# if gpus is not None:
#     for gpu in gpus:
#         gpu_name = gpu["title"][0]
#         if "sellingStatus" in gpu and gpu["sellingStatus"]:
#             selling_status_list = gpu["sellingStatus"]
#             if isinstance(selling_status_list, list) and len(selling_status_list) > 0:
#                 selling_status = selling_status_list[0]
#                 if "currentPrice" in selling_status and selling_status["currentPrice"]:
#                     gpu_price = float(selling_status["currentPrice"][0]["__value__"])
#                 else:
#                     gpu_price = None
#             else:
#                 gpu_price = None
#         else:
#             gpu_price = None
#         gpu_url = gpu["viewItemURL"][0]

#         # Fetch GPU performance
#         performance = fetch_gpu_performance(gpu_name)
#         if performance and gpu_price:
#             if gpu_name not in gpu_deals or gpu_price < gpu_deals[gpu_name]["price"]:
#                 ratio = performance / gpu_price
#                 gpu_deals[gpu_name] = {"name": gpu_name, "price": gpu_price, "url": gpu_url, "ratio": ratio}
# else:
#     print("Error: No GPUs found.")




# Set up the Chrome WebDriver
driver = webdriver.Chrome()

# Open the website
url = "https://www.videocardbenchmark.net/GPU_mega_page.html"
driver.get(url)

# Wait for the button to be present and clickable
wait = WebDriverWait(driver, 20)
button = wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="qc-cmp2-ui"]/div[2]/div/button[2]')))
button.click()

button = wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="cputable_length"]/label/select/option[4]')))
button.click()

button = wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="cputable"]/thead/tr/th[3]')))
button.click()
button.click()

# Find the table element
table = driver.find_element(By.XPATH, '//*[@id="cputable"]/tbody')

# Find all the rows in the table
rows = table.find_elements(By.TAG_NAME, 'tr')

# Initialize an empty list to store the row data
data = []

# Iterate over each row
for row in rows:
    # Find all the cells in the row
    cells = row.find_elements(By.TAG_NAME, 'td')
    
    # Extract the text from each cell and store it in a dictionary
    row_data = {
        'name': cells[1].text,
        'g3d-mark': cells[2].text,
    }

    # Remove the comma from the 'g3d-mark' string and convert it to an integer
    g3d_mark = int(row_data['g3d-mark'].replace(',', ''))

    if g3d_mark < 30000:
        break
    
    # Append the row data to the data list
    data.append(row_data)

# Print the scraped data
for row in data:
    print(row)


# Wait for user input before closing the browser
input("Press Enter to close the browser...")

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
