# -*- coding: utf-8 -*-
import scrapy
from scrapy.http import Request, FormRequest
import requests
import datetime

ECOM_EMAIL = "sourcing@europetec.ch"
ECOM_PASSWORD = "In8gT5ST94MM"

WALMART_EMAIL = "ecomigniter@gmail.com"
WALMART_PASSWORD = "BDyoaomm3fov"

def get_EndDate():
    return datetime.date.today().strftime("%m/%d/%Y")

def get_StartDate():
    return (datetime.date.today().replace(day=1) - datetime.timedelta(days=1)).replace(day=1).strftime("%m/%d/%Y")

class ShipmentcheckSpider(scrapy.Spider):
    name = "shipmentcheck"
    start_urls = ['http://app.ecomsolutions.technology/']

    def __init__(self):
        self.login_url = "http://app.ecomsolutions.technology/"
        self.list_url = "http://app.ecomsolutions.technology/amazonorder/list"

    def parse(self, response):
        token = response.xpath("//input[@name='__RequestVerificationToken']/@value").extract_first()
        payload = {"__RequestVerificationToken": token, "Username": ECOM_EMAIL, "Password": ECOM_PASSWORD}

        yield FormRequest(url=self.login_url, method="POST", formdata=payload, callback=self.load_listpage, dont_filter=True)

    def load_listpage(self, response):
        yield Request(url=self.list_url, callback=self.process_list, dont_filter=True)

    def process_list(self, response):
        token = response.xpath("//input[@name='__RequestVerificationToken']/@value").extract_first()

        payload = { "__RequestVerificationToken": token,
                    "IsSearch": "False",
                    "TotalCount": "1",
                    "HiddenOrderChildStatus": "",
                    "MerketPlace": "",
                    "MerchantId": "",
                    "SearchTerm": "",
                    "StartDate": get_StartDate(),
                    "EndDate": get_EndDate(),
                    "Status": "Ordered",
                    "OrderChildStatus": "",
                    "ListedBy": "",
                    "OrderedBy": "",
                    "PageSize": "30",
                    "ButtonSearch": "ButtonSearch" }

        yield FormRequest(url=self.list_url, method="POST", formdata=payload, callback=self.check_products, dont_filter=True)

    def check_products(self, response):
        products = response.xpath("//table/tbody/tr")

        for product in products:
            product_orderid = product.xpath("td")[2].xpath("text()").extract_first().strip()
            product_name = product.xpath("td")[3].xpath("a[@target='_blank']/span/@title").extract_first()

            notify_info = { "StartDate": get_StartDate(),
                            "EndDate": get_EndDate(),
                            "Status": "Ordered",
                            "Name": product_name, "OrderId": product_orderid}
            # print product_orderid, product_name
            if "WM-" in product_orderid: # Walmart
            	yield Request(url="https://www.walmart.com/account/trackorder", callback=self.trackorder_walmart, meta={"last6digits": product_orderid[-6:], "notify_info": notify_info}, dont_filter=True)

    def trackorder_walmart(self, response):
    	payload = {"email": WALMART_EMAIL, "partialOrderId": response.meta["last6digits"]}
    	yield FormRequest(url="https://www.walmart.com/account/trackorder", method="POST", formdata=payload, meta=response.meta, callback=self.get_orderstatus_walmart, dont_filter=True)

    def get_orderstatus_walmart(self, response):
    	notify_info = response.meta["notify_info"]

    	try:
    		notify_info["Arrivesby"] = response.xpath("//span[contains(text(), 'Arrives by')]/span/text()").extract_first().strip()
    	except:
    		notify_info["Arrivesby"] = ""
    	notify_info["LineStatus"] = response.xpath("//span[@class='infograph-label' and not(@aria-hidden)]/text()").extract_first().strip()
    	notify_info["To"] = "".join(response.xpath("//div/span[contains(text(), 'To:')]/following-sibling::div//text()").extract()).strip()

    	print notify_info
    	requests.post('https://hooks.zapier.com/hooks/catch/1227744/t85wuy/', data=notify_info)

