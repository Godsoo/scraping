# -*- coding: utf-8 -*-
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from scrapy.http import Request, FormRequest
import re, json, logging

from scrapy.utils.response import get_base_url
from urlparse import urljoin as urljoin_rfc

class DmlightsSpider(BaseSpider):

    name              = "dmlights.be"
    start_urls        = ["http://www.dmlights.be"]

    base_url          = "http://www.dmlights.be"
    download_delay    = 1





    
    def start_requests(self):
        url = "http://www.dmlights.be/changeCountry.action"
        yield FormRequest(url, formdata={'country': 'BE'})

    def parse(self, request):
        categories = ["http://www.dmlights.be/rootCategory:Accessoires%7Cbrand:Luceplan",
                      "http://www.dmlights.be/binnenverlichting?brand=Luceplan",
                      "http://www.dmlights.be/binnenverlichting?brand=Luceplan",
                      "http://www.dmlights.be/led-verlichting?brand=Luceplan"]

        for category in categories:
            yield Request(category, callback=self.parse_categories)


    def parse_categories(self, response):
        base_url = get_base_url(response)

        hxs  = HtmlXPathSelector(response)
        products = hxs.select('//div[@class="row"]/div/a/@href').extract()

        for product in products:
            yield Request(urljoin_rfc(base_url, product), cookies={'country':"BE"}, callback=self.parse_page)

        next_page = hxs.select('//a[@aria-label="Next"]/@href').extract()
        if next_page:
            yield Request(urljoin_rfc(base_url, next_page[0]), callback=self.parse_categories)

    def parse_page(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        category = hxs.select("//div[@class='dmBreadCrumbs']//a[not(@title='Luceplan') and not(@title='Home')]/@title").extract()
        category = category[0] if category else None

        current_url = re.sub('~(.*)', '', response.url)

        options = hxs.select("//div[@id='availableVariantForm']/form[@action='#']/input/@value").extract()
        for option in options:
            url = current_url + '~' + option
            yield Request(url=url, meta={'option': True, 'category': category}, callback=self.parse_product, dont_filter=True)

        if not options:
            yield Request(url=response.url, meta={'option': False, 'category': category}, callback=self.parse_product, dont_filter=True)


    def parse_product(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        option_name = ''
        if response.meta['option']:
            option_name = ''.join(hxs.select("//select[contains(@class, 'productVariantSelect')]/option[@selected='selected']/@value").extract())

        url   = response.url
        name  = ''.join(hxs.select("//span[@itemprop='name']/text()").extract())
        if option_name:
            name  = name + ' ' + option_name if option_name else name
        sku   = ''.join(hxs.select('//div[@class="ref"]/strong/text()').re('Ref: (.*)'))
        brand = 'Luceplan'

        image_url  = hxs.select('//img[contains(@class, "large-image")]/@src').extract()
        image_url  = urljoin_rfc(base_url, image_url[0]) if image_url else None
        identifier = hxs.select('//input[@name="productCode"]/@value').extract()[0]
        category   = response.meta['category']

        price = ''.join(hxs.select('//span[@itemprop="price"]/text()').extract())
        try:
            price = float(price.encode('ascii', 'ignore').replace(',', '.'))
        except:
            pass
        shipping_price = 9 if price <= 100 else 0

        l = ProductLoader(item=Product(), response=response)

        l.add_value('brand', brand)
        l.add_value('name', name)
        l.add_value('image_url', image_url)
        l.add_value('url', url)
        in_stock = 'IN VOORRAAD' in ''.join(hxs.select('//div[@id="sideActionBlock"]/div[@class="dmProduct--stock"]/text()').extract()).upper()
        if not in_stock:
            l.add_value('stock', 0)

        l.add_value('sku', sku)
        l.add_value('identifier', identifier)
        l.add_value('category', category)
        l.add_value('price', price)

        yield l.load_item()
