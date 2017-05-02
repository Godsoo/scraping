
import re
import json

from decimal import Decimal
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

from scrapy import log

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader


class TrustFordSandicliffeSpider(BaseSpider):
    name = 'trustford-sandicliffe.co.uk'
    allowed_domains = ['sandicliffe.co.uk']
    start_urls = ['https://www.sandicliffe.co.uk/ford/new-cars']

    ajax_url = "http://www.sandicliffe.co.uk/newcar/ajax2"


    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        categories = response.xpath('//a[@itemprop="url"]/@href').extract()
        for category in categories:
            yield Request(urljoin_rfc(base_url, category), callback=self.parse_category)
            
    def parse_category(self, response):
        hxs = HtmlXPathSelector(response)
        for url in hxs.select('//a[@itemprop="url"]/@href').extract():
            yield Request(url, callback=self.parse_product)
            
    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        options = hxs.select('//a[@itemprop="url"]/@href').extract()
        if options:
            for url in options:
                yield Request(response.urljoin(url), callback=self.parse_product)
            return
        
        loader = ProductLoader(item=Product(), response=response)
        loader.add_xpath('name', '//h1[@itemprop="name"]//text()')
        categories = hxs.select('//div[@class="breadcrumbs"]/ul/li/a/span/text()').extract()[6:]
        for category in categories:
            if category not in loader.get_output_value('name'):
                loader.add_value('name', category)
        loader.add_xpath('identifier', '//meta[@itemprop="productID"]/@content')
        loader.add_xpath('price', '//span[@itemprop="price"]/text()')
        loader.add_css('price', '.price ::text')
        loader.add_value('url', response.url)
        loader.add_xpath('image_url', '//img[@itemprop="image"]/@src')
        if loader.get_output_value('identifier'):
            yield loader.load_item()

    def parse_model(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        model = response.url.split('/')[-1]

        data = {"method": "getSeries", "data": {"make": "ford", "model": model, "type": 0}}
        yield Request(self.ajax_url, 
                      method='POST',
                      body=json.dumps(data),  
                      headers={'Content-Type':'application/json'},
                      callback=self.parse_series,
                      meta={'model': model})

    def parse_series(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        
        model = response.meta['model']
        model_series = json.loads(response.body)

        for series in model_series:
            data = {"method": "getRefineOptions","data": {"make": "ford","model": model,"type": 0,"series": series['series']}}
            yield Request(self.ajax_url, 
                          method='POST',
                          body=json.dumps(data),  
                          headers={'Content-Type':'application/json'},
                          callback=self.parse_options,
                          meta={'model': model, 'series': series['series']})

    def parse_options(self, response):
        model = response.meta['model']
        series = response.meta['series']

        options = json.loads(response.body)

        filters = {}
        for key, option in options.iteritems():
            filters[key] = []
            for o in option:
                filters[key].append(o.values()[0])

        data = {"method": "getResults",
                "data": {"make": "ford", "model": model,
                         "type": 0, "series": series,
                         "filters": filters}}

        yield Request(self.ajax_url, 
                      method='POST',
                      body=json.dumps(data),  
                      headers={'Content-Type':'application/json'},
                      callback=self.parse_results)

    def parse_results(self, response):
        base_url = "http://www.sandicliffe.co.uk/"

        results = json.loads(response.body)
        for result in results:
            name = result['make'].title() + ' ' + result['range'].title() + ' ' + result['bodytype'] + ' ' + result['derivative']
            loader = ProductLoader(item=Product(), response=response)
            loader.add_value('identifier', name)
            loader.add_value('name', name)
            loader.add_value('price', result['basic_price'])
            loader.add_value('image_url', result['image'])
            loader.add_value('url', urljoin_rfc(base_url, result['link']))

            yield loader.load_item()
      
    '''
    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        cars_box = hxs.select('//div[contains(@class, "sale-box sale-box-element white-box ")]')
        for car_box in cars_box:
            product_name = ' '.join(car_box.select('.//h1/text()|.//h2/text()|.//h3[1]/text()').extract())
            product_price = car_box.select('.//h3[contains(@class, "fordblue-text") and contains(text(), "Offer Price")]/text()').re(r'[\d.,]+')
            product_image = car_box.select('.//a[img][1]/img/@src').extract()
            product_url = urljoin_rfc(base_url, car_box.select('.//a[img][1]/@href').extract()[0])

            loader = ProductLoader(item=Product(), selector=car_box)
            loader.add_value('identifier', product_name)
            loader.add_value('name', product_name)
            loader.add_value('price', product_price)
            loader.add_value('image_url', product_image)
            loader.add_value('url', product_url)

            yield loader.load_item()
    '''
