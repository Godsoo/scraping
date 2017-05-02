import os
import re
import xlrd
from datetime import datetime

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse, FormRequest
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

from product_spiders.items import (
    Product,
    ProductLoaderWithNameStrip as ProductLoader,
)

from toymonitoritems import ToyMonitorMeta, Review, ReviewLoader
from brands import BrandSelector

HERE = os.path.abspath(os.path.dirname(__file__))


class JohnLewisSpider(BaseSpider):
    name = 'toymonitor-johnlewis.com'
    allowed_domains = ['johnlewis.com', 'johnlewis.ugc.bazaarvoice.com']
    start_urls = ['http://www.johnlewis.com/browse/toys/toys/toys-by-brand/_/N-fev',
                  'http://www.johnlewis.com/toys/toys-by-type/c60000243?rdr=1']
    errors = []
    brand_selector = BrandSelector(errors)
    #field_modifiers = {'brand': brand_selector.get_brand}

    def start_requests(self):
        country_url = "http://www.johnlewis.com/store/international/ajax/changeCountryAjaxRequest.jsp"
        formdata = {'country': 'GB',
                    'sourceUrl': 'http://www.johnlewis.com/',
                    'switchToggle': 'Change Country Overlay'}
        yield FormRequest(country_url, formdata=formdata, callback=self.parse_country)

    def parse_country(self, response):
        for url in self.start_urls:
            yield Request(url)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        
        site_brands = response.xpath('//section[@id="facet-brand"]/div/ul/li/a')

        for brand in site_brands:
            brand_name = brand.select('text()').extract()[0].split("(")[0].strip()
            brand_url = brand.select('@href').extract()[0]
            brand_url = urljoin_rfc(base_url, brand_url)
            yield Request(brand_url, callback=self.parse_brand)
        
        if response.meta.get('subcategory'):
            return
        
        subcats = response.xpath('//strong[contains(., "Featured Toy Types")]/following-sibling::ul//@href').extract()
        subcats += response.xpath('//section[@id="facet-toysbytype"]/div/ul/li/a/@href').extract()
        subcats += response.xpath('//header[contains(h2, "Toys by Type")]/following-sibling::div//@href').extract()
        subcats.append('http://www.johnlewis.com/browse/toys/toys/toys-by-type/games-puzzles/view-all-games-puzzles/_/N-6hxe')
        for url in subcats:
            yield Request(response.urljoin(url), meta={'subcategory': True})        

    def parse_brand(self, response):

        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        products = hxs.select("//div[@class='products']/div/article//a[@class='product-link'][1]/@href").extract()
        products += response.meta.get('products', [])

        next_page = filter(lambda link: link != '#', hxs.select('//li[@class="next"]//a/@href').extract())

        if next_page:
            self.log('PARTIAL => %s products found' % len(products))
            yield Request(url=urljoin_rfc(base_url, next_page[0]), meta={'products': list(products)}, callback=self.parse_brand)
        else:
            self.log('TOTAL PRODUCTS FOUND: %s' % len(products))
            products = set(products)
            self.log('TOTAL UNIQUE PRODUCTS URLS: %s' % len(products))
            for url in products:
                yield Request(urljoin_rfc(base_url, url), self.parse_product)


    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        name = hxs.select('normalize-space(//*[@itemprop="name"]/text())').extract()[0]

        brand = hxs.select('normalize-space(//*[@itemprop="brand"]/span/text())').extract()

        try:
            image_url = urljoin_rfc(base_url,
                                    hxs.select('//div[@id="prod-media-player"]'
                                               '//img/@src').extract()[0].strip())
        except IndexError:
            image_url = ''

        options = hxs.select('//div[@id="prod-multi-product-types"]')

        items = []
        if options:
            products = options.select('.//div[@class="product-type"]')
            for product in products:
                opt_name = product.select('.//h3/text()').extract()[0].strip()
                try:
                    stock = product.select('//div[contains(@class, "mod-stock-availability")]'
                                           '//p/strong/text()').re(r'\d+')[0]
                except IndexError:
                    stock = 0

                loader = ProductLoader(item=Product(), selector=product)
                sku = hxs.select(u'//div[@id="prod-info-tab"]//dl/dt[contains(text(),"Model name")]/following-sibling::dd/text()').extract()
                if not sku:
                    sku = hxs.select(u'//div[@id="prod-info-tab"]//dl/dt[contains(text(),"Model Number")]/following-sibling::dd/text()').extract()
                if sku:
                    loader.add_value('sku', sku[0].strip())
                loader.add_xpath('identifier', './/div[contains(@class, "mod-product-code")]/p/text()')
                loader.add_value('name', '%s %s' % (name, opt_name))
                loader.add_xpath('category', '//div[@id="breadcrumbs"]//li[@class="last"]/a/text()')
                loader.add_value('image_url', image_url)
                loader.add_value('brand', brand)
                loader.add_value('url', response.url)
                loader.add_xpath('price', './/p[@class="price"]/strong/text()')
                loader.add_value('stock', stock)
                item = loader.load_item()
                metadata = ToyMonitorMeta()
                metadata['reviews'] = []
                item['metadata'] = metadata
                items.append(item)
        else:
            price = ''.join(hxs.select('//ul/li/strong[@class="price"]/text()').extract()).strip()
            if not price:
                price = ''.join(hxs.select('//span[@class="now-price"]/text()').extract()).split()
                if not price:
                    price = ''.join(hxs.select('//div[@id="prod-price"]//strong/text()').extract()).split()

            try:
                stock = hxs.select('//div[contains(@class, "mod-stock-availability")]'
                                   '//p/strong/text()').re(r'\d+')[0]
            except IndexError:
                stock = 0

            loader = ProductLoader(item=Product(), response=response)
            sku = hxs.select(u'//div[@id="prod-product-code"]//h2[contains(text(),"Product code")]/following-sibling::p/text()').extract()
            if sku:
                loader.add_value('sku', sku[0].strip())
            loader.add_xpath('identifier', '//div[@id="prod-product-code"]/p/text()')
            loader.add_value('name', name)
            loader.add_xpath('category', '//div[@id="breadcrumbs"]//li[@class="last"]/a/text()')
            loader.add_value('image_url', image_url)
            loader.add_value('brand', brand)
            loader.add_value('url', response.url)
            loader.add_value('price', price)
            loader.add_value('stock', stock)

            item = loader.load_item()
            metadata = ToyMonitorMeta()
            metadata['reviews'] = []
            item['metadata'] = metadata

            if item.get('identifier'):
                items.append(item)

        if items:
            product_id = response.xpath('//div/@data-product-id').extract()[0]
            reviews_url = 'http://johnlewis.ugc.bazaarvoice.com/7051redes-en_gb/%s/reviews.djs?format=embeddedhtml&page=1&scrollToTop=true'
            yield Request(reviews_url % product_id, callback=self.parse_review_page, meta={'items': items, 'url': response.url})

    def parse_review_page(self, response):
        items = response.meta.get('items', '')
        url = response.meta.get('url', '')
        hxs = HtmlXPathSelector(text=self._extract_html(response))
        reviews = hxs.xpath('//div[@class="BVRRReviewDisplayStyle5"]')
        for review in reviews:
            l = ReviewLoader(item=Review(), response=response, date_format='%d/%m/%Y')
            rating = review.select(".//span[contains(@class,'BVRRRatingNumber')]/text()").extract()[0]
            date = review.select(".//span[contains(@class,'BVRRValue BVRRReviewDate')]/text()").extract()[0]
            title = review.select(".//span[contains(@class,'BVRRReviewTitle')]/text()").extract()
            review_text = ' '.join(review.select(".//span[contains(@class,'BVRRReviewText')]//text()").extract())

            if title:
                full_text = title[0].strip() + '\n' + review_text.strip()
            else:
                full_text = review_text.strip()

            l.add_value('rating', rating)
            l.add_value('url', url)
            l.add_value('date', datetime.strptime(date, '%d %B %Y').strftime('%d/%m/%Y'))
            l.add_value('full_text', full_text)
            for item in items:
                item['metadata']['reviews'].append(l.load_item())

        next = hxs.xpath('//span[@class="BVRRPageLink BVRRNextPage"]/a/@data-bvjsref').extract()
        if next:
            yield Request(next[0], callback=self.parse_review_page, meta={'items': items, 'url': url})
        else:
            for item in items:
                yield item

    def _extract_html(self, response):
        review_html = ''
        for line in response.body.split('\n'):
            if 'var materials=' in line:
                review_html = line.split('"BVRRSecondaryRatingSummarySourceID":" ')[-1].split('\n}')[0].replace('\\', '')
        return review_html
