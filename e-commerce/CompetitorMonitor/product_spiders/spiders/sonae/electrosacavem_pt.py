from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from urlparse import urljoin as urljoin_rfc
from scrapy.utils.response import get_base_url
from product_spiders.utils import extract_price_eu as extract_price
from scrapy.http import Request
from scrapy.utils.url import url_query_parameter


class ElectrosacavemSpider(BaseSpider):
    name = 'sonae-electrosacavem.pt'
    allowed_domains = ['electrosacavem.pt']
    start_urls = ('http://www.electrosacavem.pt/',)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        # parse categories
        urls = hxs.select('/html/body/table/tr[1]/td/table[2]/tr//a/@href').extract()
        for url in urls:
            if 'produtos.php' in url:
                yield Request(urljoin_rfc(base_url, url), callback=self.parse_products_list)

    def parse_products_list(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        urls = hxs.select('/html/body/table//tr[2]/td/table//tr[1]/td[2]/table//tr[5]/td//table//tr//a/@href').extract()
        for url in urls:
            if 'produtos.php' in url:
                yield Request(urljoin_rfc(base_url, url), callback=self.parse_products_list)
            if 'info.php' in url:
                yield Request(urljoin_rfc(base_url, url), callback=self.parse_product)

    @staticmethod
    def parse_product(response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        product_loader = ProductLoader(item=Product(), selector=hxs)
        price = hxs.select('/html/body/table//tr[2]/td/table//tr[1]/td[2]/table[3]//tr[2]/td/table//tr/td/font/text()').extract()
        if not price:
            price = ['0']
            product_loader.add_value('stock', 0)
        price = extract_price(price[0])
        product_loader.add_value('price', price)
        identifier = url_query_parameter(response.url, 'identif')
        product_loader.add_value('identifier', identifier)
        name = hxs.select('/html/body/table//tr[2]/td/table/tr[1]/td[2]/table[1]//tr[1]/td/text()').extract()[-1]
        name = name.replace('::', '').strip()
        product_loader.add_value('name', name)
        sku = hxs.select('/html/body/table//tr[2]/td/table//tr[1]/td[2]/table[3]//tr[4]/td/table//tr/td[1]/h1/span/text()').extract()
        if not sku:
            sku = identifier
        else:
            sku = sku[0].replace('SKU:&nbsp;', '')
        product_loader.add_value('sku', sku)
        image_url = hxs.select('/html/body/table//tr[2]/td/table//tr[1]/td[2]/table[3]//tr[1]/td[1]/img/@src').extract()
        if image_url:
            product_loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
        category = hxs.select('/html/body/table//tr[2]/td/table//tr[1]/td[2]/table[1]//tr[1]/td//a/text()').extract()
        product_loader.add_value('category', category)
        product_loader.add_value('url', response.url)
        product = product_loader.load_item()
        yield product
