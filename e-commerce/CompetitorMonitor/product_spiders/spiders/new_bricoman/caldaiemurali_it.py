from scrapy.contrib.spiders import SitemapSpider
# from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url
from product_spiders.items import Product, ProductLoader


class CaldaiemuraliItSpider(SitemapSpider):
    name = "newbricoman-caldaiemurali.it"
    allowed_domains = ["caldaiemurali.it"]
    start_urls = ('http://www.caldaiemurali.it/',)

    sitemap_urls = ['http://www.caldaiemurali.it/sitemap.xml']
    sitemap_rules = [
        ('/', 'parse_item'),
    ]

    ''''
    def start_requests(self):
        for url in self.start_urls:
            yield Request(url)

        for req in list(super(CaldaiemuraliItSpider, self).start_requests()):
            yield req
    '''

    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        categories = hxs.select("//ul[@id='ma-accordion']//a/@href").extract()
        for category in categories:
            if not category.startswith('javascript'):
                url = urljoin_rfc(get_base_url(response), category)
                yield Request(url, callback=self.parse)

        pages = hxs.select("//div[@class='pages']/ol/li/a/@href").extract()
        for page in pages:
            url = urljoin_rfc(get_base_url(response), page)
            yield Request(url, callback=self.parse)

        items = set(hxs.select("//div[@class='category-products']//a/@href").extract())
        if len(items) < 12:
            self.log('>>> WARNING: len(items) < 12')
        for item in items:
            url = urljoin_rfc(get_base_url(response), item)
            yield Request(url, callback=self.parse_item)

    def parse_item(self, response):
        url = response.url
        hxs = HtmlXPathSelector(response)
        name = hxs.select("//div[@class='product-name']/h1/text()").extract()
        if not name:
            self.log("ERROR - NO NAME!")
            return
        name = name[0]
        price = hxs.select("//*[@itemprop='price']/text()").extract()
        if not price:
            self.log("ERROR - NO PRICE!")
            return
        price = price[0].replace(".", "").replace(",", ".")
        identifier = hxs.select("//input[@type='hidden'][@name='product']/@value").extract()
        if not identifier:
            self.log("ERROR - NO IDENTIFIER!")
            return
        identifier = identifier[0]
        product_image = hxs.select('//*[@id="ma-zoom1"]/img/@src').extract()
        if not product_image:
            self.log("ERROR - no image found!")
        else:
            product_image = urljoin_rfc(get_base_url(response), product_image[0])
        category = hxs.select('//div[@class="breadcrumbs"]/ul/li[2]/a/text()').extract()
        if not category:
            self.log("ERROR - no category found!")
        else:
            category = category[0].strip()

        out_stock = hxs.select('//div[@class="product-shop"]//p[contains(@class, "availability") '
                               'and contains(@class, "out-of-stock")]')

        shipping = hxs.select('//table[@id="product-attribute-specs-table"]'
                              '//th[@class="label" and contains(text(), "Spese Spedizione")]'
                              '/following-sibling::td/text()').extract()
        if shipping:
            shipping_cost = shipping[0].strip()
            if shipping_cost.lower() == 'gratis':
                shipping_cost = '0.0'
            else:
                shipping_cost = shipping[0].replace(',', '.')
        else:
            shipping_cost = None

        brand = hxs.select('//table[@id="product-attribute-specs-table"]'
                           '//th[@class="label" and contains(text(), "Marca")]'
                           '/following-sibling::td/a/@title').extract()
        if not brand:
            brand = hxs.select('//table[@id="product-attribute-specs-table"]'
                               '//th[@class="label" and contains(text(), "Marca")]'
                               '/following-sibling::td/text()').extract()

        l = ProductLoader(item=Product(), response=response)
        l.add_value('identifier', identifier)
        l.add_value('name', name)
        l.add_value('url', url)
        l.add_value('price', price)
        l.add_value('image_url', product_image)
        l.add_value('category', category)
        if brand:
            l.add_value('brand', brand[0].strip())
        if out_stock:
            l.add_value('stock', 0)
        if shipping_cost is not None:
            l.add_value('shipping_cost', shipping_cost)

        yield l.load_item()
