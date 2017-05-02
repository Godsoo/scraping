import os
import xlrd
from urllib import quote
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.linkextractors import LinkExtractor
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.contrib.loader.processor import TakeFirst, Join, Compose
from urlparse import urljoin
from scrapy.utils.url import urljoin_rfc
from product_spiders.items import Product, ProductLoader
from brands import BrandSelector
from toymonitoritems import ToyMonitorMeta, Review, ReviewLoader

from scrapy import log
import re

HERE = os.path.abspath(os.path.dirname(__file__))

from product_spiders.spiders.BeautifulSoup import BeautifulSoup

class HamleysSpider(BaseSpider):
    name = u'toymonitor-hamleys.com'
    allowed_domains = [u'www.hamleys.com', u'hamleys.com']
    start_urls = [u'http://www.hamleys.com/']
    user_agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.10; rv:37.0) Gecko/20100101 Firefox/37.0'
    download_delay = 0.5
    errors = []
    brand_selector = BrandSelector(errors)
    #field_modifiers = {'brand': brand_selector.get_brand}
    promos = {'indicator4for20': u'4 for \xa320',
              'indicator2for20': u'4 for \xa320',
              'indicator3for2': u'3 for 2',
              'save1': 'SAVE',
              }

    def ____init__(self, *args, **kwargs):
        super(HamleysSpider, self).__init__(*args, **kwargs)
        file_path = HERE + '/Brandstomonitor.xlsx'
        wb = xlrd.open_workbook(file_path)
        sh = wb.sheet_by_index(0)

        self.brands_to_monitor = []
        for rownum in xrange(sh.nrows):
            if rownum < 1:
                continue
            row = sh.row_values(rownum)
            self.brands_to_monitor.append(row[0].upper().strip())

    def retry(self, response, error="", retries=7):
        meta = response.meta.copy()
        retry = int(meta.get('retry', 0))
        if 'redirect_urls' in meta and meta['redirect_urls']:
            url = meta['redirect_urls']
        else:
            url = response.request.url
        if retry < retries:
            retry = retry + 1
            meta['retry'] = retry
            meta['recache'] = True
            return Request(url, dont_filter=True, meta=meta, callback=response.request.callback)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        categories = LinkExtractor(restrict_css=(
            '.Soft-Toys',
            '.Arts-\&-Crafts',
            '.Dolls',
            '.Build-It',
            '.Action-Toys',
            '.Games'
            )).extract_links(response)
        for category in categories:
            if category.url == 'index.jsp':
                continue
            yield Request(category.url, callback=self.parse_categories)

    def parse_categories(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        if hxs.select('//div[@class="detailPageTitle"][text()="Viewing 0"]'):
            req = self.retry(response)
            if req:
                yield req
            return

        site_brands = hxs.select('//div[@id="refinceBrands"]/div/ul/li/a')
        for brand in site_brands:
            brand_name = brand.select('text()').extract()[0].split("(")[0].strip()
            brand_url = brand.select('@href').extract()[0]
            brand_url = urljoin_rfc(base_url, brand_url)
            yield Request(brand_url, callback=self.parse_brand, meta={'brand': brand_name})
        if not site_brands:
            request = self.retry(response, "Brands not found " + response.url)
            if request:
                    yield request

    def parse_brand(self, response):
        hxs = HtmlXPathSelector(response)
        # if nothing found try to reload page
        if hxs.select('//div[@class="detailPageTitle"][text()="Viewing 0"]'):
            req = self.retry(response)
            if req:
                yield req
            return

        soup = BeautifulSoup(response.body)

        products = hxs.select('//ul[@class="stockthumbwrapper"]')
        for p in products:
            url = p.xpath('.//li[@class="productThumbName"]/a/@href')[0].extract()
            meta = response.meta.copy()
            promo = p.xpath('.//li[@class="productThumbImage"]//img[contains(@class,"cornerImgFormat2 discount")]/@alt').extract()
            meta['promotions'] = promo[0] if promo else ''
            yield Request(urljoin(get_base_url(response), url), callback=self.parse_product, meta=response.meta)

        for p in soup.findAll('ul', 'stockthumbwrapper'):
            url = p.find('li', 'productThumbName').find('a')['href']
            meta = response.meta.copy()
            promo = p.find('li', 'productThumbImage').find('img', attrs={'class': re.compile('cornerImgFormat2 discount')})
            meta['promotions'] = promo['alt'] if promo else ''
            yield Request(urljoin(get_base_url(response), url), callback=self.parse_product, meta=meta)

        pages = soup.findAll('div', id='pagenumber')
        if pages:
            for page in set(pages[0].findAll('a')):
                yield Request(response.urljoin(page), meta=response.meta, callback=self.parse_brand)

        for page in set(hxs.select('//div[@id="pagenumber"][1]/a/@href').extract()):
            yield Request(response.urljoin(page), meta=response.meta, callback=self.parse_brand)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        try:
            name = hxs.select('//*[@itemprop="name"]/text()').extract().pop().strip()
        except IndexError:
            yield Request(response.url.replace('hamleys.com/', 'hamleys.com/detail.jsp?pName=').replace('.ir', ''), callback=self.parse_product)
            return

        out_of_stock = 'OUT OF STOCK' in ''.join(hxs.select('//li[@class="stockStatus"]/span/text()').extract()).upper()
        price = "".join(hxs.select('//div[@class="productprice "]/text()').re("([.0-9]+)") or hxs.select('//div[@class="productprice "]/span[@class="detailOurPrice"]/text()').re("([.0-9]+)"))

        loader = ProductLoader(response=response, item=Product())
        loader.add_value('url', urljoin(base_url, response.url))
        loader.add_value('name', name)
        loader.add_xpath('image_url', '//img[@class="productMain"]/@src', TakeFirst())
        loader.add_value('price', price)
        category = hxs.select('//div[@class="pagetopnav"]/ul[contains(@class, "crumb")]/li/a/text()').extract()[-2]
        loader.add_value('category', category)
        loader.add_value('sku', name, re=' (\d\d\d+)\s*$')
        loader.add_value('brand', response.meta.get('brand', ''))
        identifier = hxs.select('//*[@itemprop="productID"]/text()').extract()[0].replace('Code: ', '')
        loader.add_value('identifier', identifier)

        if out_of_stock:
            loader.add_value('stock', 0)

        item = loader.load_item()

        metadata = ToyMonitorMeta()
        promotions = response.meta.get('promotions', '')
        metadata['reviews'] = []
        item['metadata'] = metadata
        if promotions:
            item['metadata']['promotions'] = self.promos.get(promotions, promotions)

        reviews = hxs.select('//div[@class="reviewbody"]')

        prod_id = response.xpath('//input[@name="id"]/@value').extract()[0]
        has_reviews = response.xpath('//a[@class="writeReviewLink" and contains(@onclick, "'+prod_id+'")]').extract()
        if has_reviews:
            for review in reviews:
                review_loader = ReviewLoader(item=Review(), response=response, date_format="%B %d, %Y")
                #review_date = datetime.datetime.strptime(review['SubmissionTime'].split('.')[0], '%Y-%m-%dT%H:%M:%S')
                #review_loader.add_value('date', review_date.strftime("%B %d, %Y"))

                title = ''.join(review.select('.//div[@class="reviewTagLine"]/text()').extract())
                text = ''.join(review.select('.//div[@class="reviewText"]/text()').extract())
         
                if title:
                    full_text = title.encode('utf-8') + '\n' + text.encode('utf-8')
                else:
                    full_text = text.encode('utf-8')

                review_loader.add_value('full_text', unicode(full_text, errors='ignore'))
                rating = float(review.select('.//div[@class="reviewStarsInner"]/@style').re('\d+.\d+')[0])/20
                review_loader.add_value('rating', rating)
                review_loader.add_value('url', item['url'])

                item['metadata']['reviews'].append(review_loader.load_item())
            yield item
