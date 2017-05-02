from scrapy.selector import HtmlXPathSelector
from scrapy.spider import BaseSpider
from scrapy.http import Request
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

from product_spiders.utils import extract_price2uk

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
import re
import string

class ribejabtogfiskeriSpider(BaseSpider):
    name = 'ribejagtogfiskeri.dk'
    allowed_domains = ['www.ribejagtogfiskeri.dk']
    start_urls = ['http://www.ribejagtogfiskeri.dk/catalog/seo_sitemap/category/']
    
    def parse(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)
        pages = hxs.select('//div[@class="pages"]/ol/li/a/@href').extract()
        for page in pages:
            yield Request(page, meta=response.meta, callback=self.parse)
        productCategories = hxs.select('//div[@class="content"]/ul[@class="bare-list"]//a/@href').extract()
        for url in productCategories:
            yield Request(url, meta=response.meta, callback=self.parseCategoryPage)
            
            
    def parseCategoryPage(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)
        pages = hxs.select('//table[@class="pager"]//li/a/@href').extract()
        for page in pages:
            yield Request(page, meta=response.meta, callback=self.parseCategoryPage)
        products = hxs.select('//div//ol[@class="grid-row"]/li[@class="item"]').extract()
        for product in products:
            hxs2 = HtmlXPathSelector(text=product)
            pUrl = hxs2.select('//p[@class="product-image"]/a/@href').extract()
            if pUrl != None:
                yield Request(pUrl[0], meta=response.meta, callback=self.parseProductPage) 
            
    def parseProductPage(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)
        productName = hxs.select('//div[@class="product-shop"]/h1[@class="product-name"]/text()').extract()
        priceSection = hxs.select('//div[@class="price-box"]//*[@class="regular-price" or @class="special-price"]/span[@class="price"]/text()').extract()
        price = self.decodeSwedishPriceString(priceSection[0])
        optionSections = hxs.select('//dl/dd/select[@class=" required-entry product-custom-option"]').extract()
        if len(optionSections) == 0:
            loader = ProductLoader(item=Product(), selector=hxs)
            loader.add_value('name', productName[0])
            loader.add_value('price', price)
            loader.add_value('url', base_url)
            yield loader.load_item()
        else:
            optionDimensions = []
            for optionSection in optionSections:
                hxs2 = HtmlXPathSelector(text=optionSection)
                options = []
                optionNameText = hxs2.select('//option/text()').extract()
                optionValueText = hxs2.select('//option/@value').extract()
                for i in range(1, len(optionNameText)):
                    options.append((optionNameText[i], optionValueText[i]))
                optionDimensions.append(options)
            for j in (self.createOptionCombo(optionDimensions, 0, price, productName[0], base_url, hxs2)):
                yield j
                    

    def createOptionCombo(self, optionDimensions, optToIter, basePrice, baseName, baseUrl, selector):
        for i in optionDimensions[optToIter]:
            strippedOption = self.stripPriceFromOption(i[0])
            fullName = baseName + " " + strippedOption[0]
            price = basePrice + self.decodeSwedishPriceString(strippedOption[1])
            if optToIter == len(optionDimensions)-1:
                loader = ProductLoader(item=Product(), selector=selector)
                loader.add_value('name', fullName)
                loader.add_value('price', price)
                loader.add_value('url', baseUrl)
                yield loader.load_item()
            else:
                for j in (self.createOptionCombo(optionDimensions, optToIter+1, price, fullName, baseUrl, selector)):
                    yield j
        
    def stripPriceFromOption(self, optionString):
        optionRe = re.compile('(.*?)\+([0-9.]*,[0-9]*.kr)')
        mPatched = optionRe.match(optionString)
        if mPatched != None:
            return (mPatched.group(1), mPatched.group(2))
        else:
            return (optionString, '+0,00 kr')
            
    def decodeSwedishPriceString(self, pString):
        priceRe = re.compile(".*?([0-9.]*),([0-9]*).kr", re.DOTALL)
        priceMatch = priceRe.match(pString)
        if priceMatch == None:
            priceRe = re.compile(".*?([0-9.]*).kr", re.DOTALL)
            priceMatch = priceRe.match(pString)
            price = float(string.replace(priceMatch.group(1), '.', ''))
            return price
        else:    
            price = float(string.replace(priceMatch.group(1), '.', ''))
            price += float(priceMatch.group(2))/100
            return price
