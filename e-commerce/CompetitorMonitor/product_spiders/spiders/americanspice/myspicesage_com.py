from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from product_spiders.utils import extract_price
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

class MyspicesageComSpider(BaseSpider):
    name = 'myspicesage.com'
    allowed_domains = ['myspicesage.com']

    def __init__(self, *args, **kwargs):
        super(MyspicesageComSpider, self).__init__(*args, **kwargs)
 
    def start_requests(self):
        yield Request('http://www.myspicesage.com/', callback=self.parse_full)

    def parse_full(self, response):
        hxs = HtmlXPathSelector(response)

        for cat in hxs.select(u'//div[@id="navCatTabs"]//a'):
            url = urljoin_rfc(get_base_url(response), cat.select('./@href').extract()[0])
            if 'name-az' in url: continue
            yield Request(url, callback=self.parse_product_list,
                    meta={'category':cat.select(u'normalize-space(./text())').extract()[0]})

    def parse_product_list(self, response):
        hxs = HtmlXPathSelector(response)

        for url in hxs.select(u'//div[@id="categories"]//a/@href').extract():
            url = urljoin_rfc(get_base_url(response), url)
            yield Request(url, callback=self.parse_product_list, meta=response.meta)

        for url in hxs.select(u'//div[@id="productsListingListingTopLinks"]//a/@href').extract():
            url = urljoin_rfc(get_base_url(response), url)
            yield Request(url, callback=self.parse_product_list, meta=response.meta)

        for url in hxs.select(u'//div[@class="productListing-info"]//a/@href').extract():
            url = urljoin_rfc(get_base_url(response), url)
            yield Request(url, callback=self.parse_product, meta=response.meta)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        product_loader = ProductLoader(item=Product(), selector=hxs)
        product_loader.add_value('url', response.url)
        product_loader.add_xpath('name', u'//td/span[contains(@class, "ex-large")]/text()')
        product_loader.add_xpath('category', u'//div[@id="navBreadCrumb"]/a[2]/text()')

        img = hxs.select(u'//div[@id="productMainImage"]/noscript/a/@href').extract()[0]
        product_loader.add_value('image_url', urljoin_rfc(get_base_url(response), img))

        sku = hxs.select(u'//td/span[contains(@class, "bold") and contains(text(), "SKU")]/text()').extract()[0]
        sku = sku.split('#')[1].split(')')[0]
        product_loader.add_value('sku', sku)


        product_id = hxs.select(u'//input[@name="product_id"]/@value').extract()
        if not product_id:
            product_id = hxs.select(u'//input[@name="pid"]/@value').extract()
            if not product_id:
                product_id = response.url.split('p-')[-1].split('.html')[0]

        product = product_loader.load_item()
        for opt in hxs.select(u'//div[@id="productMainImage"]/../..//select[@id="attrib-1"]/option[@value != ""]'):
            prod = Product(product)
            value = opt.select(u'./@value').extract()[0]
            text = opt.select(u'./text()').extract()[0]

            prod['identifier'] = product_id[0] + ':' + value
   
            prod['name'] = prod['name'] + ' ' + text.split('$')[0].strip()
            prod['price'] = extract_price(text.split('$')[-1])
            yield prod
