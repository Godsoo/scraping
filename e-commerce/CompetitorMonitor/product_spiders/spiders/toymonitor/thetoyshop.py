import re
import os
import xlrd
from datetime import datetime

from scrapy import log
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

from product_spiders.items import (
    Product,
    ProductLoaderWithNameStrip as ProductLoader
)

from toymonitoritems import ToyMonitorMeta, Review, ReviewLoader

from utils import brand_in_file
from brands import BrandSelector

HERE = os.path.abspath(os.path.dirname(__file__))


class TheToyShopSpider(BaseSpider):
    name = 'toymonitor-thetoyshop.com'
    allowed_domains = ['thetoyshop.com', 'theentertainer.ugc.bazaarvoice.com']
    start_urls = ['http://www.thetoyshop.com/']
    brands_to_monitor = []
    errors = []
    brand_selector = BrandSelector(errors)
    #field_modifiers = {'brand': brand_selector.get_brand}

    def parse_sitemap(self, response):
        categories = response.xpath('//div[@id="main"]//a/@href').extract()
        for category in categories:
            url = response.urljoin(category)
            yield Request(url, callback=self.parse_brand)

    def parse(self, response):
        categories = response.xpath('//li[contains(@class,"listing category parent")]//a/@href').extract()
        for category in categories:
            url = response.urljoin(category)
            yield Request(url, callback=self.parse_brands)
        yield Request('http://www.thetoyshop.com/sitemap', callback=self.parse_sitemap)

    def parse_brands(self, response):
        if not isinstance(response, HtmlResponse):
            return
        base_url = get_base_url(response)

        hxs = HtmlXPathSelector(response)
        brands = hxs.select('//div[div/h3[contains(text(), "by brand")]]/div/ul/li/a')
        for brand in brands:
            brand_name = brand.select('text()').extract()[0].split('\n')[0]
            brand_url = brand.select('@href').extract()[0]
            url = response.urljoin(brand_url)
            yield Request(url, callback=self.parse_brand, meta={'brand': brand_name})
        for item in self.parse_brand(response):
            yield item

    def parse_brand(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        categories = response.xpath('//div[contains(@class, "category")]/div/ul/li/a/@href').extract()
        categories += response.xpath('//li[contains(@class, "-list-li")]/a/@href').extract()
        for url in categories:
            url = response.urljoin(url)
            yield Request(url, callback=self.parse_brand, meta=response.meta)

        next_page = hxs.select(u'//li[@class="page next"]/a/@href').extract()
        if next_page:
            yield Request(response.urljoin(next_page[0]), callback=self.parse_brand, meta=response.meta)

        products = hxs.select(u'//h3[@class="prod_name"]/a/@href').extract()
        for url in products:
            url = response.urljoin(url)
            yield Request(url, callback=self.parse_product, meta=response.meta)

    def parse_product(self, response):
        if not isinstance(response, HtmlResponse):
            return

        hxs = HtmlXPathSelector(response)
        loader = ProductLoader(item=Product(), selector=hxs)

        name = hxs.select(u'//div[@class="prod_title"]/h1/text()').extract()
        if not name:
            self.log('ERROR: no product NAME found! URL:{}'.format(response.url))
            return
        else:
            name = name[0].strip()
            loader.add_value('name', name)

        prod_id = hxs.select('//input[@name="productCode"]/@value').extract()
        loader.add_value('identifier', prod_id[0])

        loader.add_value('url', response.url)

        price = hxs.select(u'//h3[@class="prod_price"]/text()').extract()[0].strip()
        if not price:
            self.log('ERROR: no product PRICE found! URL:{}'.format(response.url))
            return
        if price:
            loader.add_value('price', price)

        product_image = hxs.select(u'//a[@id="imageLink"]/img/@src').extract()
        if not product_image:
            self.log('ERROR: no product Image found!')
        else:
            image = urljoin_rfc(get_base_url(response), product_image[0].strip())
            loader.add_value('image_url', image)

        categories = hxs.select(u'//nav[@id="breadcrumb"]/ol/li/a/text()').extract()[1:-1]
        if not categories:
            self.log('ERROR: category not found! URL:{}'.format(response.url))
        else:
            for category in categories:
                loader.add_value('category', category.strip())

        sku = hxs.select('//dl[dt/text()="Our Product Number"]/dd/text()').extract()
        if not sku:
            self.log('ERROR: no SKU found! URL:{}'.format(response.url))
        else:
            loader.add_value('sku', sku[0].strip())

        loader.add_value('brand', response.meta.get('brand', ''))

        item = loader.load_item()
        metadata = ToyMonitorMeta()
        ean = ''.join(hxs.select('//dl[dt/text()="Manufacturer Number"]/dd/text()').extract()).strip()
        if ean:
            metadata['ean'] = ean
        promo = response.xpath('//div[@class="prod_details_main"]/span[@class="badge"]/img/@alt').extract()
        if promo:
            metadata['promotions'] = promo[0]
        metadata['reviews'] = []
        item['metadata'] = metadata

        reviews_url = 'http://theentertainer.ugc.bazaarvoice.com/6038-en_gb/%s/reviews.djs?format=embeddedhtml&page=1&scrollToTop=true'
        yield Request(reviews_url % item['identifier'], callback=self.parse_review_page, meta={'item': item})


    def parse_review_page(self, response):
        item_ = response.meta.get('item', '')
        hxs = HtmlXPathSelector(text=self._extract_html(response))
        reviews = hxs.xpath('//div[@class="BVRRReviewDisplayStyle5"]')
        for review in reviews:
            l = ReviewLoader(item=Review(), response=response, date_format='%d/%m/%Y')
            rating = review.select(".//span[contains(@class,'BVRRRatingNumber')]/text()").extract()[0]
            date = review.select(".//span[contains(@class,'BVRRValue BVRRReviewDate')]/text()").extract()[0]
            title = review.select(".//span[contains(@class,'BVRRReviewTitle')]/text()").extract()
            review_text = review.select(".//span[contains(@class,'BVRRReviewText')]/text()").extract()[0]

            if title:
                full_text = title[0].strip() + '\n' + review_text.strip()
            else:
                full_text = review_text.strip()

            l.add_value('rating', rating)
            l.add_value('url', item_['url'])
            l.add_value('date', datetime.strptime(date, '%d %B %Y').strftime('%d/%m/%Y'))
            l.add_value('full_text', full_text)
            item_['metadata']['reviews'].append(l.load_item())

        next = hxs.xpath('//span[@class="BVRRPageLink BVRRNextPage"]/a/@data-bvjsref').extract()
        if next:
            yield Request(next[0], callback=self.parse_review_page, meta={'item': item_})
        else:
            yield item_

    def _extract_html(self, response):
        review_html = ''
        for line in response.body.split('\n'):
            if 'var materials=' in line:
                review_html = line.split('"BVRRSecondaryRatingSummarySourceID":" ')[-1].split('\n}')[0].replace('\\', '')
        return review_html
