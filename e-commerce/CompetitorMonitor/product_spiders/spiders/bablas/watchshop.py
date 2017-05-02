import re

from scrapy.contrib.spiders import SitemapSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from urlparse import urljoin as urljoin_rfc

from product_spiders.items import Product
from bablas_item import ProductLoader


class WatchShopSpider(SitemapSpider):
    name = 'watchshop.com'
    allowed_domains = ['watchshop.com']
    # start_urls = ('http://www.watchshop.com/All-Watches.html&prodsorting=pricelow',)

    sitemap_urls = ['http://www.watchshop.com/sitemap.xml']
    sitemap_rules = [
        ('/', 'parse_product'),
    ]
    errors = []

    def start_requests(self):
        yield Request('http://www.watchshop.com/change_currency_post.php?country=GB', callback=self.parse_sitemap)

    def parse_sitemap(self, response):
        for req in list(super(WatchShopSpider, self).start_requests()):
            yield req

    def retry(self, response, error="", retries=3):
        meta = response.meta.copy()
        retry = int(meta.get('retry', 0))
        if 'redirect_urls' in meta and meta['redirect_urls']:
            url = meta['redirect_urls']
        else:
            url = response.request.url
        if retry < retries:
            retry = retry + 1
            meta['retry'] = retry
            meta['recache'] = True
            return Request(url, dont_filter=True, meta=meta, callback=response.request.callback)
        else:
            self.errors.append(error)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        jewellery_urls = hxs.select(u'//div[@id="jewellery"]//a/@href').extract()
        for url in jewellery_urls:
            url = urljoin_rfc(base_url, url)
            yield Request(url)

        product_urls = hxs.select(u'//div[@class="productbox3"]/a/@href').extract()
        for url in product_urls:
            url = urljoin_rfc(base_url, url)
            yield Request(url, callback=self.parse_product)

        next_page = hxs.select(u'//div[@id="pagination"]/a[contains(text(),"Next Page")]/@href').extract()
        if next_page:
            url = urljoin_rfc(base_url, next_page[0])
            yield Request(url)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)

        try:
            identifier = re.search(u'-(p[\d]+)\.html', response.url).group(1)
        except:
            return

        loader = ProductLoader(item=Product(), response=response)

        sku = hxs.select(u'//span[@itemprop="productID"]/text()').extract()
        if not sku:
            try:
                sku = hxs.select(u'//div[@class="sku"]/span[@class="sku"]/text()')[0].re('Product Code: (.*)')
            except:
                sku = hxs.select('//div[@class="featuresleft" and contains(text(), "MPN")]/following-sibling::div[@class="featuresright"][1]/text()').extract()
        if not sku:
            sku = hxs.select('//div[@class="product-page-code"]/text()').extract()
        sku = sku[0].strip() if sku else ''

        category = hxs.select(u'//div[@id="breadcrumb"]//a/text()').extract()
        category = category[-1].strip() if category else ''
        loader.add_value('identifier', identifier)
        name = hxs.select(u'//h1[@class="product-title"]/text()').extract()
        if not name:
            request = self.retry(response, "name not found on " + response.url)
            if request:
                yield request
            return
        loader.add_value('name', u'%s (%s)' % (name[0].strip(), sku))
        match = re.search("'brand': '(.*?)',", response.body, re.IGNORECASE | re.DOTALL)
        if match:
            brand = match.group(1)
        else:
            brand = ''
        loader.add_value('brand', brand)
        loader.add_value('category', category)
        loader.add_value('sku', sku)
        loader.add_value('identifier', identifier)
        loader.add_value('url', response.url)
        price = hxs.select(u'//span[@itemprop="price"]/text()').extract()
        price = [x for x in price if re.match('.*\d.*', x)]
        price = price[0].replace(',', '') if price else ''
        loader.add_value('price', price)
        image = hxs.select(u'//img[@itemprop="image"]/@src').extract()
        image = image[0] if image else ''
        loader.add_value('image_url', urljoin_rfc(get_base_url(response), image))
        stock = hxs.select('//div[@class="product-stock-amount"]/text()').re('\d+')
        stock = int(stock[0]) if stock else 0
        loader.add_value('stock', stock)
        yield loader.load_item()
