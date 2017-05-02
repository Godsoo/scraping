from decimal import Decimal
from urlparse import urljoin
from urllib import quote as url_quote

from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from scrapy import log

from product_spiders.utils import extract_price
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.spiders.comms_express.utils import CommsBaseSpider

class InsightSpider(CommsBaseSpider):
    name = 'commsexpress-insight.com'
    allowed_domains = ['insight.com']

    #download_timeout = 60

    def start_requests(self):
        for i, search in enumerate(self.whitelist):
            self.log('Searching: %s' % search)
            yield Request('http://www.uk.insight.com/en-gb/apps/nbs/results.php?K=%s' % url_quote(search, ''),
                          callback=self.parse_product,
                          meta={
                              'handle_httpstatus_list': [404],
                              'search_term': search,
                              'sku': search,
                          })

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)

        products = hxs.select('//div[@id="search_results_products"]//h2[@class="product-name"]/a/@href').extract()
        if products:
            for product in products:
                yield Request(urljoin_rfc(get_base_url(response), product), dont_filter=True, callback=self.parse_product, meta=response.meta)
            
            #next = hxs.select('//li[@class="pagination-next navigate"]/a/@href').extract()
            #if next:
            #    yield Request(urljoin_rfc(get_base_url(response), next[0]), callback=self.parse_product, meta=response.meta)
        else:
            identifier = hxs.select('//input[@name="d[0]"]/@value').extract()
            if not identifier:
                identifier = hxs.select('//span[@itemprop="sku"]/text()').extract()

            if not identifier:
                log.msg('No search results for: ' + response.url)
                return

            loader = ProductLoader(item=Product(), selector=hxs)
            #loader.add_value('identifier', identifier)
            loader.add_xpath('identifier', '//h2/span[@itemprop="mpn"]/text()')
            loader.add_value('url', response.url)
            loader.add_xpath('name', '//h1[@itemprop="name"]/span/text()')
            loader.add_xpath('price', '//span[@class="linelistprice"]/text()')
            loader.add_xpath('sku', '//h2/span[@itemprop="mpn"]/text()')

            categories = hxs.select('//ul[@class="breadcrumbs"]/li//span/text()').extract()[2:]
            loader.add_value('category', categories)

            img = hxs.select('//div[@id="prod-pres-gallery-image"]/img/@src').extract()
            if img:
                loader.add_value('image_url', img[0])

            loader.add_xpath('brand', '//img[@id="manufacturer-logo"]/@alt')

            if not loader.get_output_value('price'):
                loader.add_value('stock', 0)

            #yield loader.load_item()
            self.yield_item(loader.load_item())
            return

    def yield_item(self, item):
        self.log('Product identifier: %s' % item['identifier'])
        match = match_sku(item.get('identifier').encode('utf'), self.whitelist, self.product_list, item.get('brand', ''))
        if match:
            item['identifier'] = match

            if item['identifier'] in self.collected:
                if item['price'] < self.collected[item['identifier']]['price']:
                    self.collected[item['identifier']] = item
            else:
                self.collected[item['identifier']] = item
        else:
            self.log('[%s] identifier not in whitelist: %s' % (item['url'], item['identifier']))

def match_sku(a, whitelist, product_list, brand):
    """
    >>> whitelist = ['TS5800D0808-EU', 'TS5800D1608-EU']
    >>> product_list = dict([(x, x) for x in whitelist])
    >>> match_sku('fets5800d0808-eu', whitelist, product_list, '')
    'FETS5800D0808-EU'
    """
    if a in whitelist:
        return a
    if a.upper() in whitelist:
        return a.upper()
    plain_a = a.replace('-', '').replace('/', '').lower()
    plain_a = plain_a[2:] if plain_a.startswith('fe') else plain_a
    for b in whitelist:
        plain_b = b.replace('-', '').replace('/', '').lower()
        plain_b = plain_b[2:] if plain_b.startswith('fe') else plain_b
        if plain_a == plain_b:
            if a.lower().startswith('fe'):
                return 'FE' + b
            else:
                return b

    for b in whitelist:
        plain_b = b.replace('-', '').replace('/', '').lower()
        plain_b = plain_b[2:] if plain_b.startswith('fe') else plain_b
        if plain_a.startswith(plain_b) or plain_b.startswith(plain_a):
            for brand_part in brand.split(' '):
                if brand_part.replace('-', '').upper() in product_list[b].replace('-', '').upper():
                    if a.lower().startswith('fe'):
                        return 'FE' + b
                    else:
                        return b

    return False

def get_whitelist(rows):
    if not rows:
        return None, None

    temp_row = rows[0]

    manuf_sku_field = None
    comms_sku_field = None
    desc_field = None

    for field in temp_row:
        if 'Manufac pt n.o'.lower() in field.lower():
            manuf_sku_field = field
        elif 'Our Pt.n.o'.lower() in field.lower():
            comms_sku_field = field
        elif 'Description'.lower() in field.lower():
            desc_field = field

    whitelist = set()
    product_list = {}
    for row in rows:
        sku1 = row[manuf_sku_field].strip()
        sku2 = row[comms_sku_field].strip()

        # Remove region code from D-Link products
        #if sku1.endswith('/B'): sku1 = sku1[:-2]
        #if sku2.endswith('/B'): sku2 = sku2[:-2]

        whitelist.add(sku1 or sku2)
        product_list[sku1 or sku2] = row[desc_field].decode('utf-8')
        sku3 = fix_sku(sku2, sku1)
        if sku3:
            whitelist.add(sku3)
            product_list[sku3] = row[desc_field].decode('utf-8')

    return whitelist, product_list

