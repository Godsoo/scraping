import time
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, XmlResponse
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url
try:
    from scrapy.utils.gz import gunzip, is_gzipped
    from scrapy.contrib.spiders import SitemapSpider
except ImportError:
    from scrapy.utils.gz import gunzip
    from scrapy.contrib.spiders.sitemap import SitemapSpider, is_gzipped

from product_spiders.utils import extract_price
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader


class ChemistDirectSpider(SitemapSpider):
    name = 'chemistdirect.co.uk'
    allowed_domains = ['chemistdirect.co.uk']
    # start_urls = ('http://www.chemistdirect.co.uk/',)
    sitemap_urls = ['http://www.chemistdirect.co.uk/sitemap.xml']
    sitemap_rules = [
        ('/', 'parse_product')
    ]
    sitemap_follow = ['sitemap-product']

    # Fix for Scrapy 1.0
    # override some base spider's method to account for double compression
    def _get_sitemap_body(self, response):
        """Return the sitemap body contained in the given response, or None if the
        response is not a sitemap.
        """
        if isinstance(response, XmlResponse):
            return response.body
        elif is_gzipped(response):
            return self._decompress(response.body)
        elif response.url.endswith('.xml'):
            return self._decompress(response.body)
        elif response.url.endswith('.xml.gz'):
            return self._decompress(response.body)

    def _decompress(self, body):
        while True:
            try:
                body = gunzip(body)
            except IOError:
                return body

    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        for cat in hxs.select('//ul[contains(@class, "mega-menu")]//a/@href').extract():
            yield Request(urljoin_rfc(get_base_url(response), cat),
                          callback=self.parse_cat,
                          meta={'dont_merge_cookies': True})

    def parse_cat(self, response):
        hxs = HtmlXPathSelector(response)

        for cat in hxs.select('//div[@class="panel-content"]//a/@href').extract():
            yield Request(urljoin_rfc(get_base_url(response), cat),
                          callback=self.parse_cat,
                          meta={'dont_merge_cookies': True})

        products = hxs.select('//li[contains(@class, "item")]')
        for productxs in products:
            product = Product()
            product['price'] = extract_price(''.join(productxs.select('.//span[@class="price"]//text()').extract()))
            if productxs.select('.//span[@class="stock success"]'):
                product['stock'] = 1
            else:
                product['stock'] = 0

            product_url = productxs.select('.//a[@class="name"]/@href').extract()[0]
            yield Request(urljoin_rfc(get_base_url(response), product_url),
                          callback=self.parse_product,
                          meta={'product': product,
                                'dont_merge_cookies': True})

        pages = hxs.select('//nav[@class="pagination"]//a/@href').extract()
        for page in pages:
            meta = response.meta.copy()
            meta['next_page_retry'] = 1
            yield Request(urljoin_rfc(get_base_url(response), page),
                          callback=self.parse_cat,
                          meta=meta)

        if not products and response.meta.get('next_page_retry'):
            retry = int(response.meta['next_page_retry'])
            if retry < 5:
                time.sleep(5)
                retry += 1
                self.log('Retrying No. %s => %s' % (str(retry), response.url))
                yield Request(response.url,
                              callback=self.parse_cat,
                              meta={'dont_merge_cookies': True,
                                    'next_page_retry': retry},
                              dont_filter=True)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        loader = ProductLoader(item=Product(), selector=hxs)
        loader.add_xpath('identifier', '//*[@itemprop="sku"]/@content')
        loader.add_value('url', response.url)
        loader.add_xpath('name', '//*[@itemprop="name"]//text()')
        loader.add_xpath('sku', '//*[@itemprop="sku"]/@content')
        loader.add_xpath('price', '//*[@itemprop="price"]/@content')

        loader.add_xpath('category', '//ul[@itemprop="breadcrumb"]/li[2]/a/text()')

        img = hxs.select('//img[@itemprop="image"]/@src').extract()
        if img:
            loader.add_value('image_url', urljoin_rfc(get_base_url(response), img[0]))

        stock = hxs.select('//*[@itemprop="availability"]/@content').extract()
        if stock and stock[0].lower().strip() == 'in stock':
            loader.add_value('stock', 1)
        else:
            loader.add_value('stock', 0)

        loader.add_xpath('brand', '//*[@itemprop="brand"]/@content')
        yield self.add_shipping_cost(loader.load_item())

    def add_shipping_cost(self, item):
        if item.get('price', 0) < 40:
            item['shipping_cost'] = 3.49
        else:
            item['shipping_cost'] = 0
        return item
