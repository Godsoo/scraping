import re
import os

from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from product_spiders.items import Product
from product_spiders.base_spiders.bigsitemethodspider import BigSiteMethodSpider

from tigerchefloader import TigerChefLoader as ProductLoader
from tigerchefitems import TigerChefMeta

HERE = os.path.abspath(os.path.dirname(__file__))

class WasserstromSpider(BigSiteMethodSpider):
    name = 'wasserstrom.com'
    allowed_domains = ['wasserstrom.com']
    start_urls = ('http://www.wasserstrom.com/',)

    website_id = 397491

    full_crawl_day = 6

    product_loader = ProductLoader
    metadata_class = TigerChefMeta

    def parse_full(self, response):

        hxs = HtmlXPathSelector(response)
        # categories
        cats = hxs.select('//td[@class="popover_link"]/a/@href').extract()

        for cat in cats:
            yield Request(cat, callback=self.parse_full)

        sub_cats = hxs.select('//table[@class="sub_cats_table"]//td/h3/a/@href').extract()
        for sub_cat in sub_cats:
            yield Request(sub_cat, callback=self.parse_full)


        next = hxs.select('//a[@class="paginglink" and contains(text(), "Next")]/@href').extract()

        if next:
            yield Request(urljoin_rfc(get_base_url(response), next[0]), callback=self.parse_full)

        products = hxs.select('//div[@class="displayproducttitle"]//a/@href').extract()

        for product in products:
            yield Request(product, callback=self.parse_product)

    def parse_product(self, response):

        # self.log("parse_product")

        hxs = HtmlXPathSelector(response)

        name = hxs.select('//h1[@id="partNameId"]/text()').extract()

        quantity = hxs.select('//label[@class="productdetail-qtytxt"]/../text()[last()]').extract()
        if quantity:
            quantity = quantity[0].replace('\n', ' ').replace('\r', ' ').replace('\t', ' ').strip()
            quantity = re.sub(' +', ' ', quantity)

        loader = ProductLoader(response=response, item=Product(), spider_name=self.name)
        
        if not name:
            self.log("ERROR name not found")
        else:
            loader.add_value('name', name[0].strip())

        brand = hxs.select('//div[@class="productdetail-contentarea-wrapper"]/table/tr/td[.//b[contains(text(),"Manufacturer:")]]/a/text()').extract()
        if not brand:
            self.log("ERROR brand not found")
        else:
            loader.add_value("brand", brand[0].strip())


        img_url = hxs.select('//div[@class="productdetail-productimage"]/a/img/@src').extract()
        if not img_url:
            self.log("ERROR img_url not found")
        else:
            loader.add_value("image_url", img_url[0])

        category = hxs.select('(//div[@id="productdetail-crumbcategory"]/ul/li/a)[last()]/text()').extract()
        if not category:
            self.log("ERROR category not found")
        else:
            loader.add_value("category", category[0].strip())

        # self.log("name = " + name[0].strip() + ", quantity = " + quantity.strip())

        if quantity and quantity.lower() != 'each':
            loader.add_value('name', quantity)

        loader.add_value('url', response.url)
        loader.add_xpath('price', '//font[@class="txt-purchaseprice20blue"]/text()')
        sku = ''.join(hxs.select('//b[contains(text(), "Model #:")]/../text()').extract()).strip()
        temp = sku.split()
        if len(temp) == 2 and temp[0] == temp[1]:
            sku = temp[0]
        loader.add_value('sku', sku)
        loader.add_xpath('identifier', '//form//input[@name="productId"]/@value')

        product = loader.load_item()

        metadata = TigerChefMeta()
        metadata['sold_as'] = quantity if quantity else '1 ea'
        product['metadata'] = metadata

        yield product

    # def parse_simple(self, response):
    #
    #     hxs = HtmlXPathSelector()
    #     products = json.loads(response.body)
    #
    #     self.matched = products.get('matches', [])
    #
    #     identifiers = []
    #     for prod in self.matched:
    #         identifiers.append(prod['identifier'])
    #         yield Request(prod['url'], self.parse_product)
    #
    #     crawl_id = open(os.path.join(HERE, 'wasserstrom_crawl')).read().strip()
    #     shutil.copy('data/meta/%s_meta.json' % crawl_id, os.path.join(HERE, 'wasserstrom.json'))
    #
    #     with open(os.path.join(HERE, 'wasserstrom.json')) as f:
    #         products = json.loads(f.read())
    #         for prod in products:
    #             if prod['identifier'] not in identifiers:
    #                 loader = ProductLoader(selector=hxs, item=Product())
    #                 loader.add_value('url', prod.get('url',''))
    #                 loader.add_value('sku', prod.get('sku',''))
    #                 loader.add_value('identifier', prod['identifier'])
    #                 loader.add_value('name', prod['name'])
    #                 loader.add_value('price', prod['price'])
    #                 loader.add_value('brand', prod.get('brand',''))
    #                 loader.add_value('image_url', prod.get('image_url',''))
    #                 loader.add_value('category', prod.get('category',''))
    #                 product = loader.load_item()
    #                 metadata = TigerChefMeta()
    #                 metadata['sold_as'] = prod['metadata'].get('sold_as')
    #                 product['metadata'] = metadata
    #                 yield product


