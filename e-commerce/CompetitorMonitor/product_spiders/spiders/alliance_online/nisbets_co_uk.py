from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

from product_spiders.utils import extract_price
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

from product_spiders.base_spiders import PrimarySpider
import time
from math import floor


class NisbetsSpider(PrimarySpider):
    name = 'allianceonline-nisbets.co.uk'
    allowed_domains = ['nisbets.co.uk']
    start_urls = ('http://www.nisbets.co.uk/SearchError.action',)
    errors = []
    csv_file = 'nisbets_crawl.csv'

    # NOTE: important to get the first page
    user_agent = 'User-Agent: Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Ubuntu Chromium/32.0.1700.107 Chrome/32.0.1700.107 Safari/537.36'

    _skus = None

    def parse(self, response):
        yield FormRequest('http://www.nisbets.co.uk/SearchError.action', formdata={'VAT_SWITCH_MARKER': 'true'}, callback=self.parse_categories)

    def parse_categories(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        for cat in hxs.select('//ul[@class="clear-after"]/li/ul/li/a[text()]'):
            cat_url = urljoin_rfc(base_url, cat.select('./@href').extract()[0])
            category = cat.select('./text()').extract()[0].strip()
            yield Request(cat_url, callback=self.parse_cat, meta={'category':category})

    def parse_cat(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        if 'Please enable JavaScript to view the page content' in response.body:
            self.log('No JavaScript on %s' %response.url)
            yield response.request.replace(dont_filter=True)
            return

        for url in hxs.select('//div[contains(@class,"category-fourgrid") or contains(@class,"sub-category-grid")]//a/@href').extract():
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_cat, meta=response.meta)

        for productxs in hxs.select('//div[contains(@class,"product-list-row") and div[contains(@class, "product-list-info")]]'):
            product_options_link = productxs.select('.//div[@class="product-list-button"]/a/@href').extract()
            if product_options_link:
                yield Request(urljoin_rfc(base_url, product_options_link[0]), callback=self.parse_cat, meta=response.meta)
            else:
                loader = ProductLoader(item=Product(), selector=productxs)
                price = float(extract_price(''.join(productxs.select('.//div[@class="product-list-price"]//span[last()]/text()').extract())))
                loader.add_value('price', price)
                if productxs.select('.//img[@alt="In stock" or contains(@alt,"days delivery") or contains(@alt, "Day Delivery") or contains(@alt,"Hour Delivery")]'):
                    loader.add_value('stock', 1)
                else:
                    loader.add_value('stock', 0)
                code = ''.join(productxs.select('.//p[@class="code"]/text()').extract()).strip()
                loader.add_value('identifier', code)
                product_url = productxs.select('.//div[@class="product-list-title"]/h3/a/@href').extract()[0]
                loader.add_value('url', urljoin_rfc(base_url, product_url))
                loader.add_xpath('name', './/div[@class="product-list-title"]/h3/a/text()')
                loader.add_value('category', response.meta.get('category'))
                loader.add_value('sku', code)
                img = productxs.select('.//img[@class="primaryImage"]/@src').extract()
                if img:
                    loader.add_value('image_url', urljoin_rfc(base_url, img[0].replace('/medium/', '/large/')))
                loader.add_xpath('brand', './/img[@class="brand-image"]/@alt')
                item = self.add_shipping_cost(loader.load_item())

                item['metadata'] = {}
                item['metadata']['product_code'] = code
                pack_qty = productxs.select('.//p[@class="description"]/text()').re(r'Pack .uantity:\s*(\d+)')
                if pack_qty:
                    item['metadata']['Quantity'] = pack_qty[0]

                if item.get('identifier', '').strip():
                    yield item

        for url in hxs.select('//ul[@class="pager"]//a/@href').extract():
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_cat, meta=response.meta)

    def add_shipping_cost(self, item):
        if item.get('price', 0) < 50:
            # item['shipping_cost'] = 5
            item['shipping_cost'] = 0
        else:
            item['shipping_cost'] = 0
        return item
