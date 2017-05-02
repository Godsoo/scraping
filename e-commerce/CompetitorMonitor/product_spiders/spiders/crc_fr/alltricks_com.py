import json
import re
from decimal import Decimal
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from scrapy import log

from product_spiders.spiders.pedalpedal.crcitem import CRCMeta

from product_spiders.base_spiders.primary_spider import PrimarySpider
from product_spiders.items import Product, ProductLoaderWithoutSpacesEU as ProductLoader
from product_spiders.utils import extract_price2uk as extract_price


class AlltricksSpider(PrimarySpider):
    name = "alltricks.com"
    allowed_domains = ('alltricks.com',)
    start_urls = ('http://alltricks.com',)

    csv_file = 'alltricks_crawl.csv'
    parsed_category_page = []

    '''
    def parse(self, response):
        yield FormRequest('http://www.alltricks.com', dont_filter=True,
                formdata={'id_country_selected':'22'}, callback=self.parse2)
    def _start_requests(self):
        yield Request('http://www.alltricks.com/bikewear/sunglasses-goggles/glasses/', callback=self.parse_cat)
    '''

    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        for url in response.css('.nav-first a::attr(href)').extract():
            yield Request(response.urljoin(url), callback=self.parse_cat)

    def parse_cat(self, response):
        hxs = HtmlXPathSelector(response)
        # self.log("Got page %s" % (response.meta.get('page')))
        
        for url in response.css('.alltricks-Product a::attr(href)').extract():
            yield Request(response.urljoin(url), self.parse_product)

        if 'I-Page' in response.url:
            return
        
        try:
            page_size = int(response.xpath('//@data-page-size').extract_first())
        except TypeError:
            return
        page_count = int(response.xpath('//@data-page-count').extract_first())

        for page in xrange(page_count):
            yield Request(response.url + '/I-Page%d_%d' %(page+1, page_size), 
                          self.parse_cat)

        category_id = response.xpath('//input[@id="id_category"]/@value').extract_first()

        brands = response.xpath('//select[@name="brand"]/option/@value').extract()
        for brand in brands:
            yield FormRequest('http://www.alltricks.com/ajax-category.php',
                        dont_filter=True, 
                        formdata={
                        'id_category': category_id,
                        'limit':'80',
                        'brand': brand,
                        'order_by':'alphabetique',
                        'view_mode':'',
                        'page': '1',
                        'ProductAttributeIds': '',
                        'ProductGroupFilterIdsType': '',
                        'ProductAttributeValues': '',
                        'ProductAttributeScope': '',
                        'inStock': 'true',
                        'keyword': '',
                        },
                        callback=self.parse_brand, meta={'brand': brand})

    def parse_brand(self, response):
        hxs = HtmlXPathSelector(response)

        meta = response.meta

        for url in hxs.select('//td[@class="product-name"]//a/@href').extract():
            yield Request(url, callback=self.parse_product)

        pages = list(hxs.select('//div[@class="list-page-wrapper"]/a/@href').re("'[0-9]*'"))
        if pages:
            category_id = hxs.select('//input[@id="id_category"]/@value').extract()[0]
            for page in xrange(1, int(pages[-2].strip('\'')) + 1):

                # Stores category, brand and page to not crawl it again
                category_page = category_id + '-' + meta['brand'] +'-' + str(page)
                if category_page in self.parsed_category_page:
                    continue
                self.parsed_category_page.append(category_page)


                meta['page'] = page
                yield FormRequest('http://www.alltricks.com/ajax-category.php',
                        dont_filter=True, 
                        formdata={
                        'id_category': category_id,
                        'limit':'80',
                        'brand': meta['brand'],
                        'order_by':'alphabetique',
                        'view_mode':'',
                        'page': str(page),
                        'ProductAttributeIds': '',
                        'ProductGroupFilterIdsType': '',
                        'ProductAttributeValues': '',
                        'ProductAttributeScope': '',
                        'inStock': 'true',
                        'keyword': '',
                        },
                        callback=self.parse_brand, meta=meta)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        product_loader = ProductLoader(item=Product(), response=response)
        product_loader.add_value('url', response.url)
        product_loader.add_css('name', '.heading-title-text::text')
        categories = response.css('.breadcrumb a::text').extract()[2:]
        category = categories.pop(0).strip() if categories else ''
        if category == 'All Categories':
            category = categories.pop(0)
        product_loader.add_value('category', category)
        product_loader.add_xpath('brand', '//*[@id="product-header-order-brand"]//img/@alt')
        product_loader.add_xpath('image_url', '//meta[@property="og:image"]/@content')
        product_loader.add_xpath('identifier', '//input[@name="product_id"]/@value')
        price = response.css('.price::text').extract_first()
        if price:
            product_loader.add_value('price', price.replace(' ', ''))
        product_loader.add_value('price', 0)
        stock = response.xpath('//script/text()').re('availability.+')
        if stock and 'InStock' not in stock[0]:
            product_loader.add_value('stock', 0)
        product_loader.add_xpath('sku', '//input[@name="product_id"]/@value')
        item = product_loader.load_item()
        metadata = CRCMeta()
        rrp = response.css('.price-public::text').extract_first()
        if rrp:
            rrp = extract_price(rrp)
            metadata['rrp'] = rrp if float(rrp)>float(item['price']) else ''
            item['metadata'] = metadata
        
        options = response.xpath('//select[@name="product_id"]/option')
        if not options:
            yield item
            return        
        for opt in options:
            product_loader = ProductLoader(item=Product(), selector=opt)
            product_loader.add_value(None, item)
            identifier = opt.xpath('@value').extract_first()
            if not identifier:
                continue
            product_loader.replace_value('identifier', identifier)
            product_loader.replace_value('sku', identifier)
            product_loader.add_xpath('name', 'text()')
            price = response.xpath('//div[@data-value="%s"]' %identifier).css('.alltricks-ChildSelector-customOptionPrice::text').extract_first()
            product_loader.replace_value('price', price.replace(' ', ''))
            stock = opt.xpath('@data-stock-label').extract_first()
            if stock == 'Out of stock':
                product_loader.replace_value('stock', 0)
            option_item = product_loader.load_item()
            option_item['metadata'] = metadata
            yield option_item

    def parse_info(self, response):
        data = json.loads(response.body)
        item = response.meta['item']
        item['identifier'] = data.get('id_product')
        item['price'] = data.get('price')
        item['stock'] = data.get('stock')
        item['sku'] = data.get('reference')
        item['url'] = data.get('product_url')
        metadata = CRCMeta()
        rrp = data.get('price_public', '')
        metadata['rrp'] = rrp if float(rrp)>float(item['price']) else ''
        item['metadata'] = metadata
        yield item
