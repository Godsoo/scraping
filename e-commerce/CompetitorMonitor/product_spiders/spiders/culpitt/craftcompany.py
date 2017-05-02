from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader
from urlparse import urljoin as urljoin_rfc
from scrapy.utils.response import get_base_url
from product_spiders.utils import extract_price
from w3lib.url import url_query_parameter, add_or_replace_parameter


class CraftcompanySpider(BaseSpider):
    name = 'craftcompany'
    allowed_domains = ['craftcompany.co.uk']
    start_urls = ('http://www.craftcompany.co.uk/',)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        #parse menu categories
        urls = response.xpath('//nav[@id="nav"]//a/@href').extract()
        for url in urls:
            if 'shop-by-brand' not in url:
                yield Request(urljoin_rfc(base_url, url), callback=self.parse_cats_or_product_list)

    def parse_cats_or_product_list(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        #parse pagination
        if response.css('button.load-more'):
            page = url_query_parameter(response.url, 'p', '1')
            url = add_or_replace_parameter(response.url, 'p', int(page) + 1)
            yield Request(url, self.parse_cats_or_product_list)

        #parse products list
        products = response.xpath('//ul[contains(@class, "products-grid")]/li')
        for product in products:
            product_loader = ProductLoader(item=Product(), selector=product)
            price = product.xpath('.//span[@class="price"]/text()').extract()[-1]
            product_loader.add_value('price', extract_price(price))
            product_name = product.xpath('.//h2/a/text()').extract()[0]
            image_url = product.xpath('.//img/@src').extract()[0]
            product_loader.add_value('image_url', urljoin_rfc(base_url, image_url))
            product_loader.add_value('name', product_name)
            product_url = product.xpath('.//h2/a/@href').extract()[0]
            product_loader.add_value('url', urljoin_rfc(base_url, product_url))
            identifier = product.xpath('.//*/@data-product-id').extract()
            if not identifier:
                identifier = product.xpath('.//span/@id').re('product-price-(\d+)') or product.xpath('.//img/@id').re('product-collection-image-(\d+)')
            product_loader.add_value('identifier', identifier[0])
            sku = product.css('span.sku-value::text').extract_first()
            sku = sku.strip().replace('SKU: ', '').replace('*', '')
            product_loader.add_value('sku', sku)
            category = response.xpath('//div[@class="breadcrumbs"]/ul/li[2]/a/text()').extract()
            if category:
                product_loader.add_value('category', category[0])
            if product.css('p.out-of-stock'):
                product_loader.add_value('stock', 0)
            product = product_loader.load_item()
            yield product
