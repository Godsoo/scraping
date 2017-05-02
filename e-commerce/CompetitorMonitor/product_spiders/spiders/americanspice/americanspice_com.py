import urllib
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

class AmericanspiceComSpider(BaseSpider):
    name = 'americanspice.com'
    allowed_domains = ['americanspice.com']

    def __init__(self, *args, **kwargs):
        super(AmericanspiceComSpider, self).__init__(*args, **kwargs)
 
    def start_requests(self):
        yield Request('http://www.americanspice.com/spices-dry-goods/', callback=self.parse_full)
        yield Request('http://www.americanspice.com/sauces-oils/', callback=self.parse_full)
        yield Request('http://www.americanspice.com/mixes/', callback=self.parse_full)
        yield Request('http://www.americanspice.com/condiments/', callback=self.parse_full)

    def parse_full(self, response):
        hxs = HtmlXPathSelector(response)

        for url in hxs.select(u'//ul[contains(@class, "ui-accordion-content-active")]//a/@href').extract():
            url = urljoin_rfc(get_base_url(response), url)
            yield Request(url, callback=self.parse_full, meta=response.meta)

        for url in hxs.select(u'//div[@class="CategoryPagination"]//a/@href').extract():
            url = urljoin_rfc(get_base_url(response), url)
            yield Request(url, callback=self.parse_full, meta=response.meta)

        for url in hxs.select(u'//div[@class="ProductDetails"]//a/@href').extract():
            url = urljoin_rfc(get_base_url(response), url)
            if 'cart.php' in url: continue
            yield Request(url, callback=self.parse_product, meta=response.meta)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)

        product_loader = ProductLoader(item=Product(), selector=hxs)
        product_loader.add_value('url', response.url)
        product_loader.add_xpath('name', u'//h1/text()')
        product_loader.add_xpath('category', u'//div[@id="ProductBreadcrumb"]/ul/li[2]/a/text()')
        if hxs.select(u'//em[@itemprop="price" and contains(text(),"-")]/text()'):
            product_loader.add_value('price', '')
        else:
            product_loader.add_xpath('price', u'//em[@itemprop="price"]/text()')
        product_loader.add_xpath('sku', u'//div[contains(@class,"ProductSKU")]/div[@class="Value"]//text()')
        product_loader.add_xpath('identifier', u'//input[@type="hidden"][@name="product_id"]/@value')

        img = hxs.select(u'//div[@class="ProductThumbImage"]/a/@href').extract()
        if img:
            product_loader.add_value('image_url', urljoin_rfc(get_base_url(response), img[0]))


        product_loader.add_xpath('brand', u'//div[contains(text(),"Brand")]/../div[@class="Value"]/a/text()')
#product_loader.add_xpath('shipping_cost', '')

        options = hxs.select(u'//div[@class="productAttributeValue"]//ul/li/label/input/../../..')

        product_id = hxs.select(u'//input[@name="product_id"]/@value').extract()[0]
        product_orig = product_loader.load_item()

        if options:
            for opt in options:
                # Product without mandatory options
                names = opt.select(u'.//input/../span/text()').extract()
                values = opt.select(u'.//input/@value').extract()
                value_names = opt.select(u'.//input/@name').extract()
                for i in xrange(len(names)):
                    product = Product(product_orig)
                    product['name'] = (product['name'] + ' ' + names[i].strip()).strip()
                    product['identifier'] += "_" + values[i]
                    yield Request('http://www.americanspice.com/remote.php' +
                            '?w=getProductAttributeDetails&product_id=' + product_id +
                            '&' + urllib.quote(value_names[i]) + '=' + values[i],
                            meta={'product': product}, callback=self.parse_price)
        else:
            yield product_orig

    def parse_price(self, response):
        product = response.meta['product']

        data = eval(response.body, {'true':True, 'false':False})
        product['price'] = data['details']['price'].replace(',', '').replace('$', '')
        product['sku'] = data['details']['sku']
        product['image_url'] = data['details']['baseImage'].replace('\\/', '/')

        yield product
