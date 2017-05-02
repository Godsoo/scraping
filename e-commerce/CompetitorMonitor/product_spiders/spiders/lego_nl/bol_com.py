import re

from scrapy.http import Request
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

from product_spiders.items import (
    Product,
    ProductLoaderWithNameStrip as ProductLoader
)


class LegoBolSpider(BaseSpider):
    name = "lego_nl-bol.com"
    allowed_domains = ['bol.com']
    start_urls = ('http://www.bol.com/nl/s/algemeen/zoekresultaten/Ntt/lego/N/0/Nty/1/search/true/searchType/qck/sc/media_all/index.html',
                  'http://www.bol.com/nl/b/speelgoed/lego/4148554/index.html',
                  'http://www.bol.com/nl/l/speelgoed/bouw-constructie-lego/N/10463+1283+1285+5260+7373/index.html',)

    re_sku = re.compile('(\d\d\d\d\d?)')

    errors = []

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        products = response.css('a.product-title::attr(href)').extract()
        for url in products:
            yield Request(urljoin_rfc(base_url, url),
                          callback=self.parse_product)
        pages = response.css('ul.pagination a::attr(href)').extract()
        for url in pages:
            yield Request(urljoin_rfc(base_url, url))

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        meta = response.meta
        try:
            meta['name'] = hxs.select('//*[@id="main_block"]//h1/text()').extract()[0].strip()
            meta['image_url'] = hxs.select('//img[@itemprop="image"]/@src').extract()[0]
            meta['identifier'] = response.url.split('/')[-2]
            meta['price'] = 0
            price1 = response.xpath('//span[@itemprop="price"]/text()[2]').extract()
            if price1:
                price2 = hxs.select('//span[@itemprop="price"]/span[2]/text()').extract()
                if price2:
                    meta['price'] = price1[0] + price2[0]
            else:
                price = response.xpath('//meta[@itemprop="price"]/@content').extract()
                if price:
                    meta['price'] = price.pop()
            meta['sku'] = self.re_sku.findall(meta['name'])
            if not meta['price']:
                return
        except Exception, e:
            raise e
        meta['url'] = response.url
        sellers_url = hxs.select('//div[contains(@class, "product_compare") and '
                                 'contains(@class, "new_prices")]/div[contains(@class, "new_prices")]'
                                 '//a[contains(@class, "js_tab_link")]/@href').extract()
        if sellers_url:
            yield Request(sellers_url[0].strip(), callback=self.parse_sellers, meta=meta)
        else:
            dealer = hxs.select('//div[@class="usp_slot grid_213 fleft"]//a/text()').extract()
            dealer_id = hxs.select('//div[@class="usp_slot grid_213 fleft"]//a/@href').re(r'/nl/v/.*/(\d+)/')
            # if not dealer:
            #    self.errors.append('WARNING: using default dealer => %s' % response.url)
            dealer = dealer[0].strip() if dealer else 'Bol.com'
            dealer_id = dealer_id[0] if dealer_id else 'Bol.com'
            l = ProductLoader(item=Product(), response=response)
            l.add_value('identifier', meta['identifier'] + '-' + dealer_id)
            l.add_value('name', meta['name'])
            l.add_value('brand', 'LEGO')
            l.add_value('sku', meta['sku'])
            l.add_value('url', meta['url'])
            l.add_value('shipping_cost', 0)
            l.add_value('price', self._encode_price(str(meta['price'])))
            l.add_value('image_url', meta['image_url'])
            l.add_value('dealer', dealer)
            yield l.load_item()

    def parse_sellers(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        meta = response.meta
        pages = response.css('.pagination a::attr(href)').extract()
        for url in pages:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_sellers, meta=meta)
        sellers = response.xpath('//*[@id="offers"]/li')
        for seller in sellers:
            price = seller.css('.product-prices span::text').extract()
            if not price:
                price = seller.select('./td[contains(@class, "product_specs")]/p[1]/text()').extract()
                if not price:
                    continue
            price = price[0]
            seller_name = seller.css('.nosp strong::text').extract_first()
            seller_id = seller.css('.link-cta ::attr(href)').re(r'/nl/v/.*/(\d+)/')
            seller_name = seller_name if seller_name else 'Bol.com'
            seller_id = seller_id[0] if seller_id else 'Bol.com'
            shipping_cost = seller.css('.product-additional-fee ::text').extract_first()
            l = ProductLoader(item=Product(), response=response)
            l.add_value('identifier', meta['identifier'] + '-' + seller_id)
            l.add_value('name', meta['name'])
            l.add_value('brand', 'LEGO')
            l.add_value('sku', meta['sku'])
            l.add_value('url', meta['url'])
            l.add_value('shipping_cost', self._encode_price(shipping_cost))
            l.add_value('price', self._encode_price(price))
            l.add_value('image_url', meta['image_url'])
            l.add_value('dealer', seller_name)
            yield l.load_item()

    def _encode_price(self, price):
        return price.replace(',', '.').encode("ascii", "ignore")
