from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc
from scrapy import log
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

from product_spiders.utils import extract_price_eu, extract_price

from product_spiders.spiders.pedalpedal.crcitem import CRCMeta

from product_spiders.base_spiders.bigsitemethodspider import BigSiteMethodSpider
from urllib import urlencode
import demjson
import re
import HTMLParser


class BikeDiscountDeSpider(BigSiteMethodSpider):
    name = 'crc-de-bike-discount.de'
    allowed_domains = ['bike-discount.de']
    website_id = 766

    # Set the country
    start_urls = ['http://www.bike-discount.de/en']

    new_system = True
    old_system = False

    full_crawl_day = 4

    identifiers = []

    def _get_matches_new_system_request(self):
        return Request('http://www.bike-discount.de/index.php?lang=en&delivery_country=48&currency=1', callback=self.__start_simple_run)

    def __start_simple_run(self, response):
        yield super(BikeDiscountDeSpider, self)._get_matches_new_system_request()

    def parse_full(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        meta = response.meta
        if not meta.get('set_currency', False):
            meta['set_currency'] = True
            yield Request('http://www.bike-discount.de/en?currency=1&delivery_country=48', callback=self.parse_full, meta=meta)
        else:
            for url in response.xpath('//ul[@class="uk-navbar-nav"]//a/@href').extract():
                url = urljoin_rfc(base_url, url)
                yield Request(url, callback=self.parse_product_list)

            yield Request('http://www.bike-discount.de/sitemap_www_bike-discount_de_en.xml',
                          callback=self.parse_sitemap)

    def parse_sitemap(self, response):
        urls = re.findall(r'(http://([\w\.-]+/?)+)', response.body)

        for url in urls:
            yield Request(url[0].replace('bike-discount.de/de/', 'bike-discount.de/en/'), callback=self.parse_product)

    def parse_product_list(self, response):
        try:
            hxs = HtmlXPathSelector(response)
            base_url = get_base_url(response)
        except:
            try:
                data = demjson.decode(response.body)
                hxs = HtmlXPathSelector(text=data['data'])
            except:
                log.msg("No valid json found: " + response.url)
                return

        products = hxs.select(u'//a[@itemprop="url"]/@href').extract()

        for url in products:
            try:
                url = urljoin_rfc(get_base_url(response), url)
            except:
                url = urljoin_rfc('http://www.bike-discount.de', url)
            yield Request(url.split('/wg_id')[0], callback=self.parse_product)

        if products:
            pages = response.xpath('//ul[contains(@class, "uk-pagination")]//a/@href').extract()
            for page in pages:
                yield Request(response.urljoin(page), callback=self.parse_product_list)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        try:
            brand_name = response.xpath('//span[@class="manufacturer"]/text()').extract()[0]
            name = response.xpath('//div[@id="product-box"]//div[@class="title"]/text()').extract()[0].strip()
        except:
            log.msg("No brand or name found: " + response.url)
            return

        if hxs.select('//div[@class="no-valid-variants" and contains(text(), "this item is currently not available")]'):
            return

        product_loader = ProductLoader(item=Product(), selector=hxs)
        product_loader.add_xpath('url', '//link[@rel="canonical"]/@href')
        product_loader.add_xpath('url', '//link[@hreflang="en"]/@href')
        product_loader.add_value('name', brand_name + ' ' + name)
        sku = hxs.select('////div[@class="additional-product-no"]/@data-xencoded').extract()
        if sku:
            sku = sku[0]
            h = HTMLParser.HTMLParser()
            key, data = sku.split(':', 1)
            key = int(key)
            data = h.unescape(data)
            # XOR decoding
            data = [ord(c) ^ key for c in data]
            data = ''.join([chr(c) for c in data])
            sku = re.search('Manufacturer Item no\. (.*)', data)
            if sku:
                sku = sku.group(1)
                # 'Hersteller Artikelnr: 20050/20051'
                product_loader.add_value('sku', sku)
        # product_loader.add_xpath('sku', u'//div[@class="additional-product-no" and contains(text(), "Manufacturer Item no.")]', re=r'Manufacturer Item no\. (.*)')
        identifier = response.xpath('//input[@name="vw_id"]/@value').extract()[0]
        product_loader.add_value('identifier', identifier)


        price = response.xpath('//div[@class="current-price"]/span[@class="price"]/text()').extract()
        if not price:
            price = hxs.select('//table[@class="product-price"]//tr[@class="price"]/td/text()').extract()
        if price:
            price = price[0]
            product_loader.add_value('price', extract_price_eu(price))
        else:
            log.msg("No product price found: " + response.url)
            return

        category = response.css('.uk-breadcrumb a::text').extract()
        if category:
            product_loader.add_value('category', category.pop())

        product_loader.add_value('brand', brand_name.strip())

        try:
            image_url = response.urljoin(response.xpath('//img[@itemprop="image"]/@src').extract()[0])
            product_loader.add_value('image_url', image_url)
        except:
            pass
        product = product_loader.load_item()

        rrp = extract_price_eu(''.join(response.xpath('//span[@class="retail-value"]/text()').extract()))
        rrp = str(rrp) if rrp>extract_price_eu(price) else ''

        metadata = CRCMeta()
        metadata['rrp'] = rrp
        product['metadata'] = metadata

        options = response.xpath('//div[contains(@id,"artikel_element_prices")]')
        if options:
            for opt in options:
                p = Product(product)
                optname =  opt.xpath('.//meta[@itemprop="name"]/@content').extract()[0]
                p['name'] = optname
                p['price'] = extract_price(opt.xpath('.//meta[@itemprop="price"]/@content').extract()[0])
                p['identifier'] = p['identifier'] + '-' + opt.xpath('@id').re('artikel_element_prices(.*)')[0]
                if p['identifier'] not in self.identifiers:
                    self.identifiers.append(p['identifier'])
                yield p
        else:
            if product['identifier'] not in self.identifiers:
                self.identifiers.append(product['identifier'])
            yield product

    def closing_parse_simple(self, response):
        for item in super(BikeDiscountDeSpider, self).closing_parse_simple(response):
            if item['identifier'] not in self.identifiers:
                self.identifiers.append(item['identifier'])
                yield item
