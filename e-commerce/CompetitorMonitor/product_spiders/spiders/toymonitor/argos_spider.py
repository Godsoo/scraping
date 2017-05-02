import os
import xlrd
import re
import json
import datetime

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.utils.url import add_or_replace_parameter
from urlparse import urljoin, urlparse
from scrapy import log

from product_spiders.items import (Product,
                                   ProductLoaderWithNameStrip as ProductLoader)
from product_spiders.utils import fix_spaces
from toymonitoritems import ToyMonitorMeta, Review, ReviewLoader
from brands import BrandSelector
from lib.schema import SpiderSchema
HERE = os.path.abspath(os.path.dirname(__file__))


class ArgosCoUKSpider(BaseSpider):
    name = 'toymonitor-argos.co.uk'
    allowed_domains = ['argos.co.uk', 'argos.scene7.com', 'api.bazaarvoice.com']
    start_urls = ('http://www.argos.co.uk/static/Browse/25051/33006252/c_1/1|category_root|Toys|33006252.htm',)
    _webapp_url = 'http://www.argos.co.uk/webapp/wcs/stores/servlet/Browse?s=Relevance&storeId=10151&langId=110&catalogId=25051&mRR=true'
    errors = []
    brand_selector = BrandSelector(errors)
    #field_modifiers = {'brand': brand_selector.get_brand}

    def __parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        file_path = HERE + '/Brandstomonitor.xlsx'
        wb = xlrd.open_workbook(file_path)
        sh = wb.sheet_by_index(0)

        self._brands_to_monitor = []
        for rownum in xrange(sh.nrows):
            if rownum < 1:
                continue
            row = sh.row_values(rownum)
            self._brands_to_monitor.append(row[0].strip())

