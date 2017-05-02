# -*- coding: utf-8 -*-
from urlparse import urljoin as urljoin_rfc

from scrapy.http import Request
from scrapy.selector import HtmlXPathSelector
from scrapy.spider import BaseSpider
from scrapy.utils.response import get_base_url

from product_spiders.items import Product, ProductLoader
from product_spiders.utils import extract_price



class JunoCoUkSpider(BaseSpider):

    name = u'juno.co.uk'
    allowed_domains = ['www.juno.co.uk']
    start_urls = ['http://www.juno.co.uk/dj-equipment/all/?items_per_page=500&show_out_of_stock=1&currency=GBP']


    def parse(self, response):

        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)
        products = hxs.select('//table[@class="product_list"]//tr[starts-with(@class,"row")]')[1:]

        for product in products:

            loader = ProductLoader(item=Product(), selector=hxs)

            try:
                name = product.select('.//span[@class="title_search_highlight"]/text()').extract()[0]
            except:
                continue
            url = product.select('.//a[@class="jhighlight"]/@href').extract()[0]
            url = urljoin_rfc(base_url, url)
            identifier = url.split('/')[-2]
            image_url = "http://images.junostatic.com/full/IS" + str(identifier) + "-01-BIG.jpg"
            image_url = urljoin_rfc(base_url, image_url)
            price = product.select('.//td[@class="productprice"]/text()').extract()
            price = extract_price(price[0])
            brand = ''.join(product.select('.//span[@class="artist_search_highlight"]/a/text()').extract())
            sku = ''.join(product.select('./following::tr[1]//td[@class="cat_no"]/span/text()').extract())
            stock = ''.join(product.select('.//a[@title="Receive an e-mail alert when this title becomes available again"]').extract())
            stock = 1 if stock else 0

            loader.add_value('name', name)
            loader.add_value('identifier', identifier)
            loader.add_value('url', url)
            loader.add_value('image_url', image_url)
            loader.add_value('price', price)
            loader.add_value('sku', sku)

            yield Request(url, meta={'loader': loader}, callback=self.parse_details)

        try:
            next_page = hxs.select("//a[text()='Next Page']/@href").extract()[0]
            yield Request(next_page, callback=self.parse)
        except Exception as e:
            pass


    def parse_details(self, response):

        hxs = HtmlXPathSelector(response)
        brand = ''.join(hxs.select("//div[@itemprop='brand']/meta[@itemprop='name']/@content").extract()).strip()
        category = brand if brand else ''

        loader = response.meta['loader']
        loader.add_value('brand', brand)
        loader.add_value('category', category)

        yield loader.load_item()
