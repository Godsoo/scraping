import os
import re
import time

from scrapy import signals
from scrapy.xlib.pydispatch import dispatcher

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc
from scrapy.exceptions import DontCloseSpider

from scrapy import log

from utils import extract_price_eu
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

HERE = os.path.abspath(os.path.dirname(__file__))

class LeroyMerlinSpider(BaseSpider):
    name = 'newbricoman-leroymerlin.it'
    allowed_domains = ['leroymerlin.it']

    start_urls = ['http://www.leroymerlin.it']

    def __init__(self, *args, **kwargs):
        super(LeroyMerlinSpider, self).__init__(*args, **kwargs)
        dispatcher.connect(self.process_products, signals.spider_idle)

        self.collect_products = []
        self.sync_calls = False

    def process_products(self, spider):
        if spider.name == self.name:
            if self.collect_products and not self.sync_calls:
                self.sync_calls = True
                product = self.collect_products[0]
                req = Request(product['item']['url'],
                              dont_filter=True,
                              callback=self.parse_sync_shipping,
                              meta={'collect_products':self.collect_products[1:],
                                    'product': product})

                log.msg('SEND REQ')
                self._crawler.engine.crawl(req, self)
                raise DontCloseSpider

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        categories = hxs.select('//a[contains(@class, "menu-voice-item")]/@href').extract()
        for category in categories:
            cat_url = urljoin_rfc(base_url, category)
            yield Request(cat_url)

        sub_categories = hxs.select('//a[@class="category-link"]/@href').extract()
        for sub_category in sub_categories:
            sub_cat_url = urljoin_rfc(base_url, sub_category)
            yield Request(sub_cat_url)

        products = hxs.select('//div[contains(@class, "product-item")]/a[contains(@class, "link")]/@href').extract()
        # Load more products ...
        products += hxs.select('//a[@id="btn-load-more"]/../following-sibling::a[@class="hidden"]/@href').extract()
        if products:
            for product in products:
                yield Request(product, callback=self.parse_product)

            next_url = response.meta.get('next_url', None)
            cat_id = response.meta.get('cat_id', None)
            if not next_url:
                next_url = re.search('getProductsChunkResourceURL="(.*)";var', response.body)
                next_url = next_url.group(1) if next_url else None
                cat_id = re.search('data.categoryCode="(.*)";/', response.body)
                cat_id = cat_id.group(1) if cat_id else None

            if next_url:
                try:
                    yield Request(next_url + '&categoryCode=' + cat_id,
                                  dont_filter=True,
                                  meta={'cat_id':cat_id,
                                        'next_url': next_url})
                except:
                    log.msg('End of pagination')

        yield Request("http://www.leroymerlin.it/catalogo/videocitofoni/videocitofono-con-fili-bticino-316513-34443353-p", callback=self.parse_product)

    def retry(self, response, error="", retries=5):
        retry = int(response.meta.get('retry', 0))
        if retry < retries:
            retry += 1
            time.sleep(30)
            new_meta = response.request.meta.copy()
            new_meta['retry'] = retry
            new_meta['recache'] = True
            yield Request(response.request.url, dont_filter=True, callback=response.request.callback, meta=new_meta)
        else:
            if error:
                self.errors.append(error)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        # skip error page
        if hxs.select('//div[@class="portlet-msg-error"]'):
            self.log('[WARNING] Error page when loading url: %s' % response.url)
            return

        if not hxs.select('//ul[contains(@class, "breadcrumbs")]/li/span/a/text()').extract():
            # retry
            yield self.retry(response, "Error getting category from: %s" % response.url)
            return

        l = ProductLoader(item=Product(), response=response)
        l.add_xpath('name', '//div[contains(@class, "description")]/h1/text()')
        l.add_value('url', response.url)
        sku = hxs.select('//div[contains(@class, "description-panel")]/span[contains(text(), "Ref. ")]/text()').extract()
        sku = sku[0].strip().replace('Ref. ', '') if sku else ''
        l.add_value('sku', sku)
        l.add_value('identifier', sku)
        l.add_value('brand', '')
        l.add_xpath('image_url', '//img[@id="current-zoomed"]/@src')
        category = hxs.select('//ul[contains(@class, "breadcrumbs")]/li/span/a/text()').extract()[-1]
        l.add_value('category', category)
        price = hxs.select('//div[@class="price"]/span[@class="amount"]/text()').extract()
        price = price[0].replace('.', '').replace(',', '.') if price else 0
        l.add_xpath('price', price)
        item = l.load_item()

        add_button = hxs.select('//div[@class="add-section"]/a[contains(@class, "btn-green")]')
        if add_button:
            formdata = {'product': sku, 'quantity': '1'}

            product = {'item': item,
                       'formdata': formdata}
            self.collect_products.append(product)
        else:
            yield item

    def parse_sync_shipping(self, response):
        meta = response.meta
        if 'retry' not in response.meta and 'addItemsResource' in response.url:
            log.msg('Product added')
            yield Request("http://www.leroymerlin.it/checkout/carrello",
                          dont_filter=True,
                          callback=self.parse_shipping_cost,
                          meta=meta)

        if 'retry' not in response.meta and 'removeEntryResource' in response.url:
            log.msg('Product removed')
            if meta.get('collect_products', []):
                product = meta.get('collect_products')[0]
                req = FormRequest(product['item']['url'],
                                  formdata=product['formdata'],
                                  callback=self.parse_sync_shipping,
                                  dont_filter=True,
                                  meta={'collect_products':meta.get('collect_products')[1:],
                                        'product': product})
                yield req

        product = meta.get('product', None)
        if product:
            product_url = product['item']['url'] if product else ''
            if response.url == product_url:
                product = meta['product']
                try:
                    add_item_regex = re.search('addItemsResourceURL:"(.*)",remove', response.body)
                    if not add_item_regex:
                        add_item_regex = re.search('addItemsResourceURL : "(.*)"', response.body)
                    add_item = add_item_regex.group(1)
                except Exception, e:
                    retry = int(response.meta.get('retry', 0))
                    if retry < 5:
                        retry += 1
                        meta = response.meta.copy()
                        meta['retry'] = retry
                        yield Request(response.url,
                                      dont_filter=True,
                                      callback=self.parse_sync_shipping,
                                      meta=meta)
                    else:
                        raise e
                else:
                    req = FormRequest(add_item,
                                      formdata=product['formdata'],
                                      dont_filter=True,
                                      callback=self.parse_sync_shipping,
                                      meta={'collect_products':meta.get('collect_products'),
                                            'product': product})
                    yield req

    def parse_shipping_cost(self, response):
        hxs = HtmlXPathSelector(response)
        meta = response.meta
        product = meta['product']
        item = product['item']
        shipping_cost = hxs.select('//div[@class="shipment-method" and ' +
                                   'div/div/label/text()="Consegna standard"]' +
                                   '//span[@class="amount"]/text()').extract()
        item['shipping_cost'] = extract_price_eu(shipping_cost[0]) if shipping_cost else 0
        yield item
        remove_regex = ',removeEntryResourceURL:"(.*)",updateItemQuantityResourceURL:"'
        try:
            remove_item = re.search(remove_regex, response.body).group(1).split('removeEntryResourceURL:"')[-1]
        except:
            return
        cart_entry = hxs.select('//div[@data-product="' + item['identifier'] + '"]/@data-cartentry').extract()
        req = FormRequest(remove_item,
                          formdata={'cartentry': cart_entry},
                          callback=self.parse_sync_shipping,
                          dont_filter=True,
                          meta={'collect_products':meta.get('collect_products')[1:]})
        yield req

