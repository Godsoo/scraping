import re
import json
from decimal import Decimal

import itertools

from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.base_spiders.bigsitemethodspider import BigSiteMethodSpider

from scrapy import log


class WorldStoresCoUkSpider(BigSiteMethodSpider):
    name = 'worldstores.co.uk'
    allowed_domains = ['worldstores.co.uk']
    website_id = 489111

    start_urls = ('http://www.worldstores.co.uk/',)

    full_crawl_day = 3

    new_system = True
    old_system = False

    def parse_full(self, response):
        hxs = HtmlXPathSelector(response)

        for url in hxs.select(u'//ul[@id="menu"]//a/@href').extract():
            url = urljoin_rfc(get_base_url(response), url)
            yield Request(url, callback=self.parse_product_list)

    def parse_product_list(self, response):
        hxs = HtmlXPathSelector(response)

        for url in hxs.select(u'//div[@class="pagination"]//a/@href').extract():
            url = urljoin_rfc(get_base_url(response), url)
            yield Request(url, callback=self.parse_product_list)

        for url in hxs.select(u'//table[@class="pagwidth"]//a/@href').extract():
            url = urljoin_rfc(get_base_url(response), url)
            yield Request(url, callback=self.parse_product_list)

        for url in hxs.select(u'//table[@class="mainbody_tablecat"]//a/@href').extract():
            url = urljoin_rfc(get_base_url(response), url)
            yield Request(url, callback=self.parse_product_list)

        for url in hxs.select(u'//div[contains(@class,"item-name")]/a/@href').extract():
            url = urljoin_rfc(get_base_url(response), url)
            yield Request(url, callback=self.parse_product)

        for url in hxs.select(u'//div[@id="item_image"]/a/@href').extract():
            url = urljoin_rfc(get_base_url(response), url)
            yield Request(url, callback=self.parse_product)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)

        name = "".join(hxs.select(u'//h1/text()').extract()).strip()
        if not name:
            name = "".join(hxs.select(u'//div[contains(@class, "ws_product_details_item_name")]/text()').extract()).strip()
        if not name:
            name = "".join(hxs.select(u'//input[@name="item_name"]/@value').extract()).strip()
        if not name:
            log.msg('No product found on page <%s>' % (response.url))
            return

        category = hxs.select(u'//div[@class="breadcrumb"]/a[2]/text()').extract()
        if not category:
            breadcrumbs = hxs.select(u'//div[contains(@class, "ws-breadcrumb")]/a[@class="breadcrumb"]/text()').extract()
            if len(breadcrumbs) > 1:
                category = breadcrumbs[-1]

        brand = hxs.select(u'//div[@class="manufacturer-logo"]/a/img/@alt').extract()
        if not brand:
            brand_link = hxs.select('//div[@class="ws_product_details_item_brand_link"]/a/@href').re(r'\/([^/]*).htm[l]?$')
            if brand_link:
                brand = brand_link[0].replace("_", " ")
            if not brand:
                brand =  "".join(hxs.select('//span[contains(@class, "sku_brand")]/text()').extract())

        sku = "".join(hxs.select('//form[@name="BuyMainForm"]/input[@name="item_id"]/@value').extract()).strip()
        if not sku:
            sku = hxs.select('//div[contains(@class, "order_code")]/text()').extract()[0].split(' ')[0]

        price = "".join(hxs.select('//form[@name="BuyMainForm"]/input[@name="base_price"]/@value').extract()).strip()
        if not price:
            price = "".join(hxs.select('//div[contains(@class, "item_price_price")]/span[contains(@class, "ourprice")]/text()').extract())

        product_loader = ProductLoader(item=Product(), selector=hxs)
        product_loader.add_value('url', response.url)
        product_loader.add_value('name', name)
        product_loader.add_value('category', category)

        img = hxs.select(u'//a[@id="imageZoom"]/@href').extract()
        if img:
            product_loader.add_value('image_url', urljoin_rfc(get_base_url(response), img[0]))
        product_loader.add_value('brand', brand)
        product_loader.add_value('sku', sku)
        product_loader.add_value('price', price)

        def option_name(opt):
            name = ''
            for mcode in opt.split('-')[1:]:
                if name:
                    name += ', '
                name += hxs.select(u'normalize-space(//option[@mcode="' + mcode + '"]/text())').extract()[0]
            return name

        product = product_loader.load_item()

        attributes = hxs.select('//div[@class="option_container clearfix"]//select[not(contains(@id, "quantity"))]')

        if attributes:
            ajax_url = 'http://www.worldstores.co.uk/ajax.get_exact_product.php'
            options = []
            for attribute in attributes:
                formdata = {}
                attribute_id, tmp, item_id = attribute.select('@id').extract()[0].rpartition('_')

                tmp = []
                for option in attribute.select('option/@value').extract():
                    tmp.append(('attributes['+attribute_id+']', option))     
                options.append(tmp)

            item_id = hxs.select('//input[@id="item_details_item_id"]/@value').extract()[0]
            option_combinations = list(itertools.product(*options))
            for option_combination in option_combinations:
                option_name = ''
                formdata = {}
                formdata['item_id'] = item_id
                for attr, value in option_combination:
                    formdata[attr] = value
                    option_name = option_name + ' ' + value if option_name else value
                yield FormRequest(ajax_url, 
                                  dont_filter=True, 
                                  method='POST', 
                                  formdata=formdata, 
                                  callback=self.parse_option,
                                  meta={'prod':product, 'option_name': option_name})
            
        elif sku:
            prod = Product(product)
            prod['identifier'] = sku
            self.matched_identifiers.add(prod['identifier'])
            yield prod

    def parse_option(self, response):
        meta = response.meta
        product = meta.get('prod')
        data = json.loads(response.body).get('data', None)
        if data:
            prod = Product(product)
            prod['price'] = data['ourprice']
            prod['name'] = prod['name'] + ' ' + response.meta.get('option_name')
            
            prod['identifier'] = data['item_id'] + '-' + data['id']
            yield prod
        else:
            log.msg('ERROR extracting option json: ' + product['url'])
