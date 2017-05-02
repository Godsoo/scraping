import time
import re

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc
from urllib import urlencode

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from keteritems import KeterMeta, Review, ReviewLoader


class SamsclubSpider(BaseSpider):
    name = "keter-samsclub.com"
    allowed_domains = ['samsclub.com',
                       'samsclub.ugc.bazaarvoice.com']

    start_urls = ['http://samsclub.com']

    def start_requests(self):
        start_urls = [
            # ('keter', 'http://www.samsclub.com/sams/search/searchResults.jsp?searchCategoryId=all&searchTerm=Keter&noOfRecordsPerPage=80'),
            ('suncast', 'http://www.samsclub.com/sams/shop/common/ajaxSearchPageLazyLoad.jsp?sortKey=relevance&searchCategoryId=all&searchTerm=SUNCAST&noOfRecordsPerPage=10000&sortOrder=0&offset=0&rootDimension=0&selectedFilter=null&pageView=list&_=1380666832327'),
            ('rubbermaid', 'http://www.samsclub.com/sams/shop/common/ajaxSearchPageLazyLoad.jsp?sortKey=relevance&searchCategoryId=all&searchTerm=RUBBERMAID&noOfRecordsPerPage=10000&sortOrder=0&offset=0&rootDimension=0&selectedFilter=null&pageView=list&_=1380666832327'),
            ('lifetime', 'http://www.samsclub.com/sams/shop/common/ajaxSearchPageLazyLoad.jsp?sortKey=relevance&searchCategoryId=all&searchTerm=LIFETIME&noOfRecordsPerPage=10000&sortOrder=0&offset=0&rootDimension=0&selectedFilter=null&pageView=list&_=1380666832327'),
            ('step2', 'http://www.samsclub.com/sams/shop/common/ajaxSearchPageLazyLoad.jsp?sortKey=relevance&searchCategoryId=all&searchTerm=STEP2&noOfRecordsPerPage=10000&sortOrder=0&offset=0&rootDimension=0&selectedFilter=null&pageView=list&_=1380666832327'),
            ('sterilite', 'http://www.samsclub.com/sams/shop/common/ajaxSearchPageLazyLoad.jsp?sortKey=relevance&searchCategoryId=all&searchTerm=STERILITE&noOfRecordsPerPage=10000&sortOrder=0&offset=0&rootDimension=0&selectedFilter=null&pageView=list&_=1380666832327'),
            ('lifetime', 'http://www.samsclub.com/sams/shop/common/ajaxSearchPageLazyLoad.jsp?sortKey=relevance&searchCategoryId=all&searchTerm=LIFETIME&noOfRecordsPerPage=10000&sortOrder=0&offset=0&rootDimension=4294959983&selectedFilter=null&pageView=list&_=1380666832327'),
        ]

        specific_products = [
            ('keter', [
                'http://www.samsclub.com/sams/search/searchResults.jsp?searchCategoryId=all&searchTerm=KETER 832342&noOfRecordsPerPage=80',
                'http://www.samsclub.com/sams/search/searchResults.jsp?searchCategoryId=all&searchTerm=KETER 17182239&noOfRecordsPerPage=80',
                'http://www.samsclub.com/sams/search/searchResults.jsp?searchCategoryId=all&searchTerm=KETER 17190650&noOfRecordsPerPage=80',
                'http://www.samsclub.com/sams/search/searchResults.jsp?searchCategoryId=all&searchTerm=KETER 17197108&noOfRecordsPerPage=80',
                'http://www.samsclub.com/sams/150-gal-deck-box/prod8340178.ip?navAction=',
                'http://www.samsclub.com/sams/orion-resin-storage-shed/prod5780148.ip?navAction=',
                'http://www.samsclub.com/sams/2pk-keter-chaise-rattan-lounger/prod9590065.ip?navAction=']
             )]

        for brand, url in start_urls:
            yield Request(url, meta={'brand': brand})

        for brand, specific_urls in specific_products:
            for url in specific_urls:
                yield Request(url, meta={'brand': brand}, callback=self.parse_product)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        products = hxs.select('//div[contains(@class, "prodTitle")]/h4/a/@href').extract()

        for url in products:
            yield Request(urljoin_rfc(base_url, url),
                          callback=self.parse_product,
                          meta=response.meta)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        name = hxs.select('//div/h1/span[@itemprop="name"]/text()').extract()
        brand = response.meta['brand'].strip().lower()

        if name and brand and self._check_brand(name[0], brand):
            name = name[0]
        else:
            return

        price = hxs.select('//span[@class="leftVal  onlinePrice"]/text()').extract()
        if not price:
            price = hxs.select('//span[@class="leftVal"]/text()').extract()

        loader = ProductLoader(item=Product(), selector=hxs)

        loader.add_value('url', response.url)
        loader.add_xpath('identifier', '//input[@name="/atg/commerce/order/purchase/CartModifierFormHandler.baseProductId"]/@value')
        loader.add_value('name', name)
        loader.add_xpath('sku', '//div/div/span[@itemprop="model"]/text()')
        loader.add_xpath('image_url', '//div/div/div[@id="plImageHolder"]/img/@src')
        loader.add_xpath('category', '(//div[@id="breadcrumb"]/span/a)[last()]/text()')
        loader.add_value('price', price[0] if price else 0)
        loader.add_value('brand', brand)

        reviews_url = u'http://samsclub.ugc.bazaarvoice.com/1337/%s/reviews.djs?format=embeddedhtml'

        product = loader.load_item()

        metadata = KeterMeta()
        metadata['brand'] = response.meta['brand'].strip().lower()
        metadata['reviews'] = []
        product['metadata'] = metadata

        try:
            prod_id = hxs.select('//form//input[contains(@name, "productId")]/@value').extract()[0]

            yield Request(reviews_url % prod_id,
                          meta={'product': product,
                                'product_url': response.url,
                                'reviews_url': reviews_url % prod_id},
                          callback=self.parse_review)
        except:
            yield product

    def parse_review(self, response):

        html = re.search('var materials={.*?(<div.*?)"},.initializers', response.body, re.DOTALL).group(1)
        html = re.sub(r'\\n', r'\n', html)
        html = re.sub(r'\\(.)', r'\1', html)

        hxs = HtmlXPathSelector(text=html)

        reviews = hxs.select(u'//div[starts-with(@id, "BVRRDisplayContentReviewID_")]')
        product = response.meta['product']

        if not reviews:
            yield product
            return

        for review in reviews:
            loader = ReviewLoader(item=Review(), selector=review, date_format=u'%d/%m/%Y')

            date = review.select(u'.//span[@class="BVRRValue BVRRReviewDate"]/text()').extract()[0]
            date = time.strptime(date, u'%B %d, %Y')
            date = time.strftime(u'%d/%m/%Y', date)

            loader.add_value('date', date)

            title = review.select(u'.//span[@class="BVRRValue BVRRReviewTitle"]/text()').extract()
            if not title:
                title = u'Untitled'
            else:
                title = title[0]
            text = review.select(u'.//span[@class="BVRRReviewText"]/text()').extract()
            if text:
                text = text[0]
            else:
                text = u'No text supplied.'
            loader.add_value('full_text', u'%s\n%s' % (title, text))
            loader.add_value('url', response.meta['product_url'])
            loader.add_xpath('rating', u'.//div[@id="BVRRRatingOverall_Review_Display"]//span[@class="BVRRNumber BVRRRatingNumber"]/text()')
            product['metadata']['reviews'].append(loader.load_item())

        cur_page = hxs.select(u'//span[@class="BVRRPageLink BVRRPageNumber BVRRSelectedPageNumber"]/text()').extract()
        if not cur_page:
            yield product
            return
        else:
            cur_page = int(cur_page[0])

        if 'last_page' not in response.meta:
            response.meta['last_page'] = int(hxs.select(u'//span[@class="BVRRPageLink BVRRPageNumber"]/a/text()').extract()[-1])

        if cur_page < response.meta['last_page']:
            url = response.meta['reviews_url'] + u'&page=%s' % str(cur_page + 1)
            yield Request(url, meta=response.meta, callback=self.parse_review)
        else:
            yield product

    def _preprocess_link(self, base_url, href):
        if 'javascript: checkIsProductsSelected' in href:
            href = href.split("'")[1]
        return urljoin_rfc(base_url, href)

    def _check_brand(self, name, brand):
        return (brand.lower() in name.lower()) \
            or (brand.lower() == 'keter') \
            or (brand.lower() == 'keter' and ('lifetime' not in name.lower())) \
            or (brand.lower() == 'suncast' and  "hybrid shed" in name.lower())\
            or (brand.lower() == 'step2')
