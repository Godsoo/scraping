import os
import pandas as pd

from scrapy.spider import BaseSpider

from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc, canonicalize_url, add_or_replace_parameter
from product_spiders.items import Product
from tigerchefloader import TigerChefLoader as ProductLoader

from scrapy import log

from tigerchefitems import TigerChefMeta

from scrapy import signals
from scrapy.xlib.pydispatch import dispatcher

from product_spiders.config import DATA_DIR


class LionsDealSpider(BaseSpider):
    name = 'lionsdeal.com'
    allowed_domains = ['lionsdeal.com']
    start_urls = ('http://www.lionsdeal.com',)

    def __init__(self, *args, **kwargs):
        super(LionsDealSpider, self).__init__(*args, **kwargs)

        dispatcher.connect(self.spider_idle, signals.spider_idle)

        self.new_ids = []

        self.try_deletions = True

    def _get_prev_crawl_filename(self):
        filename = None
        if hasattr(self, 'prev_crawl_id'):
            filename = os.path.join(DATA_DIR, '%s_products.csv' % self.prev_crawl_id)
        return filename

    def spider_idle(self, spider):
        if self.try_deletions:
            self.try_deletions = False

            filename = self._get_prev_crawl_filename()
            if filename and os.path.exists(filename):
                old_products = pd.read_csv(filename, dtype=pd.np.str)
                deletions = old_products[old_products['identifier'].isin(self.new_ids) == False]
                for url in deletions['url']:
                    request = Request(url, dont_filter=True, callback=self.parse_product)
                    self._crawler.engine.crawl(request, self)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        cats = filter(lambda u: u not in ['#', '/sale.php', '/shop-by-business.html'],
                      hxs.select('//*[@id="nav"]//a/@href').extract())

        for url in cats:
            yield Request(urljoin_rfc(base_url, url))

        sub_cats = hxs.select('//ul[@class="products-categories"]//a/@href').extract()
        for url in sub_cats:
            yield Request(urljoin_rfc(base_url, url))

        pagination = hxs.select('//div[@class="pagination"]')
        if pagination:
            yield Request(add_or_replace_parameter(response.url, 'setPerPage', '1000'))

        products = hxs.select('//div[contains(@id, "product_")]//strong[@class="category-title"]/a/@href').extract()
        for url in products:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        loader = ProductLoader(item=Product(), response=response)
        loader.add_xpath('name', '//div[@class="product-info-box"]//*[@itemprop="name"]/text()')
        price = ''.join(hxs.select('//div[@class="product-info-box"]//*[@itemprop="price"]//text()').extract()).strip()
        if not price:
            price = ''.join(hxs.select('//div[@class="product-info-box"]//*[@itemprop="lowPrice"]//text()').extract()).strip()
        loader.add_value('price', price)
        identifier = response.url.split('/')[-1].split('.html')[0]
        loader.add_value('identifier', identifier)
        loader.add_xpath('sku', '//div[@class="product-info-box"]//*[@itemprop="name"]/following-sibling::small/text()',
                         lambda sku: sku[0].replace(' ', '') if sku else '', re=r'Product Code: (.*)')
        loader.add_xpath('brand', '//div[@class="product-details-section"]//*[@itemprop="brand"]//*[@itemprop="name"]/text()')
        loader.add_xpath('image_url', '//div[@id="product-left-holder"]//img[@itemprop="image"]/@src')

        bcumbs = hxs.select('//div[contains(@class, "breadcrumbs")]//a/text()').extract()
        if bcumbs:
            loader.add_value('category', bcumbs[-1])

        loader.add_value('url', response.url)

        product = loader.load_item()
        metadata = TigerChefMeta()
        sold_as = hxs.select('//div[@class="product-info-box"]//span[@id="priced_per"]/text()').extract()
        metadata['sold_as'] = sold_as[0] if sold_as else '1 ea'
        product['metadata'] = metadata

        if product['identifier']:
            self.new_ids.append(product['identifier'])
            yield product
