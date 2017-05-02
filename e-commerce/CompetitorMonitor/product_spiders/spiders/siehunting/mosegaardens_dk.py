import string
import re

from scrapy.spider import BaseSpider
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy import log
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader


class mosegaardensSpider(BaseSpider):
    name = 'mosegaardens.dk'
    allowed_domains = ['www.mosegaardens.dk']
    start_urls = ['http://www.mosegaardens.dk']
    
    def parse(self, response):
        base_url = get_base_url(response)
        catMenuRe = re.compile("Menu[0-9_]*= new Array.\".*?\",\"(.*?)\"")
        categoryMatches = catMenuRe.finditer(response.body)
        for i in categoryMatches:
            yield Request(i.group(1), meta=response.meta, callback=self.parseCategoryPage)
            
            
    def parseCategoryPage(self, response):
        base_url = get_base_url(response)
        nextPageRe = re.compile(u"<a href=\"([^\"]*?)\" class=\"pageResults\" title=\" N..te side \"")
        npMatch = nextPageRe.match(response.body)
        if npMatch != None:
            yield Request(npMatch.group(1), meta=response.meta, callback=self.parseCategoryPage)
            
        productRe = re.compile(u"<tr class=\"productListing-(.*?)<\/tr>", re.DOTALL)
        productMatches = productRe.finditer(response.body)
        for i in productMatches:
            productBody = i.group(1)
            fieldSeparatorRe = re.compile(u"<td(.*?)<\/td>.*?<td(.*?)<\/td>.*?<td(.*?)<\/td>", re.DOTALL)
            fsResults = fieldSeparatorRe.findall(productBody)
            productDetailsRe = re.compile(u"<a href=\"([^\"]*?)\"><b>(.*?)<\/b>", re.DOTALL)
            prodDetails = productDetailsRe.findall(fsResults[0][1])
            priceRe = re.compile(u".*?([0-9.,]*) DKK", re.DOTALL)
            price = priceRe.findall(productBody)
            loader = ProductLoader(item=Product(), response=response)
            loader.add_value('name', prodDetails[0][1].decode('ascii', 'ignore'))
            loader.add_value('url', prodDetails[0][0])
            if price != None:
                if len(price)>1:
                    loader.add_value('price', self.decodeDanishPriceString(price[1]))
                else:
                    loader.add_value('price', self.decodeDanishPriceString(price[0]))
            yield loader.load_item()
            
    def decodeDanishPriceString(self, pString):
        priceRe = re.compile(u".*?([0-9.]*),([0-9]*)", re.DOTALL)
        priceMatch = priceRe.match(pString)
        if priceMatch == None:
            priceRe = re.compile(".*?([0-9.]*)", re.DOTALL)
            priceMatch = priceRe.match(pString)
            price = float(string.replace(priceMatch.group(1), '.', ''))
            return price
        else:
            price = float(string.replace(priceMatch.group(1), '.', ''))
            price += float(priceMatch.group(2))/100
            return price
