import csv
import json
import StringIO

from scrapy import Spider

from scrapy import Request, FormRequest, signals
from scrapy.xlib.pydispatch import dispatcher

from product_spiders.utils import extract_price
from product_spiders.base_spiders.primary_spider import PrimarySpider
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader


class Gear4Music(Spider):
    name = 'gear4music-gear4music.com'
    allowed_domains = ['gear4music.com', 'competitormonitor.com']
    start_urls = ('http://www.gear4music.com',)

    matched_identifiers = []

    def start_requests(self):
        yield Request('https://app.competitormonitor.com/api/get_matched_products.json?website_id=1827&api_key=3Df7mNg',
                      callback=self.parse_matches)

    def parse_matches(self, response):
        data = json.loads(response.body)
        matches = data['matches']
        urls = []
        for match in matches:
            self.matched_identifiers.append(match['identifier'])
            urls.append(match['url'])

        for url in urls:
            yield Request(url, callback=self.parse_product)

    def parse_product(self, response):
        product_loader = ProductLoader(item=Product(), response=response)
        product_loader.add_value('url', response.url)
        product_loader.add_xpath('name', u'//h1[@class="product"]/text()')
        product_loader.add_xpath('category', u'//div[@class="breadcrumb-item"][last()]/a/span[@itemprop="title"]/text()')
        price = response.xpath(u'//span[@itemprop="price"]/text()').extract()
        price = extract_price(price[0]) if price else 0
        product_loader.add_value('price', price)
        product_loader.add_xpath('identifier', u'//p[contains(@class, "prd-ref")]/text()', re=u'Product Ref: (.*)')
        product_loader.add_value('sku', product_loader.get_output_value('identifier'))

        product_loader.add_xpath('brand', u'//meta[@itemprop="brand"]/@content')

        img = response.xpath(u'//meta[@property="og:image"]/@content').extract()
        if img:
            product_loader.add_value('image_url', response.urljoin(img[0]))
        stock = response.xpath('//p[contains(@class, "instock")]/text()').re('^In Stock')
        if not stock:
            stock = response.xpath('//p[contains(@class, "instock")]/text()').re('Stock Available')

        if not stock:
            stock = response.xpath('//p[contains(@class, "instock")]/text()').re('\d+')
            if stock:
                product_loader.add_value('stock', int(stock[0]))

        if not stock:
            product_loader.add_value('stock', 0)

        # Collect only matched products
        item = product_loader.load_item()
        if item['identifier'] in self.matched_identifiers:
            yield item

    def parse(self, response):
        #categories
        category_urls = response.xpath('//ul[@class="menu_list_third"]/li/a/@href').extract()
        for url in category_urls:
            yield Request(response.urljoin(url))

        #subcategories
        subcategory_urls = response.xpath('//ul[@class="brands-list"]//a/@href').extract()
        for url in subcategory_urls:
            yield Request(response.urljoin(url))

        manufacturers = response.xpath('//ul[contains(@class, "check-list")]/li//input[@name="m[]"]/@value').extract()
        ignore_manufacturers = response.meta.get('ignore_manufacturers', False)
        if not ignore_manufacturers and manufacturers:
            formdata = {'_lp': response.xpath('//form[@id="pf_frm"]//input[@name="_lp"]/@value').extract()[0],
                        '_up': response.xpath('//form[@id="pf_frm"]//input[@name="_up"]/@value').extract()[0],
                        'lp': response.xpath('//form[@id="pf_frm"]//input[@name="lp"]/@value').extract()[0],
                        'up': response.xpath('//form[@id="pf_frm"]//input[@name="up"]/@value').extract()[0],
                        'w': response.xpath('//form[@id="pf_frm"]//input[@name="w"]/@value').extract()[0]
                       }
            for manufacturer in manufacturers:
                formdata['m[]'] = manufacturer
                form_url = 'http://www.gear4music.com/search/product-finder'
                yield FormRequest(form_url, dont_filter=True, formdata=formdata, callback=self.parse, meta={'ignore_manufacturers': True})


        #next page
        next_pages = [] # response.xpath('').extract()
        for url in next_pages:
            yield Request(response.urljoin(url))

        products = response.xpath('//ul[@class="result-list"]//a[descendant::h3]/@href').extract()
        for url in products:
            yield Request(response.urljoin(url), callback=self.parse_product)
