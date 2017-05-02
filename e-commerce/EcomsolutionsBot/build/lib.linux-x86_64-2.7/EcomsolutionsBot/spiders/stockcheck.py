# -*- coding: utf-8 -*-
import scrapy
from scrapy.http import Request, FormRequest
import requests
import datetime
import json
import re

ECOM_EMAIL = "sourcing@europetec.ch"
ECOM_PASSWORD = "In8gT5ST94MM"

def get_EndDate():
    return datetime.date.today().strftime("%m/%d/%Y")

def get_StartDate():
    return (datetime.date.today().replace(day=1) - datetime.timedelta(days=1)).replace(day=1).strftime("%m/%d/%Y")

class StockcheckSpider(scrapy.Spider):
    name = "stockcheck"
    start_urls = ['http://app.ecomsolutions.technology/']

    def __init__(self):
        self.login_url = "http://app.ecomsolutions.technology/"
        self.list_url = "http://app.ecomsolutions.technology/amazonorder/list"
        self.check_condition = {"StartDate":  get_StartDate(), "EndDate": get_EndDate(), "Status": "Ordered"}
        self.check_condition_Status_list = ["Pending..", "Ordered"]

    def parse(self, response):
        token = response.xpath("//input[@name='__RequestVerificationToken']/@value").extract_first()
        payload = {"__RequestVerificationToken": token, "Username": ECOM_EMAIL, "Password": ECOM_PASSWORD}

        yield FormRequest(url=self.login_url, method="POST", formdata=payload, callback=self.load_listpage, dont_filter=True)

    def load_listpage(self, response):
        yield Request(url=self.list_url, callback=self.process_list, dont_filter=True)

    def process_list(self, response):
        token = response.xpath("//input[@name='__RequestVerificationToken']/@value").extract_first()

        for Status in self.check_condition_Status_list:
            payload = { "__RequestVerificationToken": token,
                        "IsSearch": "False",
                        "TotalCount": "1",
                        "HiddenOrderChildStatus": "",
                        "MerketPlace": "",
                        "MerchantId": "",
                        "SearchTerm": "",
                        "StartDate": self.check_condition["StartDate"],
                        "EndDate": self.check_condition["EndDate"],
                        "Status": Status, # self.check_condition["Status"], # "Pending..",
                        "OrderChildStatus": "",
                        "ListedBy": "",
                        "OrderedBy": "",
                        "PageSize": "30",
                        "ButtonSearch": "ButtonSearch" }

            yield FormRequest(url=self.list_url, method="POST", formdata=payload, callback=self.check_products, meta={"Status": Status}, dont_filter=True)

    def check_products(self, response):
        products = response.xpath("//table/tbody/tr")
        Status = response.meta["Status"]

        for product in products:
            product_url = product.xpath("td")[3].xpath("a[@target='_blank']/@href").extract_first()
            product_name = product.xpath("td")[3].xpath("a[@target='_blank']/span/@title").extract_first()

            notify_info = { "StartDate": self.check_condition["StartDate"],
                            "EndDate": self.check_condition["EndDate"],
                            "Status": Status, # self.check_condition["Status"],
                            "Name": product_name, "url": product_url, "Stock": "IN-STOCK"}
            # print product_name, product_url
            if "walmart" in product_url:
                yield Request(url=product_url, callback=self.check_productstock_walmart, meta={"notify_info": notify_info}, dont_filter=True)

    def check_productstock_walmart(self, response):
        notify_info = response.meta["notify_info"]

        product_url = notify_info["url"]
        product_name = notify_info["Name"]

        # Convenience Concepts Tucson Deluxe 2-Tier Console Table, Weathered Gray / black
        # -> ['Convenience Concepts Tucson Deluxe 2-Tier Console Table', ' Weathered Gray ', ' black']
        # Metal Bookcase, Two-Shelf, 34-1/2w x 12-5/8d x 29h, Light Gray, Sold as 1 Each
        # -> ['Metal Bookcase', ' Two-Shelf', ' 34-1', '2w x 12-5', '8d x 29h', ' Light Gray', ' Sold as 1 Each']
        variants = re.compile(",|/|\(|\)").split(product_name)

        # In general, first element is product name and not color info. So remove first element
        variants.pop(0)

        content = response.xpath("//script[contains(text(), 'window.__WML_REDUX_INITIAL_STATE__ = ')]/text()").extract_first()
        product_info = json.loads(content.split("window.__WML_REDUX_INITIAL_STATE__ = ")[1][0:-1])

        notified = False
        # if color or size is not None:
        if len(variants) > 0:
            for variant in variants:
                variant = variant.lower().strip()
                if variant == "":
                    continue
                try:
                    variants_color = product_info["product"]["variantCategoriesMap"][product_info["product"]["primaryProduct"]]["actual_color"]["variants"]
                except:
                    variants_color = None
                try:
                    variants_size = product_info["product"]["variantCategoriesMap"][product_info["product"]["primaryProduct"]]["size"]["variants"]
                except:
                    variants_size = None

                if variants_color:
                    variants_cond = variants_color
                if variants_size:
                    variants_cond = variants_size

                for key, value in variants_cond.iteritems():
                    if variants_cond[key]["name"].lower() == variant:
                        if variants_cond[key]["availabilityStatus"] == "AVAILABLE":
                            print notify_info
                            requests.post('https://hooks.zapier.com/hooks/catch/1227744/mn8gav/', data=notify_info)
                            notified = True
                            break
        if notified == False:
            try:
                if product_info["offers"][product_info["products"][product_info["primaryProduct"]]["offers"][0]]["productAvailability"]["availabilityStatus"] == "IN_STOCK":
                    print notify_info
                    requests.post('https://hooks.zapier.com/hooks/catch/1227744/mn8gav/', data=notify_info)
                    notified = True
            except:
                pass


