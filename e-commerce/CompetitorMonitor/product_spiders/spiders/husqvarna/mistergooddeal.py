from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

from product_spiders.utils import extract_price
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.base_spiders.prodcache import ProductCacheSpider

import re



class MisterGoodDealSpider(BaseSpider):

    name            = 'mistergooddeal.com'
    allowed_domains = ['mistergooddeal.com']
    start_urls      = ['http://www.mistergooddeal.com/']


    def parse(self, response):

        hxs = HtmlXPathSelector(response)

        categories = hxs.select("//ul[@class='nav_ul']/li[not(@id)]/div//a/@href").extract()
        for category in categories: 
            yield Request(urljoin_rfc(get_base_url(response), category), callback=self.parse_category)


    def parse_category(self, response):
        
        hxs = HtmlXPathSelector(response)
        items = hxs.select("//div[@class='product_detail']//a[@class='prd_link']/@href").extract()
        for item in items:
            yield Request(urljoin_rfc(get_base_url(response), item), callback=self.parse_details)

        try:
            next_page = hxs.select("//a[text()='Suivant']/@href").extract()[0]
            yield Request(urljoin_rfc(get_base_url(response), next_page), callback=self.parse_category)
        except:
            pass


    def parse_details(self, response):

        hxs = HtmlXPathSelector(response)

        url        = response.url
        identifier = ''.join(hxs.select('//input[@name="xsell_codic"]/@value').extract())
        name       = ''.join(hxs.select("//h2[@itemprop='name']/text()").extract())
        price      = hxs.select("//meta[@itemprop='price']/@content").extract()   
        stock      = ''.join(hxs.select("//span[text()='EN STOCK' or contains(text(),'sous 48h')]/text()").extract())
        stock      = 1 if stock else 0
        image_url  = ''.join(hxs.select("//meta[@property='og:image']/@content").extract())
        sku        = identifier
        categories = hxs.select("//div[@id='product_breadcrumb']/a/text()").extract()
        price      = float(price[0]) if price else 0

        loader = ProductLoader(selector=hxs, item=Product())

        loader.add_value('identifier', identifier)
        loader.add_value('name',       name)
        loader.add_value('price',      price)
        loader.add_value('stock',      stock)
        loader.add_value('image_url',  image_url)
        loader.add_value('sku',        sku) 
        loader.add_value('url',        url)
        loader.add_value('url',        None)

        for category in categories:
            loader.add_value('category', category.strip())

        loader.load_item()