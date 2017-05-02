from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from urlparse import urljoin as urljoin_rfc
from scrapy.utils.response import get_base_url
from product_spiders.utils import extract_price
from scrapy.http import Request, FormRequest
from scrapy.item import Item, Field


class ZyroMeta(Item):
    ean = Field()


class BikeinnSpider(BaseSpider):
    name = 'zyro-bikeinn.com'
    allowed_domains = ['bikeinn.com']
    start_urls = ('http://www.bikeinn.com/', )

    def parse(self, response):
        form_data = {'options': '209'}
        yield FormRequest.from_response(response,
                                        formname='paises',
                                        formdata=form_data,
                                        callback=self.parse_categories,
                                        dont_filter=True)

    def parse_categories(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        categories = hxs.select('//div[@class="categorias"]//a/@href').extract()
        categories += hxs.select('//div[@class="menuCateg"]//a/@href').extract()
        for url in categories:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_categories)

        for url in hxs.select('//div[@class="paginadoTop"]//a/@href').extract():
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_categories)

        for url in hxs.select('//div[contains(@class,"boxProd")]//p[@class="BoxPriceName"]/a/@href').extract():
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product)

    @staticmethod
    def parse_product(response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        name = hxs.select('//h1[@class="name"]/text()').extract()[0]
        identifier = hxs.select('//meta[@itemprop="sku"]/@content').extract()[0]
        sku = hxs.select('//div[@class="detalleMarcaProducto2"]/strong[contains(text(), "Item model number:")]/following-sibling::text()[1]').extract()
        sku = sku[0] if sku else ''
        ean = hxs.select('//div[@class="detalleMarcaProducto2"]/strong[contains(text(), "EAN retail barcodes:")]/following-sibling::text()[1]').extract()
        ean = ean[0].strip() if ean else None
        brand = hxs.select('//*[@id="brandProduct"]/p/a/img/@alt').extract()
        brand = brand[0] if brand else ''
        image_url = hxs.select('//*[@id="zoom_01"]/@src').extract()
        category = hxs.select('//*[@id="wayProd"]//a/span/text()').extract()[-3:]
        price = hxs.select('//*[@id="total_dinamic"]/span/text()').extract()[0]
        price = extract_price(price)

        products = hxs.select('//*[@id="datesBuy"]//select[@name="talla_color"]/option')
        for product in products:
            product_loader = ProductLoader(item=Product(), selector=product)
            p_name = product.select('./text()').extract()[0]
            p_name = name if p_name == '- ' else name + ' ' + p_name
            p_identifier = product.select('./@value').extract()[0]
            product_loader.add_value('identifier', identifier + '_' + p_identifier)
            product_loader.add_value('name', p_name)
            product_loader.add_value('sku', sku)
            if image_url:
                product_loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
            product_loader.add_value('price', price)
            product_loader.add_value('category', category)
            product_loader.add_value('brand', brand)
            product_loader.add_value('url', response.url)
            product = product_loader.load_item()
            metadata = ZyroMeta()
            metadata['ean'] = ean
            product['metadata'] = metadata
            yield product
