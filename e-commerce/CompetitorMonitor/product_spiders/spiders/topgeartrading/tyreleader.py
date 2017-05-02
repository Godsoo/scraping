"""
IMPORTANT!!! The spider needs tyre size to be joined to product name.
Please make sure you do this when changing the spider
"""

try:
    from scrapy.spiders import Spider as BaseSpider
except ImportError:
    from scrapy.spider import BaseSpider

from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc, url_query_parameter

from product_spiders.items import Product, ProductLoader
from product_spiders.utils import extract_price

from itertools import product as iter_product


class TyreleaderSpider(BaseSpider):
    name = 'topegeartrading-tyreleader.co.uk'
    allowed_domains = ['tyreleader.co.uk']
    start_urls = ('http://www.tyreleader.co.uk',)
    
    exclude_word = 'DOT'
    
    def parse(self, response):
        yield Request('http://www.tyreleader.co.uk/car-tyres/', callback=self.parse_car_tyres)

        yield Request('http://www.tyreleader.co.uk/alloy-wheels/',
                      callback=self.parse_alloy_wheels,
                      meta={'handle_httpstatus_list': [500]})
        yield Request('http://www.tyreleader.co.uk/steel-wheels/',
                      callback=self.parse_steel_wheels,
                      meta={'handle_httpstatus_list': [500]})

    def parse_steel_wheels(self, response):
        brands = response.xpath('//a[img[contains(@alt, "Steel wheel")]]/@href').extract()
        for url in brands:
            yield Request(url, callback=self.parse_steel_wheels_search, meta={'category': 'Steel Wheels'})

        sub_sel = response.xpath('//div[contains(@class, "row-list")]//a/@href').extract()
        for url in sub_sel:
            yield Request(url, callback=self.parse_steel_wheels_search, meta={'category': 'Steel Wheels'})

    def parse_steel_wheels_search(self, response):
        brand = response.xpath('//div[@id="breadcrumb"]//span[@itemprop="title"]/text()').extract()[-1]

        urls = response.xpath('//div[contains(@class, "row-separator")]//a/@href').extract()

        for url in urls:
            yield Request(url, callback=self.parse_steel_wheels_product_details,
                          meta={'category': response.meta['category'], 'brand': brand})

    def parse_steel_wheels_product_details(self, response):
        brand = response.meta['brand']

        products = response.xpath('//div[@id]/div[@class="row"]/div/div[contains(@class, "thumbnail")]')
        for product in products:
            loader = ProductLoader(item=Product(), selector=product)
            name = brand + ' ' + ' '.join(product.xpath('./a//text()').extract())
            if self.exclude_word in name:
                continue
            loader.add_value('name', name)
            loader.add_value('brand', brand)
            loader.add_value('category', response.meta['category'])
            price = ''.join(product.xpath('.//span[@class="prix"]/text()').re(r'[\d\,.]+')).replace('.', '').replace(",", ".")
            loader.add_value('price', extract_price(price))
            url = product.xpath('./a/@href').extract()[0]
            loader.add_value('url', url)
            identifier = url.split('/')[-1].replace('.', '-')
            cart_url = product.xpath('.//a[contains(@class, "btn-cart")]/@href').extract()
            if cart_url:
                identifier_ext = url_query_parameter(cart_url, 'd')
                if identifier_ext:
                    identifier = identifier + '-' + identifier_ext
            loader.add_value('identifier', identifier)
            loader.add_value('sku', identifier)
            image_url = product.xpath('./a/img/@src').extract()
            if image_url:
                loader.add_value('image_url', image_url[0])

            yield loader.load_item()

    def parse_alloy_wheels(self, response):
        bolts = response.xpath('//select[@name="h"]/option/@value').extract()
        pcd = response.xpath('//select[@name="c"]/option/@value').extract()

        for bolt, pcd in iter_product(bolts, pcd):
            if not bolt or not pcd:
                continue
            params = {
                'bolt': bolt,
                'pcd': pcd,
            }
            yield Request('http://www.tyreleader.co.uk/alloy-wheels-%(bolt)s-%(pcd)s/' % params,
                          callback=self.parse_alloy_wheels_search,
                          meta={'category': 'Alloy Wheels'})

    def parse_alloy_wheels_search(self, response):
        base_url = get_base_url(response)

        urls = filter(lambda u: u != '#',
                      response.xpath('//div[@class="pagination tCenter"]//a/@href').extract())
        for url in urls:
            yield Request(urljoin_rfc(base_url, url),
                          callback=self.parse_alloy_wheels_search,
                          meta=response.meta)

        products = response.xpath('//div[@id="scontent"]/div[@class="row"]/div')
        for product in products:
            loader = ProductLoader(item=Product(), selector=product)
            full_name = product.xpath('.//div[contains(@class, "thumbnail")]/img/@alt').extract()[0]
            if self.exclude_word in full_name:
                continue
            loader.add_value('name', full_name)
            parts = [x for x in product.xpath('.//a//text()').extract()
                     if 'width' not in x.lower() and 'diameter' not in x.lower()]
            part_name = ' '.join(parts)
            if part_name in full_name:
                brand = full_name[:len(full_name) - len(part_name)].strip()
                loader.add_value('brand', brand)
            price = ''.join(product.xpath('.//span[@class="prix"]/text()').re(r'[\d\,.]+')).replace('.', '').replace(",", ".")
            loader.add_value('price', extract_price(price))
            url = product.xpath('.//a/@href').extract()[0]
            loader.add_value('url', url)
            identifier = url.split('/')[-1].replace('.', '-')
            loader.add_value('identifier', identifier)
            loader.add_value('sku', identifier)
            loader.add_value('category', response.meta.get('category', ''))
            image_url = product.xpath('.//div[contains(@class, "thumbnail")]/img/@src').extract()
            if image_url:
                loader.add_value('image_url', image_url[0])
            yield loader.load_item()

    def parse_car_tyres(self, response):
        width = response.xpath('//select[@name="l"]/option/@value').extract()
        for w in width:
            yield Request(
                'http://www.tyreleader.co.uk/car-tyres-%s-0-0/' % w,
                callback=self.parse_car_tyres_width,
                meta={'category': 'Car Tyres', 'width': w})

    def parse_car_tyres_width(self, response):
        height = response.xpath('//select[@name="h"]/option/@value').extract()
        meta = response.meta
        for h in height:
            meta['height'] = h
            yield Request(
                'http://www.tyreleader.co.uk/car-tyres-%(width)s-%(height)s-0/' % meta,
                callback=self.parse_car_tyres_height,
                meta=meta)

    def parse_car_tyres_height(self, response):
        diameter = response.xpath('//select[@name="d"]/option/@value').extract()
        meta = response.meta

        for d in diameter:
            meta['diameter'] = d

            yield Request(
                'http://www.tyreleader.co.uk/car-tyres-%(width)s-%(height)s-%(diameter)s/?orderby=prix' % meta,
                callback=self.parse_car_tyres_search,
                meta=meta)

    def parse_car_tyres_search(self, response):
        base_url = get_base_url(response)

        urls = filter(lambda u: u != '#',
                      response.xpath('//div[@class="pagination tCenter"]//a/@href').extract())
        for url in urls:
            yield Request(urljoin_rfc(base_url, url),
                          callback=self.parse_car_tyres_search,
                          meta=response.meta)

        products = response.xpath('//*[@class="table search-results vCenter"]/tbody//tr')
        for product in products:
            loader = ProductLoader(item=Product(), selector=product)
            brand = product.xpath('./td/a[@class="item-ref"]/span[1]/text()').extract()[0]
            # IMPORTANT!!! The spider needs tyre size to be joined to product name.
            name = ' '.join(product.xpath('./td/a[@class="item-ref"]//text()').extract())
            if self.exclude_word in name:
                continue
            loader.add_value('name', name)
            loader.add_value('brand', brand)
            category = product.xpath('.//td[@class="tCenter"]/i/../text()').extract()
            if category:
                loader.add_value('category', category[0].strip())
            else:
                loader.add_value('category', response.meta.get('category', ''))
            price = ''.join(product.xpath('.//div[@class="hidden-xs"]/span[@class="prix"]/text()').re(r'[\d\.,]+'))\
                      .replace('.', '').replace(",", ".")
            loader.add_value('price', extract_price(price))
            identifier = product.xpath('@data-id').extract()[0]
            loader.add_value('identifier', identifier)
            loader.add_value('sku', identifier)
            url = product.xpath('./td[2]/a/@href').extract()[0]
            loader.add_value('url', urljoin_rfc(base_url, url))
            image_url = product.xpath('./td[@class="img"]//img/@src').extract()
            if image_url:
                if len(image_url) < 250:
                    loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))

            yield loader.load_item()
