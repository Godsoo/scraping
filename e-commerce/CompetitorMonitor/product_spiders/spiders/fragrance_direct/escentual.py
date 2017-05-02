from decimal import Decimal

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url
from scrapy.xlib.pydispatch import dispatcher
from scrapy import signals
from scrapy.exceptions import DontCloseSpider

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.utils import extract_price

from fragrancedirectitem import FragranceDirectMeta


def normalize_space(s):
    ''' Cleans up space/newline characters '''
    import re
    return re.sub(r'\s+', ' ', s.replace(u'\xa0', ' ').strip())

class EscentualSpider(BaseSpider):
    name = 'fragrancedirect-escentual.com'
    allowed_domains = ['escentual.com']
    start_urls = ['http://www.escentual.com']
    categories = []
    user_agent = 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:42.0) Gecko/20100101 Firefox/42.0'

    def _start_requests(self):
        yield Request('http://www.escentual.com/skincare/french-pharmacy/insitutesthederm040/',
                      headers = {'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:42.0) Gecko/20100101 Firefox/42.0'}, callback=self.parse_product)

    def __init__(self, *args, **kwargs):
        super(EscentualSpider, self).__init__(*args, **kwargs)
        dispatcher.connect(self.spider_idle, signals.spider_idle)

    def spider_idle(self, spider):
        if spider.name == self.name and self.categories:
            r = self.categories.pop()
            self._crawler.engine.crawl(r, self)
            raise DontCloseSpider

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        categories = hxs.select('//ul[@id="nav"]//li[contains(@class, "parent")]//li[not(contains(@class,"brands"))]//a/@href').extract()
        for category in categories:
            if '/all-' not in category:
                self.categories.append(Request(urljoin_rfc(base_url, category),
                              callback=self.parse_page))

    # Can either a subcategory or product listing page
    def parse_page(self, response):
        hxs = HtmlXPathSelector(response)

        # Try to find products
        for url in hxs.select('//div[@class="product-name"]/a/@href').extract():
                yield Request(urljoin_rfc(response.url, url),
                              callback=self.parse_product)

        for page in hxs.select('//div[@class="pages"]//a/@href').extract():
            yield Request(urljoin_rfc(response.url, page), callback=self.parse_page)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        product_loader = ProductLoader(item=Product(), selector=hxs)
        product_loader.add_value('url', response.url)
        product_loader.add_xpath('name', '//h1/span[@class="name-name" or @class="name-range" or @class="name-size"]/text()')
        product_loader.add_xpath('brand', u'//h1/a[@class="name-brand"]/text()')
        product_loader.add_xpath('sku', '//meta[@name="esc-sku"]/@content')
        product_loader.add_xpath('category', '//div[@class="breadcrumbs"]/ul/li[position() > 1 and position() < last()-1]//a/text()')
        img = hxs.select(u'//div[@class="product-image-wrapper"]//img/@src').extract()
        if img:
            product_loader.add_value('image_url', urljoin_rfc(get_base_url(response), img[0]))

        item = product_loader.load_item()
        metadata = FragranceDirectMeta()
        metadata['promotion'] = normalize_space(' '.join(hxs.select('//div[@class="bubble-msg-container"]//text()').extract()))
        if item.get('price'):
            metadata['price_exc_vat'] = Decimal(product['price']) / Decimal('1.2')
        item['metadata'] = metadata

        for opt in hxs.select('//table[@id="super-product-table"]//tbody/tr[not(contains(@class,"gwp"))]'):
            p = Product(item)
            name = normalize_space(''.join(opt.select('./td[2]/text()').extract()))
            self.log("NAE %s" % name)
            if name not in p['name']:
                p['name'] = normalize_space(p['name'] + ' ' + name)

            p['identifier'] = opt.select('normalize-space(substring-after(.//div[@class="product-code"]/text(), "#"))').extract()[0]
            p['price'] = extract_price(''.join(opt.select('.//span[starts-with(@id,"product-price-")]//text()').extract()))
            if p['price']<30:
                p['shipping_cost'] = extract_price('1.95')
                p['price'] = p['price'] + p['shipping_cost']

            if p['price']:
                p['metadata']['price_exc_vat'] = Decimal(p['price']) / Decimal('1.2')
            p['stock'] = 'in stock' in ''.join(opt.select('.//span[@class="stock-status-main"]/text()').extract()) and 1 or 0
            yield p
