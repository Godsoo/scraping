import logging
import json

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest

from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from product_spiders.items import Product, ProductLoader


from utils import get_product_list
from product_spiders.utils import url_quote


class TescoComSagemcomSpider(BaseSpider):
    name = 'tesco.com_sagemcom'
    allowed_domains = ['tesco.com']
    start_urls = (
        'http://www.tesco.com/direct/',
    )

    def start_requests(self):
        params = {
            'catId': '4294960229',
            'lazyload': 'true',
            'offset': '0',
            'searchquery': '',
            'sortBy': '6',
            'view': 'grid',
        }
        get_params = "&".join(map(lambda x: "=".join(x), params.items()))
        ajax_url = 'http://www.tesco.com/direct/blocks/catalog/productlisting/infiniteBrowse.jsp?' + get_params
        for row in get_product_list('Tesco'):
            if row['url']:
                yield Request(row['url'], callback=self.parse_product, meta=row)
            else:
                params['searchquery'] = url_quote(row['search'].pop(0))
                meta = row.copy()
                meta['offset'] = 0
                yield FormRequest(ajax_url, formdata=params, meta=meta, callback=self.parse_search)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)

        url = response.url

        l = ProductLoader(item=Product(), response=response)
        identifier = url.lower().split('skuid=')[-1] if len(url.lower().split('skuid=')) > 0 else None
        l.add_value('identifier', identifier)
        l.add_xpath('name', '//h1[@class="page-title"]/text()')
        l.add_xpath('image_url', '//img[@itemprop="image"]/@src')
        l.add_value('url', url)
        l.add_xpath('price', '//*[@itemprop="price"]/text()')
        l.add_value('sku', response.meta['sku'])
        l.add_value('brand', response.meta['brand'])
        l.add_value('category', response.meta['category'])
        if hxs.select('//span[contains(@class,"in-stock")]'):
            l.add_value('stock', '1')
        else:
            l.add_value('stock', '0')
        l.add_value('shipping_cost', '3.00')
        item = l.load_item()
        if item['brand'].lower() in item['name'].lower():
            yield item

    def parse_search(self, response):
        data = json.loads(response.body)

        if not data['products']:
            return

        hxs = HtmlXPathSelector(text=data['products'])
        base_url = get_base_url(response)

        # parse products
        items = hxs.select("//div[contains(@class, 'product')]")
        for item in items:
            name = item.select("div[contains(@class, 'title-author-format')]/h3/a/text()").extract()
            if not name:
                continue

            url = item.select("div[contains(@class, 'title-author-format')]/h3/a/@href").extract()
            if not url:
                logging.error("ERROR! NO URL! URL: %s. NAME: %s" % (response.url, name))
                continue
            url = url[0]
            url = urljoin_rfc(base_url, url)

            yield Request(url, callback=self.parse_product, meta=response.meta)

        offset = response.meta['offset'] + 20

        params = {
            'catId': '4294967294',
            'lazyload': 'true',
            'offset': str(offset),
            'searchquery': 'Lego',
            'sortBy': '6',
            'view': 'grid',
        }
        get_params = "&".join(map(lambda x: "=".join(x), params.items()))
        ajax_url = 'http://www.tesco.com/direct/blocks/catalog/productlisting/infiniteBrowse.jsp?' + get_params

        meta = response.meta.copy()
        meta['offset'] = offset
        yield FormRequest(ajax_url, formdata=params, meta=meta, callback=self.parse_search, dont_filter=True)
