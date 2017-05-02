import os
import json
import xlrd
import datetime
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.url import urljoin_rfc, add_or_replace_parameter
from scrapy.utils.response import get_base_url
from urlparse import urljoin
from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader
import re
from product_spiders.utils import fix_spaces
from brands import BrandSelector

from toymonitoritems import Review, ReviewLoader, ToyMonitorMeta


HERE = os.path.abspath(os.path.dirname(__file__))


class ASDAcomSpider(BaseSpider):
    name = u'toymonitor-asdacom.com'
    allowed_domains = [u'direct.asda.com', 'api.bazaarvoice.com']
    start_urls = [
        u'http://direct.asda.com/george/kids-toys-landing,default,pg.html'
    ]

    user_agent = "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:40.0) Gecko/20100101 Firefox/40.0"
    errors = []
    brand_selector = BrandSelector(errors)
    #field_modifiers = {'brand': brand_selector.get_brand}

    def __start_requests(self):
        file_path = HERE + '/Brandstomonitor.xlsx'
        wb = xlrd.open_workbook(file_path)
        sh = wb.sheet_by_index(0)

        self._brands_to_monitor = []
        for rownum in xrange(sh.nrows):
            if rownum < 1:
                continue
            row = sh.row_values(rownum)
            self._brands_to_monitor.append(row[0].strip().upper())

        for url in self.start_urls:
            yield Request(url, callback=self.parse)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        categories = response.xpath('//div[text()="Toys"]/following-sibling::a/@href').extract()
        categories += response.xpath('//div[text()="Outdoor Toys"]/following-sibling::a/@href').extract()
        categories += response.xpath('//div[text()="Toys By Age"]/following-sibling::a/@href').extract()
        for category_url in categories:
            yield Request(category_url, callback=self.parse_search)

    def parse_search(self, response):
        hxs = HtmlXPathSelector(response)
        products = hxs.select('//div[@id="primary"]//div[@class="productImg"]')
        for p in products:
            promotions = p.xpath('.//span[@class="square_promo_badge"]/span/text()').extract()
            url = p.xpath('./a/@href')[0].extract()
            yield Request(url, callback=self.parse_product, meta={'promotions': promotions[0] if promotions else u''})

        prod_count = hxs.select('//span[@class="pagingcount"]/text()').re("[0-9]+")
        if prod_count:
            for page in range(1, int(prod_count.pop())/20+1):
                yield Request(add_or_replace_parameter(response.url, 'start', page * 20), callback=self.parse_search)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        brand = hxs.select('//td[normalize-space(text())="Brand"]/../td[2]/text()').extract_first()
        product_url = urljoin(base_url, response.url)

        name = hxs.select('//h1[@id="productName"]/text()').extract()
        if not name:
            name = hxs.select('//div[@class="product-name"]/text()').extract()
        if not name:
            name = hxs.select('//h1[@class="product-name"]/text()').extract()

        image = hxs.select('//img[@id="prodImg"]/@src').extract() or hxs.select('//img[@class="singleImage"]/@src').extract()
        image_url = urljoin(base_url, image[0]) if image else ''

        breadcrumb = hxs.select('//ol[@id="navBreadcrumbs"]/li/h2//a/text()').extract()
        if len(breadcrumb) > 0:
            category = breadcrumb.pop().strip()
        else:
            category = None

        if hxs.select('//input[@id="item_available"][@value="InStock"]').extract():
            stock = None
        else:
            stock = 0

        price = hxs.select('//div[@class="producttop"]//span[@class="productPrice"]/span[@class="pounds" or @class="newPrice"]/text()[last()]').extract() or hxs.select('//meta[@itemprop="price"]/@content').extract()
        if price:
            price = price.pop()
        else:
            price = '0.00'
        try:
            sku = hxs.select('//td[contains(text(), "Model Number")]/../td[@class="value"]/text()').extract()[0].strip()
        except IndexError:
            sku = ''

        loader = ProductLoader(response=response, item=Product())
        loader.add_value('url', product_url)
        loader.add_value('name', name)
        loader.add_value('image_url', image_url)
        loader.add_value('price', price.replace(' ', '').replace(',', '.'))
        loader.add_value('category', category)
        loader.add_value('sku', sku)
        loader.add_value('brand', brand)
        loader.add_xpath('identifier', '//input[@id="product_sku_string"]/@value')

        if stock == 0:
            loader.add_value('stock', 0)

        item =  loader.load_item()

        metadata = ToyMonitorMeta()
        metadata['reviews'] = []
        item['metadata'] = metadata
        if response.meta.get('promotions', ''):
            item['metadata']['promotions'] = response.meta.get('promotions', '')

        review_data = re.findall('app.reviewsQnAModel = (.*);', response.body)
        if review_data:
            review_data = json.loads(review_data[0])
            review_url = 'http:' + review_data['bvAPICallURL']
            review_url = add_or_replace_parameter(review_url, 'limit', '100')
            req = Request(review_url, meta={'item': item, 'offset': '0'}, callback=self.parse_reviews)
            yield req
        else:
            yield item

    def parse_reviews(self, response):
        item = response.meta['item']
        json_body = json.loads(response.body)

        reviews = json_body['Results']
        for review in reviews:
            review_loader = ReviewLoader(item=Review(), response=response, date_format="%B %d, %Y")
            review_date = datetime.datetime.strptime(review['SubmissionTime'].split('.')[0], '%Y-%m-%dT%H:%M:%S')
            review_loader.add_value('date', review_date.strftime("%B %d, %Y"))

            title = review['Title'] if review['Title'] else ''
            text = review['ReviewText'] if review['ReviewText'] else ''
         
            if title:
                full_text = title.encode('utf-8') + '\n' + text.encode('utf-8')
            else:
                full_text = text.encode('utf-8')

            pros = review['Pros']
            cons = review['Cons']
            if pros:
                full_text += '\nPros: ' + ', '.join(pros.encode('utf-8'))
            if cons:
                full_text += '\nCons: ' + ', '.join(cons.encode('utf-8'))

            try:
                review_loader.add_value('full_text', unicode(full_text, errors='ignore'))
            except UnicodeDecodeError:
               self.log('XXXXXXXXXXXXXXXXXXXXXXX')
               self.log(response.url)
               self.log(item['url'])
               self.log(title)
               self.log(text)
               self.log(str(full_text))
               self.log('XXXXXXXXXXXXXXXXXXXXXXX')
            rating = review['Rating']
            review_loader.add_value('rating', rating)
            review_loader.add_value('url', item['url'])

            item['metadata']['reviews'].append(review_loader.load_item())

        if len(reviews) == 100:
            offset = response.meta['offset'] + 100

            next_review_url = add_or_replace_parameter(response.url, 'offset', str(offset))
            req = Request(next_review_url, meta={'item': item, 'offset': offset},
                          callback=self.parse_reviews)
            yield req
        else:
            yield item
