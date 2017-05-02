import os
import re
import json
import csv
import urlparse

from copy import deepcopy

from scrapy import signals
from scrapy.xlib.pydispatch import dispatcher

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc
from urlparse import urljoin

from scrapy import log

from utils import extract_price
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

HERE = os.path.abspath(os.path.dirname(__file__))

class InternetWigsSpider(BaseSpider):
    name = 'specialitycommerceuk-wigsuk.com'
    allowed_domains = ['wigsuk.com']

    start_urls = ['http://www.wigsuk.com/Home_Fashion_Wigs?bitStripPage_Active=true&intStripPage_BlockFirstToDisplay=1&intStripPage_BlockTotalNumberToDisplay=999999&strProductCategories=',
                  'http://www.wigsuk.com/wigs_entire_collection',
                  'https://www.wigsuk.com/wigs_entire_collection']

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        next_page = hxs.select('//div[@class="top-pagenation"]/a[last()]/@href').extract()
        if next_page:
            yield Request(urljoin(base_url, next_page[0]))

#        product_ids = hxs.select('//div[contains(@id, "idProduct_MoveContainer")]/@id').re('idProduct_MoveContainer(.*)')
        product_urls = hxs.select('//div[@class="page-content"]/div[contains(@class, "page-block")]//a/@href').extract()
        product_url = 'http://www.wigsuk.com/ColourChartInsert_Page.php?strUniqueProductNumber='
        for url in product_urls:
            product_id = re.findall('_(\d+)', url)[0]
            yield Request(product_url+product_id, callback=self.parse_product, meta={'identifier': product_id})
	
	#category_urls = hxs.select('//div[@class="nav"]//a/@href').extract()
	#category_urls += hxs.select('//div[@class="sub-nav-quicklinks"]//a/@href').extract()
	#for url in category_urls:
	  #yield Request(urljoin(base_url, url), callback=self.parse_category)

    def parse_category(self, response):
      hxs = HtmlXPathSelector(response)
      base_url = get_base_url(response)

      next_page = hxs.select('//div[@class="top-pagenation"]/a[last()]/@href').extract()
      if next_page:
	  yield Request(urljoin(base_url, next_page[0]), callback=self.parse_category)
      
      product_urls = hxs.select('//div[@class="page-content"]/div[contains(@class, "page-block")]//a/@href').extract()
      for url in product_urls:
	yield Request(urljoin(base_url, url), callback=self.parse_product_full_page)
	
    def parse_product_full_page(self, response):
      hxs = HtmlXPathSelector(response)
      base_url = get_base_url(response)
   

    def parse_product(self, response):
	hxs = HtmlXPathSelector(response)
	base_url = get_base_url(response)

        loader = ProductLoader(item=Product(), response=response)
        brand = hxs.select('//div[@class="ProductColourChartMainProductImageDiv"]/text()').re('by +(.+)')
        if brand:
	  brand = brand[0].strip()

        product_name = hxs.select('//div[@class="ProductColourChartMainProductImageDiv"]/text()').extract()
        product_name = product_name[0].strip()
       
        product_price = hxs.select('//div[@class="ProductColourChartMainProductSelectColorBuyDiv"]/h1/text()').extract()
        product_price = extract_price(product_price[0])
       
        product_code = response.meta['identifier']

        image_url = hxs.select('//div[@class="ProductColourChartMainProductImageDiv"]/img/@src').extract()
        image_url = image_url[0] if image_url else ''
        
        categories = ''
        
        loader = ProductLoader(item=Product(), response=response)
        loader.add_value('name', product_name)
        loader.add_value('url', response.url)
        loader.add_value('sku', product_code)
        loader.add_value('identifier', product_code)
        loader.add_value('brand', brand)
        if image_url:
            loader.add_value('image_url', urljoin_rfc(base_url, image_url))

        loader.add_value('category', categories)

        loader.add_value('price', product_price)
        if loader.get_output_value('price')<=0:
            loader.add_value('stock', 0)

        item = loader.load_item()
        options = hxs.select('//div[@class="ProductColourChartItemContainer"]')
        if options:
            option_item = deepcopy(item)
            for option in options:
                option_id = option.select('@onclick').re("\'(\d+)\'")[2]
                option_item['image_url'] = urljoin_rfc(base_url, option.select('div/img/@src').extract()[0])
                option_item['identifier'] = product_code + '-' + option_id
                option_item['name'] = product_name + ' ' + option.select('div[@class="ProductColourChartItemContainer_TextName"]/text()').extract()[0]
                option_item['sku'] = option_item['identifier']
                yield option_item
        else:
            yield item
