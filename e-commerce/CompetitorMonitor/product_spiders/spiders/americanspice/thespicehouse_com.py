from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from product_spiders.utils import extract_price
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

class ThespicehouseComSpider(BaseSpider):
    name = 'thespicehouse.com'
    allowed_domains = ['thespicehouse.com']

    def __init__(self, *args, **kwargs):
        super(ThespicehouseComSpider, self).__init__(*args, **kwargs)
 
    def start_requests(self):
        yield Request('http://www.thespicehouse.com/spices/', callback=self.parse_full)

    def parse_full(self, response):
        hxs = HtmlXPathSelector(response)

        for li in hxs.select(u'//div[@id="tabs-2"]//li'):
            url = urljoin_rfc(get_base_url(response), li.select(u'./a/@href').extract()[0])
            yield Request(url, callback=self.parse_product_list,
                    meta={'category':li.select(u'normalize-space(./a/text())').extract()[0]})

    def parse_product_list(self, response):
        hxs = HtmlXPathSelector(response)

        for url in hxs.select(u'//div[@id="list_by_category"]//a/@href').extract():
            url = urljoin_rfc(get_base_url(response), url)
            yield Request(url, callback=self.parse_product_list, meta=response.meta)

        if not hxs.select(u'//div[@id="product_page"]'):
            return

        product_loader = ProductLoader(item=Product(), selector=hxs)
        product_loader.add_value('url', response.url)
        product_loader.add_xpath('name', u'//h2[@id="longname"]/text()')
        if not product_loader.get_output_value('name'):
            product_loader.add_xpath('name', u'//h1/text()')
        product_loader.add_value('category', response.meta.get('category', 'spices'))

        img = hxs.select(u'//div[contains(@class,"image") and contains(@class,"db_content")]/img/@src').extract()
        if not img:
            img = hxs.select(u'//div[contains(@class,"image") and contains(@class,"db_content")]/a/@href').extract()
        if img:
            product_loader.add_value('image_url', urljoin_rfc(get_base_url(response), img[0]))


#product_loader.add_xpath('brand', '')
#product_loader.add_xpath('shipping_cost', '')

        product = product_loader.load_item()
        for opt in hxs.select(u'//div[@id="product_container"]//form'):
            prod = Product(product)

            prod['sku'] = opt.select(u'.//input[starts-with(@name,"m")]/@name').extract()[0]
            prod['identifier'] = opt.select(u'.//input[starts-with(@name,"m") and @type="text"]/@name').extract()[0]
            prod['name'] = prod['name'] + ' ' + opt.select(u'.//li[@class="product"]/text()').extract()[0].strip()
            prod['price'] = extract_price(opt.select(u'.//li[@class="price"]/text()').extract()[0])
            yield prod
