import json

from lxml import etree

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from product_spiders.items \
    import Product, ProductLoaderWithNameStrip as ProductLoader


class JewsonToolsSpider(BaseSpider):
    name = 'jewsontools.co.uk'
    allowed_domains = ['jewsontools.co.uk']
    start_urls = ('http://www.jewsontools.co.uk/index.php/hand-tools.html',
                  'http://www.jewsontools.co.uk/index.php/power-tools.html')

    def parse(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        product_list = hxs.select('//ol[@class="products-list"]'
                                  '//a[@class="link-learn"]/@href').extract()

        if product_list:
            for url in product_list:
                yield Request(urljoin_rfc(base_url, url),
                              callback=self.parse_product)
            next_page = hxs.select('//a[contains(@class, "next")]'
                                   '/@href').extract()
            if next_page:
                yield Request(urljoin_rfc(base_url, next_page.pop()))
        else:
            links = hxs.select('//ul[@class="category-list"]'
                               '/li/a[@class="link"]/@href').extract()
            for url in links:
                yield Request(urljoin_rfc(base_url, url),
                              callback=self.parse)

    def parse_product(self, response):
        def load_product(sku, name, brand, identifier, category, price, image):
            loader = ProductLoader(response=response, item=Product())
            loader.add_value('sku', sku)
            loader.add_value('name', name)
            loader.add_value('brand', brand)
            loader.add_value('identifier', identifier)
            loader.add_value('url', response.url)
            loader.add_value('category', category)
            loader.add_value('price', price)
            loader.add_value('image_url', image)

            return loader.load_item()

        hxs = HtmlXPathSelector(response)

        first_name = hxs.select('//div[@class="product-view"]'
                                '/h1/text()').extract().pop().strip()

        first_image = hxs.select('//img[@id="image"]/@src').extract().pop()

        try:
            brand = hxs.select('//table[@id="product-attribute-specs-table"]'
                               '/tbody/tr[th/text()="Brand"]/td/text()').extract()[0]
        except:
            brand = u'No brand'

        category = hxs.select('//div[@class="breadcrumbs"]'
                              '/ul/li/a/text()').extract()[-1]

        options = hxs.select('//*[@class="product-options"]').extract()

        scraped = False

        if options:
            jscript = hxs.select('//script[contains(text(), "Product.Config")]')

            if jscript:
                json_config = jscript.select('./text()')\
                    .re(r'Product\.Config\((.+)\)')[0]
                products_config = json.loads(json_config)
                opattr = products_config['attributes'].items()[0][1]['options']
                products = json.loads(json_config)['childProducts']
                attributes = {}
                for option in opattr:
                    for p_id in option['products']:
                        attributes[p_id] = option
                for k, product in products.items():
                    # inc. 20% VAT
                    price = '%.2f' % (float(product['price']) + (float(product['price']) * 0.2))
                    name = first_name + ' ' + attributes[k]['label']
                    attr_tree = etree.HTML(product['productAttributes'])
                    sku = attr_tree.xpath('//table[@id="product-attribute-specs-table"]'
                                          '/tbody/tr/td/text()')[0]
                    identifier = k
                    image = product.get('imageUrl', first_image)

                    if not scraped:
                        scraped = True

                    yield load_product(sku, name, brand, identifier,
                                       category, price, image)

        if not scraped:
            sku = hxs.select('//table[@id="product-attribute-specs-table"]'
                             '/tbody/tr/td/text()').extract()[0]

            identifier = hxs.select('//form[@id="product_addtocart_form"]'
                                    '/@action').re(r'/(\d+)/$')
            price = hxs.select('//span[@class="regular-price"]'
                               '/span[@class="price"]/text()').extract().pop()

            yield load_product(sku, first_name, brand, identifier, category,
                               price, first_image)
