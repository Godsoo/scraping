from decimal import Decimal, ROUND_UP
import re
import os
import csv
import shutil
from scrapy import signals
from scrapy import log
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url
from scrapy.xlib.pydispatch import dispatcher

from cStringIO import StringIO

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from jersey_electricity_items import JerseyElectricityMeta

HERE = os.path.abspath(os.path.dirname(__file__))

def format_price(price, rounding=None):
    if price is None:
        return Decimal('0.00')

    return price.quantize(Decimal('0.01'), rounding=rounding or ROUND_UP)

class JohnLewisSpider(BaseSpider):

    name = 'jerseyelectricity-johnlewis.com'
    allowed_domains = ['johnlewis.com']
    filename = os.path.join(HERE, 'johnlewis_categories.csv')
    start_urls = ('file://' + filename,)


    def start_requests(self):

        country_url = "http://www.johnlewis.com/store/international/ajax/changeCountryAjaxRequest.jsp"
        formdata = {'country': 'GB',
                    'sourceUrl': 'http://www.johnlewis.com/',
                    'switchToggle': 'Change Country Overlay'}
        yield FormRequest(country_url, formdata=formdata)


    def parse(self, response):

        with open(self.filename) as f:
            reader = csv.DictReader(f)
            for row in reader:
                yield Request(row['url'], callback=self.parse_categories)


    def parse_categories(self, response):

        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        for cat in hxs.select('//section[contains(@class, "lt-nav-container-links")]//a[contains(@href,"/electricals")]/@href').extract():
            yield Request(urljoin_rfc(get_base_url(response), cat), callback=self.parse_categories)
        for url in hxs.select('//div[@class="result-row"]/article/a/@href').extract():
            yield Request(urljoin_rfc(get_base_url(response), url), callback=self.parse_products)
        next = hxs.select('//li[@class="next"][1]/a/@href').extract()
        if next:
            yield Request(url=urljoin_rfc(base_url, next[0]), callback=self.parse_categories)


    def parse_products(self, response):

        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)
        products_urls = hxs.select('//*[@id="prod-product-colour"]/ul//li//a/@href').extract()

        if products_urls:
            for url in products_urls:
                purl = urljoin_rfc(base_url, url)
                yield Request(
                    url=purl,
                    callback=self.parse_product,
                    dont_filter=True
                )
        else:
            for p in self.parse_product(response):
                yield p


    def parse_product(self, response):

        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        option_links = hxs.select('//div/ul[@class="selection-grid selection-grid-small"]/li/a/@href').extract()
        if not response.meta.get('option', False) and option_links:
            for link in option_links:
                url = urljoin_rfc(response.url, link)
                yield Request(url, meta={'option':True}, dont_filter=True, callback=self.parse_product)
            return

        product_code = hxs.select('//div[@id="prod-product-code"]/p/text()').extract()

        if not product_code:
            return

        name = hxs.select('//*[@id="prod-title"]//text()').extract()
        if not name:
            name = hxs.select('//*[@id="content"]//h1/text()').extract()
            if not name:
                return

        image_url = hxs.select('//img[@itemprop="image"]/@src').extract()
        if image_url:
            image_url = urljoin_rfc(base_url, image_url[0])

        loader = ProductLoader(item=Product(), selector=hxs)

        loader.add_value('identifier', product_code)
        loader.add_value('sku', product_code)
        loader.add_value('url', response.url)
        loader.add_value('name', ' '.join([n.strip() for n in name]).strip())
        loader.add_value('image_url', image_url)

        extra_description = hxs.select('//li[contains(@class, "selected")]//span/text()').extract()
        if extra_description:
            extra_description = extra_description[0]
            if extra_description.upper() not in loader.get_output_value('name').upper():
                loader.add_value('name', ', ' + extra_description)

        loader.add_xpath('category', '//div[@id="breadcrumbs"]/ol/li[position()>1 and position()<last()]//a/text()')
        loader.add_xpath('brand', 'normalize-space(//div[@itemprop="brand"]/span/text())')

        try:
            loader.add_xpath('stock', '//div[@data-jl-stock]/@data-jl-stock')
        except ValueError:
            loader.add_value('stock', '0')

        item = loader.load_item()
        try:
            price = hxs.select('//span[@itemprop="price"]/text()|//div[@id="prod-add-to-basket"]//strong[@class="price"]/text()').extract()
            if not price:
                price = hxs.select('//div[@id="prod-price"]/p[@class="price"]/strong/text()').extract()

            price = price[0] if price else ''
            price = re.findall(re.compile("([\d,.]+)"), price)[0].replace(',', '')

            metadata = {}
            metadata['site_price'] = price
            item['metadata'] = metadata

            price = format_price(Decimal(price) / Decimal('1.20') * Decimal('1.05'))
            item['price'] = price
        except Exception as e:
            item['price'] = ''

        if item['identifier']:
            yield item
