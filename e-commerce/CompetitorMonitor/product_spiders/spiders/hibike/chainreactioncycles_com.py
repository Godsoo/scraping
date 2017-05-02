import csv
import os
import shutil
from datetime import datetime
import StringIO
import urllib

from scrapy.spider import BaseSpider
from scrapy import signals
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc, url_query_parameter
from scrapy.xlib.pydispatch import dispatcher

from product_spiders.items import (
    Product,
    ProductLoaderWithNameStrip as ProductLoader
)

from scrapy import log

from product_spiders.utils import extract_price
HERE = os.path.abspath(os.path.dirname(__file__))

class ChainReactionCyclesComSpider(BaseSpider):
    name = 'chainreactioncycles.com_hibike'
    allowed_domains = ['chainreactioncycles.com', 'competitormonitor.com']

    start_urls = ['http://www.chainreactioncycles.com/']

    '''
    def __init__(self, *args, **kwargs):
        super(ChainReactionCyclesComSpider, self).__init__(*args, **kwargs)
        dispatcher.connect(self.spider_closed, signals.spider_closed)
    '''

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        change_loc_form = hxs.select('//div[@id="localepickerpage"]/form')
        action_url = urljoin_rfc(base_url, change_loc_form.select('./@action').extract()[0])
        input_vals = dict(zip(change_loc_form.select('.//input/@name').extract(),
                              change_loc_form.select('.//input/@value').extract()))
        params = {u'/atg/userprofiling/ProfileFormHandler.value.country': u'DE',
                  u'/atg/userprofiling/ProfileFormHandler.value.currency': u'EUR',
                  u'/atg/userprofiling/ProfileFormHandler.value.language': u'en',
                  u'Update': u'Update',
                  u'_D:Update': ''}
        input_vals.update(params)

        yield FormRequest(action_url,
                          formdata=input_vals,
                          callback=self.init_run,
                          dont_filter=True)

    def init_run(self, response):
        '''
        if self.full_run_required():
            start_req = self._full_request
            log.msg('Full run')
        else:
            start_req = self._simple_request
            log.msg('Simple run')
        '''

        start_req = self._full_request

        for r in start_req(response):
            yield r

    def spider_closed(self, spider):
        if spider.name == self.name:
            shutil.copy('data/%s_products.csv' % spider.crawl_id, os.path.join(HERE, 'chainreactioncycles_products.csv'))

    def _full_request(self, response):
        yield Request('http://www.chainreactioncycles.com/staticcontent/siteMap.jsp', callback=self.parse_full)

    def _simple_request(self, response):
        yield Request('http://competitormonitor.com/login.html?action=get_products_api&website_id=488512&matched=1',
                      callback=self.parse_simple)

    def full_run_required(self):
        if not os.path.exists(os.path.join(HERE, 'chainreactioncycles_products.csv')):
            log.err("Does not exist")
            return True

        # run full only on Mondays
        return datetime.now().weekday() == 0

    def parse_full(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        brands = [
            (name, url) \
                for \
                    (name, url) \
                in \
                    zip(hxs.select('//div[@class="brand_container"]//li[@class="even"]/a/text()').extract(),
                        hxs.select('//div[@class="brand_container"]//li[@class="even"]/a/@href').extract()) \
                if \
                    name.strip()
        ]
        for name, url in brands:
            self.log(u'BRAND => %s' % name)
            url = urljoin_rfc(base_url, url)
            yield Request(url,
                          meta={'brand': name.strip()},
                          callback=self.parse_product_list)

    def parse_product_list(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        '''
        brand_cats_urls = hxs.select('//div[@class="left_menu"]/div[@class="category_container"]//a/@href').extract()
        for url in brand_cats_urls:
            yield Request(urljoin_rfc(base_url, url),
                          meta=response.meta.copy(),
                          callback=self.parse_product_list)
        '''

        if not url_query_parameter(response.url, 'f'):
            filter_brand_url = hxs.select(u'//p[@class="arrow_head" and span[@class="leftsubcat_categories" '
                u'and contains(text(), "Brand")]]/following-sibling::ul[contains(@class, "brand_list")]'
                u'//span[@id="refine_label" and contains(text(), "%s")]/parent::a/@href' % response.meta['brand']).extract()
            if filter_brand_url:
                url = filter_brand_url[0]
                yield Request(urljoin_rfc(base_url, url),
                              meta=response.meta.copy(),
                              callback=self.parse_product_list)
                return

        all_products_link = hxs.select('//div[@class="left_nav brand_cat"]//a[p[@class="upto_cat"]]/@href').extract()
        if all_products_link:
            url = all_products_link[0]
            yield Request(urljoin_rfc(base_url, url),
                          meta=response.meta.copy(),
                          callback=self.parse_product_list)

        products = hxs.select('//div[@id="grid-view"]/div[@class="grid_view_row"]'
                              '/div[contains(@class, "products_details_container")]'
                              '/div[contains(@class, "products_details")]'
                              '//li[contains(@class, "description")]/a/@href').extract()
        for url in products:
            url = urljoin_rfc(base_url, url)
            yield Request(url,
                          meta=response.meta.copy(),
                          callback=self.parse_product)

        pages = hxs.select('//div[@class="pagination"][1]/a[not(@class="active")]/@href').extract()
        for next_page in pages:
            url = urljoin_rfc(base_url, next_page)
            yield Request(url,
                          meta=response.meta.copy(),
                          callback=self.parse_product_list)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        product_loader = ProductLoader(item=Product(), selector=hxs)
        product_loader.add_value('url', response.url)
        product_loader.add_xpath('name', '//li[@class="product_title"]/text()')
        try:
            category = hxs.select('//div[@class="breadcrumb"]//li/a/text()')[-1].re(r'[\w\- ]+')
            product_loader.add_value('category', category)
        except:
            pass
        # product_loader.add_xpath('brand', u'//a[@id="ModelsDisplayStyle4_HlkSeeAllBrandProducts"]/@title')

        img = hxs.select('//div[@id="pdpcontainer"]//img/@pagespeed_lazy_src').extract()
        if img:
            product_loader.add_value('image_url', urljoin_rfc(base_url, img.pop()))

        # product_loader.add_xpath('brand', u'//span[@itemprop="manufacturer"]/text()')
        # product_loader.add_xpath('shipping_cost', '')
        product = product_loader.load_item()
        options_values = hxs.select('//script[contains(text(), "var allVariants={")]/text()').re(r'var variantsAray=(\[.*\]);')
        if options_values:
            options_values = eval(options_values[0])
        options = hxs.select('//script[contains(text(), "var allVariants={")]/text()').re(r'allVariants={"variants":(\[.*\,])\}\;')
        if options:
            options = eval(options[0])
        if options and options_values:
            for option in options:
                prod = Product(product)
                sku = option['skuId'].replace('sku', '')
                prod['identifier'] = sku
                prod['sku'] = sku
                prod['name'] = prod['name'].strip() + ' ' + ' '.join(option[k] for k in options_values if option[k] is not 'null').decode('utf-8')
                prod['price'] = extract_price(option['RP'])
                prod['brand'] = response.meta['brand']
                yield prod

    def parse_simple(self, response):
        f = StringIO.StringIO(response.body)
        hxs = HtmlXPathSelector()
        reader = csv.DictReader(f)
        self.matched = set()
        for row in reader:
            self.matched.add(row['url'])

        for url in self.matched:
            yield Request(url, self.parse_product)

        with open(os.path.join(HERE, 'chainreactioncycles_products.csv')) as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['url'] not in self.matched:
                    loader = ProductLoader(selector=hxs, item=Product())
                    loader.add_value('url', row['url'])
                    loader.add_value('sku', row['sku'].decode('utf-8'))
                    loader.add_value('identifier', row['identifier'].decode('utf-8'))
                    loader.add_value('name', row['name'].decode('utf-8'))
                    loader.add_value('price', row['price'])
                    loader.add_value('category', row['category'].decode('utf-8'))
                    loader.add_value('brand', row['brand'].decode('utf-8'))
                    loader.add_value('image_url', row['image_url'])
                    loader.add_value('shipping_cost', row['shipping_cost'])
                    yield loader.load_item()
