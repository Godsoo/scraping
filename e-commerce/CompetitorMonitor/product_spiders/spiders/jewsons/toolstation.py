from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc, file_uri_to_path

from product_spiders.items \
    import Product, ProductLoaderWithNameStrip as ProductLoader


class ToolStationSpider(BaseSpider):
    name = 'toolstation.com'
    allowed_domains = ['toolstation.com']
    start_urls = ('http://www.toolstation.com/documents/specials/',
                  'http://www.toolstation.com/shop/Power+Tools/d40',
                  'http://www.toolstation.com/shop/Power+Tool+Accessories/d80',
                  'http://www.toolstation.com/shop/Hand+Tools/d10')

    def parse(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        products_list = []

        if file_uri_to_path(response.url) == '/documents/specials/':
            products_list.extend(hxs.select('//a[@class="specialMore"]'
                                            '/@href').extract())
            category = u'Specials'
        else:
            products_list.extend(hxs.select('//ul[@class="subdepartment_list"]'
                                            '/li/a/@href').extract())
            category = file_uri_to_path(response.url)\
                                        .split('/')[2].replace('+', ' ')

        for url in products_list:
                yield Request(urljoin_rfc(base_url, url),
                              callback=self.parse_products,
                              meta={'category': category})

    def parse_products(self, response):
        hxs = HtmlXPathSelector(response)

        def load_product(sku, name, id, category, price, url, image):
            loader = ProductLoader(response=response, item=Product())
            loader.add_value('sku', sku)
            loader.add_value('name', name)
            loader.add_value('identifier', id)
            loader.add_value('url', url)
            loader.add_value('category', category)
            loader.add_value('price', price)
            loader.add_value('image_url', image)

            return loader.load_item()

        p_containers = hxs.select('//div[@class="subdepartment_table"]/form'
                                  '/table/tr[contains(td/@class, "sttA")]')

        for p_container in p_containers:
            sku = p_container.select('./td[@class="sttA"]/a/text()')\
                .extract().pop().strip()
            id = sku
            name = p_container.select('./td[@class="sttB"]/a/text()')\
                .extract().pop().strip()
            category = response.meta.get('category', None)
            price = p_container.select('./td[@class="sttD"]/text()')\
                .extract().pop().strip()
            url = p_container.select('./td[@class="sttA"]/a/@href')\
                .extract().pop().strip()
            try:
                image = p_container.select('../../..'
                                           '/div[contains(@class,''"imageBxCont")]'
                                           '//img/@src').extract().pop().strip()
            except:
                image = None

            yield load_product(sku=sku,
                               name=name,
                               id=id,
                               category=category,
                               price=price,
                               url=url,
                               image=image)
