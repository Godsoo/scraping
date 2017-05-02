import re

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader


class PramWorldSpider(BaseSpider):
    name = 'uberkids-preciouslittleone.com'
    allowed_domains = ['preciouslittleone.com']
    start_urls = ['http://www.preciouslittleone.com']

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        categories = hxs.select('//div[@class="megaMenu"]//a/@href').extract()

        for category in categories:
            yield Request(urljoin_rfc(base_url, category), meta=response.meta)

        products = hxs.select('//div[@class="productList"]//p[@class="catprodtitle"]/a/@href').extract()
        for product in products:
            yield Request(urljoin_rfc(get_base_url(response), product), callback=self.parse_product, meta=response.meta)

        nextp = hxs.select('//a[contains(text(), "Next")]/@href').extract()
        if nextp:
            yield Request(urljoin_rfc(get_base_url(response), nextp[0]), meta=response.meta)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        loader = ProductLoader(response=response, item=Product())

        loader.add_value('url', response.url)
        loader.add_xpath('identifier', '//input[@name="hidProdId"]/@value')
        sku = hxs.select('//span[@itemprop="mpn"]/text()').extract()
        loader.add_value('sku', sku)
        loader.add_xpath('name', '//div[contains(@id, "prodinfo_center")]//*[@class="productPageName"]/text()')

        price = re.findall('ecomm_totalvalue: (.*),', response.body)
        price = price[0] if price else 0
        loader.add_value('price', price)

        categories = hxs.select('//ul[@class="breadcrumbs"]/li[@itemprop="itemListElement"]/a/span/text()').extract()[1:]
        loader.add_value('category', categories)

        image_url = hxs.select('//img[@id="mainimage"]/@src').extract()
        if image_url:
            loader.add_value('image_url', urljoin_rfc(get_base_url(response), image_url[0]))

        product_brand = ''
        brands = hxs.select('//select[@name="selLSBrand"]//option/text()').extract()
        for brand in brands:
            if len(brand)>3 and loader.get_output_value('name').upper().startswith(brand.upper().strip()):
                product_brand = brand.strip()
                break

        loader.add_value('brand', product_brand)

        out_of_stock = hxs.select('//form[@id="addcartform"]//span[contains(text(), "Out of stock")]')

        if out_of_stock:
            loader.add_value('stock', 0)

        if loader.get_output_value('price')<50:
            loader.add_value('shipping_cost', 3.95)

        item = loader.load_item()
        if item.get('identifier'):
            yield item
