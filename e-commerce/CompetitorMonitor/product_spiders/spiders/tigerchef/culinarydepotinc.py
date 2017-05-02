import re
import os

from scrapy import log
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc, canonicalize_url

from product_spiders.items import Product
# from product_spiders.base_spiders.bigsitemethodspider import BigSiteMethodSpider

from tigerchefloader import TigerChefLoader
from tigerchefitems import TigerChefMeta

identifier_regex = re.compile(r'\/(p-\d*)-')

HERE = os.path.abspath(os.path.dirname(__file__))

class CulinaryDepotIncSpider(BaseSpider):
    name = 'culinarydepotinc.com'
    allowed_domains = ['culinarydepotinc.com']
    start_urls = ('http://www.culinarydepotinc.com',)

    rotate_agent = True

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        cats = hxs.select('//div[@class="leftNav"]//ul/li/a/@href').extract()
        cats += hxs.select('//ul[@class="tame"]/li/a/@href').extract()
        cats += [c for c in hxs.select('//td[@id="featuredProductsTable"]//a/@href').extract() if 'c-' in c]
        if cats:
            for cat in cats:
                yield Request(
                        url=canonicalize_url(urljoin_rfc(base_url, cat)),
                        cookies={'pagesize': 10000})

        next_page = hxs.select(
                '//li[@class="pagingPreviousNext"]'
                '/a[starts-with(text(), "Next")]/@href').extract()
        log.msg(">>>>>>>>>>>>>>>>> NEXT PAGE >>> %s" % next_page)
        if next_page:
            log.msg(">>>>>>>>>>>>>>>>> TURN TO NEXT PAGE")
            yield Request(
                    url=urljoin_rfc(base_url, next_page[0]),
                    callback=self.parse_full)

        for product in self.parse_products(response):
            yield product

    def parse_products(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        products = hxs.select('//div[contains(@class, "productResult")]')
        log.msg(">>>>>>>> FOUND %s ITEMS >>>" % len(products))
        for product in products:
            product_loader = TigerChefLoader(Product(), product, spider_name=self.name)
            product_loader.add_xpath(
                    'name', './/h2[@class="productResultName"]/a/text()')
            try:
                name = product.select('.//h2[@class="productResultName"]/a/text()').extract()[0]
            except:
                self.log('Cannot find name %s' % response.url)
            url = product.select(
                    './/h2[@class="productResultName"]/a/@href'
                    ).extract()[0]
            url = canonicalize_url(urljoin_rfc(base_url, url))
            price = ' '.join(product.select(
                    './/span[@class="variantprice"]//text()').extract())
            identifier = identifier_regex.search(url).group(1)
            yield Request(url, callback=self.parse_product, meta={'name': name,
                                                                  'price': price,
                                                                  'identifier': identifier})

        products2 = hxs.select('//div[contains(@id, "ageContent_pnlContent")]/table/tr/td/table/tr[2]/td/a/@href').extract()
        for url in products2:
            identifier = identifier_regex.search(url).group(1)
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product, meta={'identifier': identifier})

        if not products and not products2 and not hxs.select('//td[@id="featuredProductsTable"]'):
            retry = int(response.meta.get('retry', 0))
            if retry < 10:
                self.log('WARNING: No products and no subcategories, Retry => %s' % response.url)
                retry += 1
                new_meta = response.meta.copy()
                new_meta['retry'] = retry
                yield Request(
                    response.url,
                    meta=new_meta,
                    cookies={'pagesize': 10000},
                    callback=self.parse_products,
                    dont_filter=True)
            else:
                self.log('ERROR - NO PRODUCTS FOUND, retry limit reached, giving up, url: {}'.format(response.url))

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        meta = response.meta

        sku = hxs.select('.//span[@itemprop="sku"]/text()').extract()
        if not sku:
            return

        sku = sku[0].strip()

        name = meta.get('name', None)
        if not name:
            name = ''.join(hxs.select('//span[@itemprop="name"]/text()').extract())

        brand_r = re.search(r'by (.*)$', name)

        if brand_r:
            brand = brand_r.group(1)
        else:
            if sku in name:
                try:
                    brand = re.search(r'^(.*) %s' % re.escape(sku), name).groups()[0].strip()
                except AttributeError:
                    brand = ''
            else:
                brand = ''

        if not brand:
            brand = response.xpath('//span[@itemprop="manufacturer"]/text()').extract()
            brand = brand[0].strip() if brand else ''

        product_loader = TigerChefLoader(Product(), response=response, spider_name=self.name)
        product_loader.add_value('name', name)
        if 'identifier' in meta:
            product_loader.add_value('identifier', meta['identifier'])
        elif 'item' in meta and 'identifier' in meta['item']:
            product_loader.add_value('identifier', meta['item']['identifier'])
        price = meta.get('price', None)
        if not price:
            price = hxs.select('//div[@itemprop="price"]/span/span/text()').extract()
        if not price:
            price = hxs.select('//div[@itemprop="price"]/span/text()').extract()
        product_loader.add_value('price', price or '0')
        product_loader.add_value('url', response.url)
        product_loader.add_value('sku', sku)
        category = hxs.select('//span[@class="SectionTitleText"]/li/a/text()')
        category = category[-1].extract() if category else ''
        product_loader.add_value('category', category)
        product_loader.add_value('brand', brand)

        image_url = hxs.select('//div[@id="prodImageMediumBox"]//div/div/img/@src').extract()
        image_url = urljoin_rfc(base_url, image_url[0]) if image_url else ''
        product_loader.add_value('image_url', image_url)

        sold_as = hxs.select('//table[@id="prodInfo"]/tr/td[div/div[@itemprop="price"]]/span[@class="details"]/text()').extract()
        product = product_loader.load_item()
        metadata = TigerChefMeta()
        metadata['sold_as'] = ' '.join(sold_as[0].replace('/', '').split()) if sold_as else ''
        product['metadata'] = metadata

        yield product
