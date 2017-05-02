from scrapy.selector import HtmlXPathSelector
from scrapy.spider import BaseSpider
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from urlparse import urljoin as urljoin_rfc
import itertools
from product_spiders.utils import extract_price
import re

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader


class CBMrmattressCoUkSpider(BaseSpider):
    name = 'colourbank-mrmattress.co.uk'
    allowed_domains = ['mrmattress.co.uk']
    start_urls = ['http://www.mrmattress.co.uk/manufacturers']
    brands = []

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        image_urls = hxs.select('//div[@class="manufacturerInside"]/a/img/@src').extract()
        brand_names = hxs.select('//div[@class="manufacturerLink"]/a/text()').extract()
        self.brands = dict(zip(image_urls, brand_names))
        for url in hxs.select('//table[contains(@class, "topmenu")]//a[@class="menu"]/@href').extract():
            url = urljoin_rfc(get_base_url(response), url)
            yield Request(url, callback=self.parse_subcats)

    def parse_subcats(self, response):
        hxs = HtmlXPathSelector(response)
        subcats = hxs.select('//div[@class="block-categories-catalog"]//a/@href').extract()
        for url in subcats:
            url = urljoin_rfc(get_base_url(response), url)
            yield Request(url, callback=self.parse_subcats)
        if not subcats:
            for url in hxs.select('//div[@class="productItem"]//h2[@class="productItemTitle  "]/a/@href').extract():
                url = urljoin_rfc(get_base_url(response), url)
                yield Request(url, callback=self.parse_product)
            show_all = hxs.select('//table[@class="sortViewPage"]//td[@class="view"]//a[contains(@href, "show_all=1")]/@href').extract()
            if not show_all:
                show_all = response.xpath('//span/a[contains(text(), "all")]/@href').extract()
            if show_all:
                yield Request(urljoin_rfc(get_base_url(response), show_all[0]), callback=self.parse_products_list)

    def parse_products_list(self, response):
        hxs = HtmlXPathSelector(response)
        for url in hxs.select('//div[@class="productItem"]//h2[@class="productItemTitle  "]/a/@href').extract():
            url = urljoin_rfc(get_base_url(response), url)
            yield Request(url, callback=self.parse_product)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        product_loader = ProductLoader(item=Product(), selector=hxs)
        product_identifier = hxs.select('//td[@class="blockTD"]//input[@name="item_id"]/@value').extract()[0]
        product_loader.add_value('identifier', product_identifier)
        product_loader.add_value('url', response.url)
        price = hxs.select('//div[@class="productItemPrices"]//span[@class="salesPrice"]//text()').extract()
        if not price:
            price = hxs.select('//div[@class="productItemPrices"]//span[@class="price"]//text()').extract()
        price = extract_price(price[0])
        product_loader.add_value('price', price)
        name = hxs.select('//td[@class="blockTD"]//div[@class="right-side"]/h1/text()').extract()[0].strip()
        product_loader.add_value('name', name)
        category = hxs.select('//td[@class="breadcrumbDelimiter"]//a[2]/text()').extract()[0]
        product_loader.add_value('category', category)
        product_loader.add_value('sku', name)
        brand = hxs.select('//div[@class="manufacturerImage"]/img/@src').extract()
        if brand:
            brand = self.brands[brand[0]]
            product_loader.add_value('brand', brand)
        img = hxs.select('//div[@class="product-item-image"]/img/@src').extract()
        if img:
            product_loader.add_value('image_url', urljoin_rfc(get_base_url(response), img.pop()))

        product = product_loader.load_item()

        options = hxs.select('//div[@class="productItemPoperties"]//select')
        if options:
            variations = []
            for opt in options:
                items = opt.select('./option[@value!=""]')
                var = []
                for item in items:
                    item_name = item.select('./text()').extract()[0].strip()
                    item_price = item_name[item_name.find("(")+1:item_name.find(")")]
                    if not u'\xa3' in item_price:
                        item_price = re.search(u'(\xa3.*)\)', item_name)
                        item_price = item_price.group(1) if item_price else '0.00'
                    item_name = re.sub(r'\([^)]*\)', '', item_name).strip()
                    item_value = item.select('./@value').extract()[0]
                    var.append([item_name, item_value, item_price])
                variations.append(var)
            options = itertools.product(*variations)
            for opt in options:
                prod = Product(product)
                name = prod['name']
                identifier = prod['identifier']
                base_price = prod['price']
                price = extract_price('0')
                for item in opt:
                    name += ' - ' + str(item[0])
                    identifier += '_' + str(item[1])
                    opt_price = extract_price(str(item[2].replace(u'\xa3', '')))
                    if opt_price >= base_price:
                        base_price = opt_price
                    else:
                        price += opt_price

                prod['identifier'] = identifier
                prod['name'] = name
                prod['price'] = price + base_price
                yield prod
        else:
            prod = Product(product)
            yield prod
