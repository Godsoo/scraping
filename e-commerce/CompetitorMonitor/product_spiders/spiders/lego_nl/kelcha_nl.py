from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

from product_spiders.utils import extract_price_eu
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader


class KelchaSpider(BaseSpider):

    name = 'kelcha.nl'
    allowed_domains = ['kelcha.nl']
    start_urls = [
        'http://www.kelcha.nl',
    ]

    user_agent = 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:17.0) Gecko/17.0 Firefox/17.0'


    def parse(self, response):

        #== doesn't work without Upgrade-Insecure-Requests meta (07/09/15) ==#
        headers = {'User-agent': self.user_agent, 'Upgrade-Insecure-Requests': '1'}
        yield Request(
            url=self.start_urls[0],
            callback=self.parse_subcategory,
            headers=headers,
        )


    def parse_subcategory(self, response):

        hxs = HtmlXPathSelector(response)
        subcategories = hxs.select("//span[text()='LEGO' or text()='DUPLO']/following::ul[1]/li/a/@href").extract()

        for subcat in subcategories[5:]:
            yield Request(urljoin_rfc(get_base_url(response), subcat), callback=self.parse_subcategory)

        products = hxs.select('//div[@class="item-title"]//a/@href').extract()
        if products:
            for product in products:
                yield Request(product, callback=self.parse_product, meta=response.meta)

        try:
            next_page = hxs.select("//a[contains(@class,'next')]/@href").extract()[0]
            yield Request(next_page, callback=self.parse_subcategory)
        except:
            pass


    def parse_product(self, response):

        hxs = HtmlXPathSelector(response)
        loader = ProductLoader(item=Product(), selector=hxs)

        price = hxs.select('//span[@itemprop="price"]/text()').extract()[0].strip().replace(',', '.')
        categories = hxs.select('//div[contains(@class,"breadcrumbs")]/ul//span[@itemprop="title"]/text()').extract()
        categories.remove('Home')
        brand = 'Lego' if 'LEGO' in categories else 'Duplo'
        stock = hxs.select('//link[@itemprop="availability"]/@href').extract()
        stock = stock[0] if stock else ''
        stock = 1 if 'instock' in stock.lower() else 0
        product_image = hxs.select('//img[@id="image"]/@src').extract()
        product_image = urljoin_rfc(get_base_url(response), product_image[0]) if product_image else ''

        loader.add_xpath('identifier', '//input[@name="product"]/@value')
        loader.add_xpath('name', '//h2[@itemprop="name"]/text()')
        loader.add_xpath('sku', '//input[@name="product"]/@value')
        loader.add_value('image_url', product_image)
        loader.add_value('url', response.url)
        loader.add_value('price', price)
        loader.add_value('brand', brand)
        loader.add_value('stock', stock)

        for category in categories:
            loader.add_value('category', category)

        yield loader.load_item()
