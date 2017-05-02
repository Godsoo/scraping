import os
import json
import re
from datetime import datetime

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request

from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from product_spiders.items import Product, ProductLoader
from urlparse import urljoin

from toymonitoritems import ToyMonitorMeta, Review, ReviewLoader
from brands import BrandSelector

HERE = os.path.abspath(os.path.dirname(__file__))


class RakutenCoUk(BaseSpider):
    name = 'toymonitor-rakuten.co.uk'
    allowed_domains = ['www.rakuten.co.uk']
    start_urls = ['http://www.rakuten.co.uk/category/931/?l-id=gb_product_allcat_17',]
    errors = []
    brand_selector = BrandSelector(errors)
    #field_modifiers = {'brand': brand_selector.get_brand}
    
    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        subcategory_urls = hxs.select('//li[@class="b-open"]//li/a/@href').extract()
        for url in subcategory_urls:
          yield Request(urljoin(base_url, url))
        
        yield Request(response.url, callback = self.parse_products, dont_filter=True)

    def parse_products(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        # parse pages
        pages = hxs.select('//div[contains(@class, "b-pagination")]/ul/li/a/@href').extract()
        for page in pages:
            yield Request(urljoin_rfc(base_url, page), meta=response.meta, callback=self.parse_products)

        # parse products
        items = hxs.select('//li[@class="b-item"]/div/div[@class="b-img"]/div/a/@href').extract()
        for item in items:
            yield Request(urljoin_rfc(base_url, item), callback=self.parse_product, meta=response.meta)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        
        mpn = hxs.select('//span[@class="b-item"]').re("MPN: ([0-9]+)")
        ean = hxs.select('//span[@class="b-item"]').re("EAN: ([0-9]+)")
        sku = hxs.select('//input[@name="sku"]/@value').extract()
        name = hxs.select('//h1[@class="b-ttl-main"]/text()').extract()[0]
        dealer_name = "".join(hxs.select('//h2[@id="auto_shop_info_name"]//text()').extract()).strip()
        brand = hxs.select('.//span[@itemprop="brand"]/text()').extract()
        if brand:
          brand = brand[0].strip()
        else:
          brand = response.meta.get('brand')

        categories = hxs.select('//ul[@class="b-breadcrumb"]/li/a/text()').extract()
        image_url = hxs.select('//img[@itemprop="image"]/@data-frz-src').extract()

##        options = hxs.select('//script[contains(text(), "var variant_details")]/text()').re('var variant_details = (.*);\n')
        options = hxs.select('//script[contains(text(), "var variant_details")]/text()').extract()
        if options:
            options = options[0].replace('&quot;', "'")
            options = re.findall('var variant_details = (.*);\n', options)
            variants = json.loads(options[0])
        else:
            identifier = hxs.select('//input[@name="item_id"]/@value').extract()[0]
            price = hxs.select('//div[@class="b-product-main"]//meta[@itemprop="price"]/@content').extract()[0]
            variants = [{'itemVariantId': identifier, 'sku': sku, 'variantValues': [], 'defaultPricing': {'price': price}}]

        items = []
        for variant in variants:
            loader = ProductLoader(item=Product(), selector=hxs)
            loader.add_value('identifier', variant['itemVariantId'])
            loader.add_value('name', " ".join([name] + variant.get('variantValues', [])))
            loader.add_value('sku', variant['sku'])
            loader.add_value('url', response.url)
            loader.add_value('price', variant['defaultPricing']['price'])
            loader.add_value('dealer', dealer_name)
            loader.add_value('category', categories)
            if brand:
                loader.add_value('brand', brand)
            if image_url:
                loader.add_value('image_url', image_url[0])
            product = loader.load_item()

            metadata = ToyMonitorMeta()
            metadata['reviews'] = []
            product['metadata'] = metadata

            if mpn or ean:
                if mpn:
                    metadata['mpn'] = mpn[0]
                if ean:
                    metadata['ean'] = ean[0]
                product['metadata'] = metadata
            items.append(product)

        reviews_url = response.xpath('//a[contains(text(), "See All Reviews")]/@href').extract()
        if reviews_url:
            yield Request(reviews_url[0], callback=self.parse_reviews, meta={'items': items, 'url': response.url})
        else:
            for item in items:
                yield item


    def parse_reviews(self, response):
        items = response.meta.get('items', '')
        url = response.meta.get('url', '')

        reviews = response.xpath('//div[contains(@class, "b-review")]')
        for review in reviews:
            l = ReviewLoader(item=Review(), response=response, date_format='%d/%m/%Y')
            rating = len(review.xpath('.//span/span[contains(@class, "b-star-full")]'))
            date = review.xpath('.//div[@class="b-content"]/span[@class="b-text-sub"]/text()').re('\d+/\d+/\d+')[0]
            title = review.xpath('.//div[@class="b-head"]/div/text()').extract()
            review_text = ' '.join(review.xpath('.//div[@class="b-content" and not(child::*)]/text()').extract())

            if title:
                full_text = title[0].strip() + '\n' + review_text.strip()
            else:
                full_text = review_text.strip()

            l.add_value('rating', rating)
            l.add_value('url', url)
            l.add_value('date', date)
            l.add_value('full_text', full_text)
            for item in items:
                item['metadata']['reviews'].append(l.load_item())

        next = response.xpath('//a[@id="right_arrow"]/@href').extract()
        if next:
            yield Request(next[0], callback=self.parse_reviews, meta={'items': items, 'url': url})
        else:
            for item in items:
                yield item
