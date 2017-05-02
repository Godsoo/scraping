from scrapy.spider import BaseSpider

from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

from product_spiders.items import Product, \
    ProductLoaderWithNameStrip as ProductLoader
from product_spiders.utils import extract_price2uk

class RefrinclimaItSpider(BaseSpider):
    name = 'refrinclima.it'
    allowed_domains = ['refrinclima.it']
    start_urls = ('http://store.refrinclima.it/',)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        categ_urls = hxs.select('//ul[@class="umenu"]/li/a/@href').extract()

        for categ_url in categ_urls:
            yield Request(urljoin_rfc(base_url, categ_url),
                          callback=self.parse_category)

    def parse_category(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        subcat_urls = hxs.select('//ul[@class="bullet"]/li/a/@href').extract()

        for subcat_url in subcat_urls:
            yield Request(urljoin_rfc(base_url, subcat_url),
                          callback=self.parse_products)

    def parse_products(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        products = hxs.select('//ul[@id="product_list"]/li')

        for product in products:
            try:
                identifier = product\
                    .select('.//a[contains(@class, "ajax_add_to_cart_button")]/@href')\
                    .re(r'^.*&id_product=(\d+)&token')
                name = product.select('.//h3/a/@title').extract().pop().strip()
                url = urljoin_rfc(base_url,
                                  product
                                    .select('.//h3/a/@href').extract().pop().strip()
                                    )
                price = extract_price2uk(product
                                         .select('.//div[@class="content_price"]'
                                                 '/*[@class="price"]/text()')
                                         .extract().pop().strip())
                image = urljoin_rfc(get_base_url(response),
                                    product.select('.//a[@class="product_img_link"]'
                                                   '/img/@src').extract().pop().strip())

                category = None
                try:
                    category = hxs.select('//span[@class="navigation_page"]'
                                          '/text()').extract().pop().strip()
                except:
                    pass

            except:
                pass
            else:
                if not identifier:
                    loader = ProductLoader(response=response, item=Product())
                    loader.add_value('name', name)
                    loader.add_value('url', url)
                    loader.add_value('brand', category)
                    loader.add_value('price', price)
                    loader.add_value('image_url', image)
                    yield Request(url,
                                  meta={'product': loader.load_item()},
                                  callback=self.parse_identifier)
                else:
                    loader = ProductLoader(response=response, item=Product())
                    loader.add_value('name', name)
                    loader.add_value('identifier', identifier)
                    loader.add_value('url', url)
                    loader.add_value('brand', category)
                    loader.add_value('price', price)
                    loader.add_value('image_url', image)

                    yield loader.load_item()

        next_page = hxs.select('//div[@id="pagination"]'
                               '//li[@id="pagination_next"]/a/@href').extract()

        if next_page:
            yield Request(urljoin_rfc(base_url, next_page.pop().strip()),
                          callback=self.parse_products)

    def parse_identifier(self, response):
        hxs = HtmlXPathSelector(response)
        product = response.meta['product']

        identifier = hxs.select('//input[@name="id_product"][1]/@value').extract()
        if identifier:
            product['identifier'] = identifier[0]
            yield product