##        site_brands = hxs.select('//div[@id="atoz"]/dl/dd/a')
##        for brand in site_brands:
##            brand_name = brand.select('text()').extract()[0].strip()
##            brand_url = brand.select('@href').extract()[0]
##            if brand_name.upper().strip() in brands_to_monitor:
##                brand_url = urljoin_rfc(base_url, brand_url)
##                yield Request(brand_url, callback=self.parse_brand, meta={'brand': brand_name})

        yield Request(response.url, callback=self.parse_category)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        for sub_cat in response.xpath('//ul[@id="categoryList"]//a/@href').extract():
            yield Request(response.urljoin(sub_cat), callback=self.parse_products)

    def parse_subcategory(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        lego = False
        for sub_cat in hxs.select('//ul[@id="categoryList"]//a/@href').extract():
            yield Request(urljoin(base_url, sub_cat), callback=self.parse_subcategory)

        categories = urlparse(response.url).path
        if "Lego" in categories.title():
            lego = True
        categories = re.findall('(c_\d.+?)[/.]', categories)
        cat_url = self._webapp_url
        for category in categories:
            cat_url += '&' + category.replace('/', '=')


        site_brands = hxs.select('//div[@id="Brands-refinement"]//label')
        brands = set()
        for brand in self._brands_to_monitor:
            for site_brand in site_brands:
                brand_name = fix_spaces(site_brand.select('span/text()').extract()[0])
                try:
                    brand_name = fix_spaces(re.findall('(.*)\(', brand_name)[0])
                except IndexError:
                    brand_name = fix_spaces(brand_name)
                if lego:
                    brands.add((brand_name, site_brand))
                elif brand.upper() == brand_name.upper():
                    brands.add((brand_name, site_brand))
            if lego:
                break
        for brand_name, brand_sel in brands:
            brand_url = brand_sel.select('.//@value').extract()[0].replace(' ', '+')
            url = cat_url + '&r_001=' + brand_url.replace('&', '%26')
            yield Request(url, callback=self.parse_products, meta = {'brand':brand_name})

    def parse_brand(self, response):
        try:
            hxs = HtmlXPathSelector(response)
        except:
            return
        base_url = get_base_url(response)

        products = hxs.select('//div[@class="content"]//div[@id="products"]')
        brand_links = hxs.select('//div[@id="staticcontent"]//a/@href').extract()
        product = hxs.select('//div[@id="pdpDetails"]')
        if products:
            for item in self.parse_products(response):
                yield item
        elif brand_links:
            for url in brand_links:
                yield Request(urljoin(base_url, url), meta=response.meta, callback=self.parse_brand)
        elif product:
            for item in self.parse_product(response):
                yield item

    def parse_products(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        for url in response.xpath('//div[@id="categories"]//@href').extract():
            yield Request(response.urljoin(url), meta=response.meta, callback=self.parse_products)

        # parse pages
        pages = response.css('.page ::attr(href)').extract()
        for page in pages:
            yield Request(page, meta=response.meta, callback=self.parse_products)

        # parse products
        items = response.xpath("//div[@id='products']/ul/li[contains(@class, 'item')]/dl")
        if not items:
            items = hxs.select('//dl[@class="product noquickview"]')
        for item in items:
            url = item.select('dt[@class="title"]/a/@href').extract()
            if not url:
                self.log("ERROR! NO URL! URL: %s." % (response.url,))
                continue
            url = urljoin(base_url, url[0])

            yield Request(url, callback=self.parse_product, meta=response.meta)


    def parse_product(self, response):
        pdata = SpiderSchema(response).get_product()
        hxs = HtmlXPathSelector(response)

        url = response.url
        l = ProductLoader(item=Product(), response=response)

        name = pdata['name']

        l.add_value('name', name)

        l.add_value('sku', pdata['sku'])

        l.add_value('category', SpiderSchema(response).get_category())

        product_image = response.css('li.active a img::attr(src)').extract_first()
        if product_image:
            l.add_value('image_url', response.urljoin(product_image))

        brand = response.css('.pdp-view-brand-main ::text').extract_first()
        l.add_value('url', url)
        l.add_value('price', pdata['offers']['properties']['price'])
        l.add_value('brand', response.meta.get('brand', brand))
        identifier = response.xpath('//form/input[@name="productId"]/@value').extract_first()
        if not identifier:
            self.log('No identifier found on %s' %response.url)
            return
        l.add_value('identifier', identifier)
        item = l.load_item()

        promotions = response.xpath('//li[@class="pricesale"]/text()').extract()
        promotions += response.xpath('//div[@class="special-offers"]/p/text()').extract()
        promotions = [x.strip() for x in promotions]
        promotions = u' * '.join(promotions)

        metadata = ToyMonitorMeta()
        ean = hxs.select('//li[contains(text(), "EAN")]/text()').re("EAN: ([0-9]+)")
        if ean:
            metadata['ean'] = ean[0]
        metadata['reviews'] = []
        item['metadata'] = metadata
        item['metadata']['promotions'] = promotions

        part_number = response.xpath('//form/input[@name="partNumber"]/@value').extract_first()

        if pdata.get('aggregateRating'):
            review_url = ("http://api.bazaarvoice.com/data/reviews.json?Callback=jQuery111206106209812916942_1465931826753"
                            "&apiversion=5.4&passkey=q3mz09yipfffc2yhguids3abz&locale=en_GB&Filter=ProductId:%s"
                            "&Filter=IsRatingsOnly:false&Include=Products&Stats=Reviews&Limit=100&Offset=0&Sort=SubmissionTime:Desc"
                            "&_=1465931826756") % (part_number)
            req = Request(review_url, meta={'item': item, 'offset': 0},
                            callback=self.parse_reviews)
            yield req
        else:
            yield item

    def parse_image(self, response):
        item = response.meta['item']
        image_url = re.findall('"img_set","n":"(.*)","item', response.body)
        if image_url:
            image_url = 'http://argos.scene7.com/is/image/' + image_url[0]
            item['image_url'] = image_url

        if response.meta['has_reviews']:
            part_number = response.meta['part_number']
            review_url = ("http://api.bazaarvoice.com/data/reviews.json?Callback=jQuery111206106209812916942_1465931826753"
                          "&apiversion=5.4&passkey=q3mz09yipfffc2yhguids3abz&locale=en_GB&Filter=ProductId:%s"
                          "&Filter=IsRatingsOnly:false&Include=Products&Stats=Reviews&Limit=100&Offset=0&Sort=SubmissionTime:Desc"
                          "&_=1465931826756") % (part_number)
            req = Request(review_url, meta={'item': item, 'offset': 0},
                          callback=self.parse_reviews)
            yield req
        else:
            yield item

    def parse_reviews(self, response):
        item = response.meta['item']
        body = response.body.strip().partition('(')[-1].replace('});', '}').replace('})', '}')
        json_body = json.loads(body)

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


            review_loader.add_value('full_text', unicode(full_text, errors='ignore'))
            rating = review['Rating']
            review_loader.add_value('rating', rating)
            review_loader.add_value('url', item['url'])

            item['metadata']['reviews'].append(review_loader.load_item())

        if len(reviews) == 100:
            offset = response.meta['offset'] + 100

            next_reviews = add_or_replace_parameter(response.url, 'Offset', str(offset))
            req = Request(next_reviews, meta={'item': item, 'offset': offset}, callback=self.parse_reviews)
            yield req
        else:
            yield item
