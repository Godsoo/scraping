import os
import re
import shutil
from datetime import datetime

from scrapy import signals
from scrapy import log
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url
from scrapy.xlib.pydispatch import dispatcher

from johnlewisitems import JohnLewisMeta, Review, ReviewLoader

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

HERE = os.path.abspath(os.path.dirname(__file__))

class bootsSpider(BaseSpider):
    name = 'johnlewis-trial-boots.com'
    allowed_domains = ['boots.com', 'bootskitchenappliances.com', 'boots.ugc.bazaarvoice.com']
    start_urls = [
          'http://www.boots.com/en/Photo/Digital-Cameras',
          'http://www.bootskitchenappliances.com/dishwashers/Dishwashers.aspx',
          'http://www.bootskitchenappliances.com/fridge-freezers/fridge-freezers.aspx',
          'http://www.bootskitchenappliances.com/refrigerators/Refrigerators.aspx',
          'http://www.bootskitchenappliances.com/freezers/Freezers.aspx',
          'http://www.bootskitchenappliances.com/range-cookers/range-cookers.aspx',
          'http://www.bootskitchenappliances.com/cookers/Cookers.aspx',
          'http://www.bootskitchenappliances.com/ovens/Ovens.aspx',
          'http://www.bootskitchenappliances.com/hobs/Hobs.aspx',
          'http://www.boots.com/en/Toys/Pre-school-toys/',
          'http://www.boots.com/en/Toys/Boys-toys',
          'http://www.boots.com/en/Toys/Girls-toys',
          'http://www.boots.com/webapp/wcs/stores/servlet/CategoryDisplay?categoryParentId=&storeId=10052&categoryId=333979&catalogId=11051&langId=-1',
          'http://www.boots.com/en/Fragrance/Fragrance-gift-sets/',
          'http://www.boots.com/en/Fragrance/Fragrance-for-her/',
          'http://www.boots.com/en/Fragrance/Fragrance-for-him/',
          'http://www.boots.com/en/Beauty/Premium-Beauty/Premium-Grooming-for-Men']

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        meta = response.meta

        products = hxs.select('//div[@id="ProductViewListGrid"]')
        if products:
            brands = hxs.select('//div[h3/text()="By brand:"]/ul/li/a')
            if brands:
                for brand in brands:
                    brand_url = brand.select('@href').extract()[0]
                    brand_name = brand.select('text()').extract()[0].split(u'\xa0')[0]
                    yield Request(brand_url, meta={'brand':brand_name})
            else:
                yield Request(response.url, dont_filter=True, callback=self.parse_products, meta=meta)
        else:
            categories = hxs.select('//div[@class="narrowResults"]/div[1]/ul/li/a/@href').extract()
            for category in categories:
                yield Request(category, meta=meta)
            if not categories:
                categories = hxs.select('//div[@class="AppBoxLinks"]/ul/li/a/@href').extract()
                for category in categories:
                    url = urljoin_rfc(get_base_url(response), category)
                    yield Request(url, callback=self.parse_size_products, meta=meta)

    def parse_products(self, response):
        hxs = HtmlXPathSelector(response)
        meta = response.meta
        products = hxs.select('//div[@id="ProductViewListGrid"]/div')
        if products:
            for product in products:
                loader = ProductLoader(item=Product(), selector=product)
                loader.add_xpath('name', 'div//div[@class="pl_productName"]/a/text()')
                sku = product.select('div//div[@class="pl_productCode"]/text()').extract()[0].strip()
                loader.add_value('sku', sku)
                loader.add_value('brand', meta.get('brand'))
                loader.add_value('identifier', sku)
                loader.add_xpath('url', 'div//div[@class="pl_productName"]/a/@href')
                loader.add_xpath('price', 'div//div[@class="pl_price"]/text()')
                item = loader.load_item()
                price_was = product.select('div//div[@class="pl_priceWas"]/text()').extract()
                price_was = price_was[0] if price_was else ''

                metadata = JohnLewisMeta()
                metadata['promotion'] = price_was
                metadata['reviews'] = []
                item['metadata'] = metadata

                yield Request(item['url'], callback=self.parse_product, meta={'item':item})

            next = hxs.select('//li[@class="next"]/a/@href').extract()
            if next:
                yield Request(next[0], callback=self.parse_products)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        item = response.meta['item']

        category = hxs.select('//div[@class="breadcrumb"]/ul/li/a/text()').extract()[-1]
        image_url = hxs.select('//p/img/@src').extract()
        image_url = image_url[-1] if image_url else ''
        out_of_stock = hxs.select('//a[contains(@class, "out_of_stock")]')

        if out_of_stock:
            item['stock'] = 0

        item['category'] = category
        item['image_url'] = image_url
        if item['price'] <= 45:
            item['shipping_cost'] = 2.95

        item['metadata'] = metadata

        reviews_url = 'http://boots.ugc.bazaarvoice.com/2111-en_gb/%s/reviews.djs?format=embeddedhtml'
        part_number = re.search(r'_(\d+)/', response.url).group(1)
        yield Request(reviews_url % part_number, callback=self.parse_review_page, meta={'product': item})

    def parse_review_page(self, response):
        item_ = response.meta.get('product', '')
        hxs = HtmlXPathSelector(response)
        reviews = hxs.select('//div[@class="BVRRReviewDisplayStyle2"]')
        if not reviews:
            hxs = HtmlXPathSelector(text=self._extract_html(response))
            reviews = hxs.select('//div[@class="BVRRReviewDisplayStyle5"]')

        for review in reviews:
            l = ReviewLoader(item=Review(), response=response, date_format='%m/%d/%Y')
            rating = review.select(".//span[contains(@class,'BVRRRatingNumber')]/text()").extract()[0]
            date = review.select(".//span[contains(@class,'BVRRValue BVRRReviewDate')]/text()").extract()[0]
            review = review.select(".//span[contains(@class,'BVRRReviewText')]/text()")[1].extract()

            l.add_value('rating', rating)
            l.add_value('url', response.url)
            l.add_value('date', datetime.strptime(date, '%d %B %Y').strftime('%m/%d/%Y'))
            l.add_value('full_text', review)
            item_['metadata']['reviews'].append(l.load_item())

        next = hxs.select('//span[@class="BVRRPageLink BVRRNextPage"]/a/@data-bvjsref').extract()
        if not next:
            next = hxs.select('//span[@class="BVRRPageLink BVRRNextPage"]/a/@href').extract()

        if next:
            yield Request(next[0], callback=self.parse_review_page, meta={'product': item_})
        else:
            yield item_

    def parse_size_products(self, response):
        hxs = HtmlXPathSelector(response)
        url = hxs.select('//ul[@id="pageSize"]/a[text()="All"]/@href').extract()[0]
        if url:
            url = urljoin_rfc(get_base_url(response), url)
            yield Request(url, callback=self.parse_kitchen_products)

    def parse_kitchen_products(self, response):
        hxs = HtmlXPathSelector(response)
        products = hxs.select('//div[@id="productListerPage"]/div[@class="thirdproducton" or @class="thirdproductoff"]/div')
        for product in products:
            loader = ProductLoader(item=Product(), selector=product)
            loader.add_xpath('name', 'h2/a/strong/text()')
            url = product.select('h2/a/@href').extract()
            if url:
                url = urljoin_rfc(get_base_url(response), url[0])
                loader.add_value('url', url)
                image_url = product.select('div[@class="listerPrice"]/a/img/@src').extract()
                if image_url:
                    loader.add_value('image_url', urljoin_rfc(get_base_url(response), image_url[0]))
                loader.add_xpath('sku', 'div[@class="priceBox"]/div/a/@productcode')
                loader.add_xpath('category', '//ul[@id="menuSelected"]/li/a/span/text()')
                loader.add_xpath('identifier', 'div[@class="priceBox"]/div/a/@productcode')
                loader.add_xpath('price', 'div[@class="priceBox"]/a/strong/text()')
                item = loader.load_item()
                if item['price'] <= 45:
                    item['shipping_cost'] = 2.95
                item['brand'] = item['name'].split()[0]
                price_was = ''.join(product.select('div//span[@class="wasPrice"]//text()').extract())

                metadata = JohnLewisMeta()
                metadata['promotion'] = price_was
                metadata['reviews'] = []
                item['metadata'] = metadata

                reviews_url = 'http://reviews.bootskitchenappliances.com/5627b-en_gb/%s/reviews.htm?format=embedded&reviewID=%s&scrollToTop=true'
                part_number = re.search(r'-(\d+).aspx', url).group(1)
                yield Request(reviews_url % (part_number, part_number), callback=self.parse_review_page, meta={'product': item})

    def _extract_html(self, response):
        review_html = ''
        for line in response.body.split('\n'):
            if 'var materials=' in line:
                review_html = line.split('"BVRRSecondaryRatingSummarySourceID":" ')[-1].split('\n}')[0].replace('\\', '')
        return review_html
