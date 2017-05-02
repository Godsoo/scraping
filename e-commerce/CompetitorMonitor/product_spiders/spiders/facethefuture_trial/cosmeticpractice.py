from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector

from scrapy.http import Request

from scrapy.utils.response import get_base_url

from scrapy.utils.url import  urljoin_rfc

from product_spiders.items import Product, ProductLoader

import logging

class CosmeticPracticeSpider(BaseSpider):
    name = "facethefuture-trial-thecosmeticpractice"
    allowed_domains = ["www.thecosmeticpractice.co.uk"]
    start_urls = (
        "http://www.thecosmeticpractice.co.uk/sitemap/",
    )

    products_parsed = []

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        categories = []
        cat_anchors = hxs.select('//div[@class="cms_page_2 sitemap_category"]//ul[@class="sitemap_list"]//li//a')
        for anchor in cat_anchors:
            link = anchor.select('@href').extract()[0]
            name = anchor.select('@title').extract()[0]
            categories.append((name,link))

            new_url = urljoin_rfc(base_url, link)
            request = Request(new_url, callback=self.parse_listing)
            yield request

        brands = []
        brand_anchors= hxs.select('//div[@class="cms_page_2 sitemap_brands"]//ul[@class="sitemap_list"]//li//a')
        for anchor in brand_anchors:
            link = anchor.select('@href').extract()[0]
            name = anchor.select('@title').extract()[0]
            brands.append((name,link))
            new_url = urljoin_rfc(base_url, link)
            request = Request(new_url, callback=self.parse_listing)
            yield request

    def parse_listing(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        #Get all products for a page, save/yield the links, move to next page
        products = hxs.select('//div[@id="search_results_products"]//div[@class="product_details"]//a[@class="product_options_view"]')
        for product in products:
            link = product.select("@href").extract()[0]
            new_url = urljoin_rfc(base_url, link)
            request = Request(new_url, callback=self.parse_product)
            yield request

        try:
            #If the key exists then this request was yielded from the
            #pagination
            val = response.meta['paginate']
        except KeyError:
            pages = hxs.select('//p[@class="pagination"]//a[@class="page_num"]/@href').extract()
            for page in pages:
                new_url = urljoin_rfc(base_url, page)
                request = Request(new_url, callback=self.parse_listing)
                request.meta['paginate'] = True
                yield request

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)

        if response.url in self.products_parsed:
            return
        loader = ProductLoader(response=response, item=Product() )


        logging.error("RESPONSE URL")
        logging.error(response.url)

        #desc = hxs.select('//div[@id="product_description"]')

        price = None
        category = None
        crumbs = None
        brand = None

        price_raw = hxs.select('//div[@id="product_price"]//span[@class="price"]//span[@class="GBP"]/text()').extract()
        if price_raw:
            price = price_raw[0][1:]

        name = hxs.select('//div[@id="product_page_right_title"]//span[@id="product_title"]//text()').extract()[0]

        try:
            category = response.meta['category']
        except KeyError:
            pass

        crumbs = hxs.select('//div[@id="breadcrumb_container"]//span//a/@title').extract()
        try:
            category = crumbs[1]
        except IndexError:
            pass

        try:
            brand = crumbs[2]
        except IndexError:
            pass

        img_url = hxs.select('//img[@id="product_medium_image"]/@src').extract()[0]

        if name:
            loader.add_value('name', name)
        if price:
            loader.add_value('price', price)
        loader.add_value('url', response.url)
        identifier = hxs.select(u'//input[@type="hidden" and @name="parent_product_id"]/@value').extract()
        loader.add_value('identifier', identifier[0])
        loader.add_value('image_url', img_url)
        if category:
            loader.add_value('category', category)
        if brand:
            loader.add_value('brand', brand)
        loader.add_value('shipping_cost', 'N/A')

        yield loader.load_item()
