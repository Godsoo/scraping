from decimal import Decimal
from urlparse import urljoin
from urllib import quote as url_quote

from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url

from product_spiders.utils import extract_price
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.spiders.comms_express.utils import CommsBaseSpider

class EbuyerSpider(CommsBaseSpider):
    name = 'ebuyer.com'
    allowed_domains = ['ebuyer.com']

    download_timeout = 60

    def start_requests(self):
        for i, search in enumerate(self.whitelist):
            self.log('Searching: %s' % search)
            yield Request('http://www.ebuyer.com/search?q=%s' % url_quote(search, ''),
                          callback=self.parse_product,
                          meta={
                              'handle_httpstatus_list': [404],
                              'search_term': search,
                              'sku': search,
                          })

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)

        warning = ''.join(hxs.select('//div[@id="no-results"]/h2/text()').extract())
        if not warning:
            warning = ''.join(hxs.select('//div[@class="no-search-results"]/h2/text()').extract())
        if warning:
            search = response.meta.get('search_term', '').split('-')[0]
            if search:
            #if response.meta.get('no_res_tries', 0) < 3:
                url = 'http://www.ebuyer.com/search?q=%s' % url_quote(search, '')
                self.log("Try: %s. Retrying page: %s" % (response.meta.get('tries', 0) + 1, response.url))
                #search = response.meta.get('search_term', '').split('-')[0]
                yield Request('http://www.ebuyer.com/search?q=%s' % url_quote(search, ''),
                              callback=self.parse_product,
                              dont_filter=True,
                              meta={
                                  'handle_httpstatus_list': [404],
                                  'sku': response.meta.get('sku', '')
                                  #'no_res_tries': response.meta.get('no_res_tries', 0) + 1
                              })
                return
            else:
                self.log('Gave up trying: %s' % response.url)
                self.log(warning)
                return

        many = hxs.select('//div[contains(@class,"product-listing")]//h3/a/@href').extract()
        if not many:
            many = hxs.select('//div[contains(@class,"listing-product")]//h3/a/@href').extract()
        if many:
            for url in many:
                yield Request(urljoin(get_base_url(response), url), callback=self.parse_product)
            return

        price = hxs.select('//span[@class="now"]/span[@itemprop="price"]/text()').extract()
        if not price:
            price = hxs.select('//div[@class="product-price"]//span[@itemprop="price"]/text()').extract()
        if not price:
            if response.meta.get('tries', 0) < 3:
                self.log("Try: %s. Retrying page: %s" % (response.meta.get('tries', 0) + 1, response.url))
                yield Request(response.url,
                              callback=self.parse_product,
                              dont_filter=True,
                              meta={
                                  'handle_httpstatus_list': [404],
                                  'tries': response.meta.get('tries', 0) + 1
                              })
                return
            else:
                self.log('Gave up trying: %s' % response.url)
                self.log('No price found on page: %s' % response.url)
                return
        else:
            price = price[0]

        loader = ProductLoader(item=Product(), selector=hxs)
        loader.add_xpath('identifier', 'substring(//h2[@id="manu"]/@content, 5)')
        loader.add_xpath('identifier', '//strong[@itemprop="mpn"]/text()')
        loader.add_value('url', response.url)
        loader.add_xpath('name', '//h1/text()')
        loader.add_value('price', (extract_price(price)/Decimal(1.2)).quantize(Decimal('1.00')))
        loader.add_xpath('sku', 'substring(//h2[@id="manu"]/@content, 5)')
        loader.add_xpath('sku', '//strong[@itemprop="mpn"]/text()')
        loader.add_xpath('category', '//div[contains(@class, "breadcrumb")]//a/span/text()')

        img = hxs.select('//img[@itemprop="image"]/@src').extract()
        if img:
            loader.add_value('image_url', urljoin(get_base_url(response), img[0]))

        loader.add_xpath('brand', '//div[@itemprop="brand"]/meta[@itemprop="name"]/@content')
        if loader.get_output_value('price') < 50:
            loader.add_value('shipping_cost', '2.99')
        else:
            loader.add_value('shipping_cost', 0)

        loader.add_xpath('stock', '//span[@itemprop="quantity"]/text()')

        self.yield_item(loader.load_item())
        return
