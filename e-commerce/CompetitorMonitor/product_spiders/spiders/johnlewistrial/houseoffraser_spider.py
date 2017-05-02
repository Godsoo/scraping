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
from product_spiders.base_spiders.prodcache import ProductCacheSpider

HERE = os.path.abspath(os.path.dirname(__file__))

class HouseOfFraserSpider(ProductCacheSpider):
    name = 'johnlewis-trial-houseoffraser.co.uk'
    allowed_domains = ['houseoffraser.co.uk', 
                       'houseoffraserkitchenappliances.co.uk', 
                       'houseoffraser.ugc.bazaarvoice.com']
    start_urls = [
        'http://www.houseoffraser.co.uk/Electricals/10,default,sc.html',
        'http://www.houseoffraserkitchenappliances.co.uk/',
    ]

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        categories = hxs.select('//div[@id="categoryQuickLinks"]//ul[@class="secondary"]/li/a/@href').extract()
        for category in categories:
            yield Request(urljoin_rfc(get_base_url(response), category)+"?sz=200&spcl", callback=self.parse_products)

        if not categories:
            categories = hxs.select('//div[@class="rollovers"]/div/a/@href').extract()
            for category in categories:
                yield Request(category, callback=self.parse_view_all_products)
            if not categories:
                yield Request(response.url+"?sz=200&spcl", callback=self.parse_products)


        for cat in hxs.select('//ul[starts-with(@id,"ctl00_ContentPlaceHolder_rptCategories_ctl")]//a/@href').extract():
            yield Request(urljoin_rfc(get_base_url(response), cat), callback=self.parse_view_all_products)

    def parse_product_category(self, response):
        hxs = HtmlXPathSelector(response)
        loader = ProductLoader(item=response.meta['product'], selector=hxs)
        loader.add_xpath('category', '//ol[contains(@class,"breadcrumbs")]/li[position()>1]//a/text()')
        item = loader.load_item()
        reviews_url = 'http://houseoffraser.ugc.bazaarvoice.com/6017-en_gb/%s/reviews.djs?format=embeddedhtml'
        yield Request(reviews_url % item['identifier'], callback=self.parse_review_page, meta={'product': item})
        
    def parse_products(self, response):
        hxs = HtmlXPathSelector(response)
        products = hxs.select('//li[@class="product-list-element"]')
        if products:
            category = hxs.select('//h1[@class="category-heading"]/text()').extract()[0].strip()
            for product in products:
                url = product.select('a/@href').extract()[0]
                price = ''.join(product.select('div//span[@class="price" or @class="price-now"]/text()').extract()).strip()
                price_was = ' '.join(''.join(product.select('div//span[@class="price-was"]/text()').extract()).split())
                brand = ''.join(product.select('div//div[@class="product-description"]/a/h3/text()').extract()).strip()
                if "From" in price:
                    yield Request(url, callback=self.parse_product, meta={'brand':brand, 'category': category})
                else:
                    loader = ProductLoader(item=Product(), selector=product)
                    name = ' '.join(product.select('div//div[@class="product-description"]/a/descendant::*/text()').extract()).strip()
                    loader.add_value('name', name)
                    loader.add_value('sku', url.split('/')[-1].split(',')[0])
                    loader.add_value('identifier', url.split('/')[-1].split(',')[0])
                    loader.add_value('url', url)
                    loader.add_value('brand', brand)
                    loader.add_value('price', price)
                    image_url = product.select('a/img/@src').extract()
                    if image_url:
                        loader.add_value('image_url', image_url[0])
                    item = loader.load_item()

                    metadata = JohnLewisMeta()
                    metadata['promotion'] = price_was
                    metadata['reviews'] = []
                    item['metadata'] = metadata

                    request = Request(item['url'], callback=self.parse_product_category, meta=response.meta)
                    yield self.fetch_product(request, item)

            next = hxs.select('//a[@class="pager nextPage"]/@href').extract()
            if next:
                yield Request(next[0], callback=self.parse_products)
        else:
            sub_categories = hxs.select('//ol[@class="interstitialMenu clearfix"]/li/a/@href').extract()
            if sub_categories:
                for sub_category in sub_categories:
                    url = urljoin_rfc(get_base_url(response), sub_category)
                    yield Request(url, callback=self.parse_products)
            else:
                categories = hxs.select('//*[@id="container"]/div[@class="rollovers"]/div/a/@href').extract()
                for category in categories:
                    yield Request(category, callback=self.parse_view_all_products)

    def parse_view_all_products(self, response):
        hxs = HtmlXPathSelector(response)
        size = hxs.select('//ul[@class="pageSize"]/li/a/@href').extract()
        if size:
            size = size[0].split('&')[-1]
            yield Request(''.join((response.url, '&', size)), callback=self.parse_brands)

    def parse_brands(self, response):
        hxs = HtmlXPathSelector(response)
        brands = hxs.select('//li[contains(strong/text(), "brand")]/ul/li/a')
        for brand in brands:
            brand_name = brand.select('text()').extract()[0].split('(')[0].strip()
            brand_url = brand.select('@href').extract()[0]
            yield Request(urljoin_rfc(get_base_url(response), brand_url), 
                          callback=self.parse_kitchen_products, 
                          meta={'brand': brand_name})

    def parse_kitchen_products(self, response):
        hxs = HtmlXPathSelector(response)
        products = hxs.select('//*[@id="content"]/div[@id!="pageControl"]/div/ul')
        for product in products:
            loader = ProductLoader(item=Product(), selector=product)
            name = ''.join(product.select('li/a/strong/text()').extract()).strip()
            if not name: continue
            loader.add_value('name', name)
            loader.add_value('brand', response.meta.get('brand'))
            url = product.select('li[@class="alignCenter"]/a/@href').extract()
            if url:
                url = urljoin_rfc(get_base_url(response), url[0])
                loader.add_value('url', url)
                sku = url.split('ProductCode=')[-1].split('&')[0]
                loader.add_value('sku', sku)
                loader.add_value('identifier', sku)
                loader.add_value('identifier', response.meta.get('brand'))
                loader.add_xpath('price', 'div[@class="priceBox"]/strong/a/text()')
                loader.add_xpath('category', '//div[@id="categoryHeader"]/h1/text()')
                if loader.get_output_value('price') > 0:
                    loader.add_value('stock', '1')

                image_url = product.select('li/a/img/@src').extract()
                if image_url:
                    loader.add_value('image_url', urljoin_rfc(get_base_url(response), image_url[0]))

                price_was = product.select('div//p//text()').extract()
                price_was = ''.join(price_was[:2]) if price_was else ''
                item = loader.load_item()

                metadata = JohnLewisMeta()
                metadata['promotion'] = price_was
                metadata['reviews'] = []
                item['metadata'] = metadata

                reviews_url = 'http://reviews.houseoffraserkitchenappliances.co.uk/5627hof-en_gb/%s/reviews.htm?format=embedded&reviewID=20782'
                part_number = re.search('ProdColourID=(.*)&', url).group(1)
                yield Request(reviews_url % part_number, callback=self.parse_review_page, meta={'product': item})

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        products = hxs.select('//div[@class="setProduct available" or @class="setProduct available even"]')
        if not products:
            products = hxs.select('//div[@class="setProductRow available" or @class="setProductRow available even"]')
        for product in products:
            loader = ProductLoader(item=Product(), selector=product)
            name = response.meta['brand'] + " " + product.select('div/h5/a/text()').extract()[0].strip()
            url = product.select('div/h5/a/@href').extract()
            if url:
                url = urljoin_rfc(get_base_url(response), url[0])
                sku = product.select('div/input[@class="productID"]/@value').extract()[0]
                loader.add_value('name', name.strip())
                loader.add_value('url', url)
                loader.add_value('brand', response.meta['brand'])
                loader.add_value('category', response.meta['category'])
                loader.add_value('sku', sku)
                loader.add_value('identifier', sku)
                image_url = hxs.select('//img[@class=" featuredProductImage"]/@src').extract()
                if image_url:
                    loader.add_value('image_url', image_url[0])

                price = product.select('div/p[@class="priceNow"]/text()').extract()
                if price:
                    price = price[0]
                else:
                    price = product.select('div/p[@class="price"]/text()').extract()
                    pirce = price[0] if price else 0
                
                loader.add_value('price', price)
                if loader.get_output_value('price') > 0:
                    loader.add_value('stock', '1')

                item = loader.load_item()

                yield item

    def parse_review_page(self, response):
        item_ = response.meta.get('product', '')
        hxs = HtmlXPathSelector(response)
        reviews = hxs.select('//div[@class="BVRRReviewDisplayStyle3"]')
        if not reviews:
            hxs = HtmlXPathSelector(text=self._extract_html(response))
            reviews = hxs.select('//div[@class="BVRRReviewDisplayStyle5"]')

        for review in reviews:
            l = ReviewLoader(item=Review(), response=response, date_format='%m/%d/%Y')
            rating = review.select(".//span[contains(@class,'BVRRRatingNumber')]/text()").extract()[0]
            date = review.select(".//span[contains(@class,'BVRRValue BVRRReviewDate')]/text()").extract()[0]
            review = review.select(".//span[contains(@class,'BVRRReviewText')]/text()")
            try:
                review = review[1].extract()
            except:
                review = review[0].extract()

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

    def _extract_html(self, response):
        review_html = ''
        for line in response.body.split('\n'):
            if 'var materials=' in line:
                review_html = line.split('"BVRRSecondaryRatingSummarySourceID":" ')[-1].split('\n}')[0].replace('\\', '')
        return review_html
