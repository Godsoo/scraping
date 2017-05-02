from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

from product_spiders.utils import extract_price
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from phantomjs import PhantomJS
import time
from math import floor


class NisbetsSpider(BaseSpider):
    name = 'buycatering-nisbets.co.uk'
    allowed_domains = ['nisbets.co.uk']
    start_urls = ('http://www.nisbets.co.uk/Homepage.action',)
    errors = []

    # NOTE: important to get the first page
    user_agent = 'User-Agent: Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Ubuntu Chromium/32.0.1700.107 Chrome/32.0.1700.107 Safari/537.36'

    _skus = None

    def parse(self, response):
        browser = PhantomJS()
        url = self.start_urls[0]
        self.log('>>> BROWSER: GET => %s' % url)
        browser.get(url)
        self.log('>>> BROWSER: OK')

        time.sleep(120)
        browser.driver.find_element_by_xpath('//p[@class="style-inc"]//input').click()
        time.sleep(30)

        page_source = browser.driver.page_source

        browser.close()
        hxs = HtmlXPathSelector(text=page_source)
        for cat in hxs.select('//ul[@class="clear-after"]/li/ul/li/a'):
            yield Request(urljoin_rfc(url, cat.select('./@href').extract()[0]), callback=self.parse_cat, meta={'category':cat.select('./text()').extract()[0]})

    def parse_cat(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        for url in hxs.select('//div[contains(@class,"category-fourgrid") or contains(@class,"sub-category-grid")]//a/@href').extract():
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_cat, meta=response.meta)

        for productxs in hxs.select('//div[contains(@class,"product-list-row") and div[contains(@class, "product-info")]]'):
            product_options_link = productxs.select('.//div[@class="form-row"]/a/@href').extract()
            if product_options_link:
                yield Request(urljoin_rfc(base_url, product_options_link[0]), callback=self.parse_cat, meta=response.meta)
            else:
                loader = ProductLoader(item=Product(), selector=productxs)
                price = ''.join(productxs.select('.//div[@class="price"]//text()').extract())
                loader.add_value('price', price)
                if productxs.select('.//img[@alt="In stock" or contains(@alt,"days delivery") or contains(@alt,"Day Delivery") or contains(@alt,"Hour Delivery")]'):
                    loader.add_value('stock', 1)
                else:
                    loader.add_value('stock', 0)
                loader.add_xpath('identifier', './/p[@class="code"]/text()')
                product_url = productxs.select('.//h3[@class="product-name"]/a/@href').extract()[0]
                loader.add_value('url', urljoin_rfc(base_url, product_url))
                loader.add_xpath('name', './/h3[@class="product-name"]/a/text()')
                loader.add_value('category', response.meta.get('category'))
                loader.add_xpath('sku', './/p[@class="code"]/text()')
                img = productxs.select('.//div[@class="primaryImageDiv"]//img/@src').extract()
                if img:
                    loader.add_value('image_url', urljoin_rfc(base_url, img[0].replace('/medium/', '/large/')))
                loader.add_xpath('brand', './/img[@class="brand-image"]/@alt')
                item = self.add_shipping_cost(loader.load_item())

                #item['metadata'] = {}
                #pack_qty = productxs.select('.//p[@class="qty-icon-small" and contains(span/text(), "Pack Quantity")]//text()').re(r'(\d+)')
                #if pack_qty:
                #    item['metadata']['Quantity'] = pack_qty[0]

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
