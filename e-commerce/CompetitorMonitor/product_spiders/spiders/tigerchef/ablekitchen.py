from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
import re

from scrapy import log
from scrapy.utils.response import get_base_url
from urlparse import urljoin as urljoin_rfc

from product_spiders.items import Product
from tigerchefloader import TigerChefLoader as ProductLoader

from tigerchefitems import TigerChefMeta

class AblekitchenSpider(BaseSpider):
    name = 'ablekitchen.com'
    allowed_domains = ['ablekitchen.com']
    start_urls = ('http://www.ablekitchen.com',)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        categories = hxs.select('//div[@class="topnav_sec"]/div/div/div/a/@href').extract()

        for category in categories:
            yield Request(category, callback=self.parse_subcategories)

    def parse_subcategories(self, response):
        hxs = HtmlXPathSelector(response)

        meta = response.meta
    
        sub_cats = hxs.select('//div[@class="leftscroll_text_subcategory"]/ul/li/a')
        for sub_cat in sub_cats:
            url = sub_cat.select('@href').extract()[0].strip()
            if url != '#':
                meta['category'] = sub_cat.select('text()').extract()[0].split(' (')[0].strip()
                yield Request(url, callback=self.parse_brands, meta=meta)

    def parse_brands(self, response):
        hxs = HtmlXPathSelector(response)
        meta = response.meta

        brands = hxs.select('//li[a[@data-facet="manufacturer"]]')
        if brands:
            for brand in brands:
                url = response.url+'?form_values=&manufacturer='+brand.select('input/@value').extract()[0]
                meta['brand'] = brand.select('a/text()').extract()[0].split(u' (')[0]
                yield Request(url, callback=self.parse_products, meta=meta)
        else:
            sub_cats = hxs.select('//div[@class="leftscroll_text_subcategory"]/ul/li/a')
            for sub_cat in sub_cats:
                url = sub_cat.select('@href').extract()[0].strip()
                if url != '#':
                    meta['category'] = sub_cat.select('text()').extract()[0].split(' (')[0].strip()
                    yield Request(url, callback=self.parse_brands, meta=meta)


    def parse_products(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        meta = response.meta

        products = hxs.select('//li[contains(@itemtype, "Product")]')
        for product in products:
            product_loader = ProductLoader(Product(), product, spider_name=self.name)
            product_loader.add_xpath('name', './/a[@itemprop="name"]/text()')
            product_loader.add_xpath('url', './/a[@itemprop="name"]/@href')
            product_loader.add_xpath('price', './/span[@itemprop="price"]/text()')
            product_loader.add_xpath('image_url', 'div/a/img/@src')
            identifier = product.select('@id').extract()[0].split('product_')[-1]
            product_loader.add_value('identifier', identifier)
            product_loader.add_value('category', meta.get('category'))
            product_loader.add_value('brand', meta.get('brand'))

            sku = product.select('.//span[@itemprop="model"]/text()')
            if sku:
                
                sku = sku.extract()[0]
                '''
                dash_pos = sku.find('-')
                if dash_pos >= 0:
                    sku = sku[dash_pos + 1:]
                '''
                product_loader.add_value('sku', sku)

            sold_as = product.select('div/div/div/div/span[contains(text(), "Sold As")]/text()').extract()
            product = product_loader.load_item()
  
            metadata = TigerChefMeta()
            metadata['sold_as'] = sold_as[0].split('Sold As: ')[-1].strip() if sold_as else '1 ea'
            product['metadata'] = metadata

            yield product

        next_page = hxs.select('//td[@class="next"]/a[@class="pagerlink"]/@href').extract()
        if next_page:
            yield Request(urljoin_rfc(base_url, next_page[0]), callback=self.parse_products, meta=meta)



    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        loader = response.meta['loader']

        category = hxs.select('//div[@id="wapper"]/div[@class="statemenu"]/div[@class="statemenu2"]/ul/li[@class="active"]//text()').extract()
        if not category:
            #try another one
            category = hxs.select('(//div[@id="wapper"]/div[@class="statemenu"]/div[@class="statemenu2"]/ul/li[@itemprop="title"])[position()=1]//text()').extract()

        if not category:
                self.log("ERROR category not found")
        else:
            loader.add_value("category", category[0].strip())

        img = hxs.select('//div[@class="pro_box"]/a/img/@src').extract()
        if not img:
            self.log("ERROR img not found")
        else:
            loader.add_value("image_url",img[0])

        brand = hxs.select('//div[@class="productcode1"]/span[@class="content18" and contains(text(),"Brand:")]/span//text()').extract()
        if not brand:
            self.log("ERROR brand not found")
        else:
            loader.add_value("brand",brand[0].strip())

        identifier = ""
        review_url = hxs.select('//a[contains(text(),"write a review")]/@href').extract()
        if not review_url:
            self.log("ERROR review_url not found")
        else:
            ttt = review_url[0]
            m = re.search('((?<=product_id\=)(.*))',ttt)
            if m:
                identifier = m.group(1)

        if not identifier:
            self.log("ERROR identifier not found")
        else:
            loader.add_value("identifier", identifier.strip())

        product = loader.load_item()

        yield product
