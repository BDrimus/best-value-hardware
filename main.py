import requests
import json
import re
from bs4 import BeautifulSoup
from operator import itemgetter
from ebaysdk.finding import Connection as Finding
from ebaysdk.exception import ConnectionError
import csv

# Function to fetch GPUs from eBay API
def fetch_gpus():
    try:
        api = Finding(siteid='EBAY-GB', appid=APP_ID, config_file=None)
        payload = {
            'keywords': 'gpu',
            'itemFilter': [
                {'name': 'ListingType', 'value': 'FixedPrice'}
            ]
        }
        response = api.execute('findItemsAdvanced', payload)
        search_result = response.dict().get("searchResult")
        if search_result is not None and "item" in search_result:
            return search_result["item"]
        else:
            return None
    except ConnectionError as e:
        print(e)
        print(e.response.dict())


# Function to fetch GPU performance from UserBenchmark
def fetch_gpu_performance(gpu_name):
    with open("GPU_UserBenchmarks.csv", newline="") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            if row["Type"] == "GPU" and row["Model"].lower() == gpu_name.lower():
                return float(row["Benchmark"])
    return None

def find_best_matching_model(gpu_name, gpu_models):
    for model in gpu_models:
        if model.lower() in gpu_name.lower():
            return model
    return None

def get_brand(gpu_name):
    with open("GPU_UserBenchmarks.csv", newline="") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            if row["Type"] == "GPU" and row["Model"].lower() == gpu_name.lower():
                return row["Brand"]
    return None

def get_unique_gpu_models():
    gpu_models = set()
    with open("GPU_UserBenchmarks.csv", newline="") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            if row["Type"] == "GPU" and row["Brand"] in ["Nvidia", "AMD"]:
                gpu_models.add(row["Model"])
    return gpu_models

# Fetch GPUs from eBay
gpus = get_unique_gpu_models()

gpu_deals = {}

if gpus is not None:
    for gpu in gpus:
        gpu_name = gpu["title"][0]
        if "sellingStatus" in gpu and gpu["sellingStatus"]:
            selling_status_list = gpu["sellingStatus"]
            if isinstance(selling_status_list, list) and len(selling_status_list) > 0:
                selling_status = selling_status_list[0]
                if "currentPrice" in selling_status and selling_status["currentPrice"]:
                    gpu_price = float(selling_status["currentPrice"][0]["__value__"])
                else:
                    gpu_price = None
            else:
                gpu_price = None
        else:
            gpu_price = None
        gpu_url = gpu["viewItemURL"][0]

        # Fetch GPU performance
        performance = fetch_gpu_performance(gpu_name)
        if performance and gpu_price:
            if gpu_name not in gpu_deals or gpu_price < gpu_deals[gpu_name]["price"]:
                ratio = performance / gpu_price
                gpu_deals[gpu_name] = {"name": gpu_name, "price": gpu_price, "url": gpu_url, "ratio": ratio}
else:
    print("Error: No GPUs found.")

# Sort GPUs by value to performance ratio
sorted_gpu_deals = sorted(gpu_deals.values(), key=itemgetter("ratio"), reverse=True)

# Print top 10 deals
for deal in sorted_gpu_deals[:10]:
    print(f"Name: {deal['name']}\nPrice: ${deal['price']}\nURL: {deal['url']}\nValue to Performance Ratio: {deal['ratio']}\n")
