import logging

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from keteritems import KeterMeta, Review

class WayFairComSpider(BaseSpider):
    name = 'wayfair.com'
    allowed_domains = ['wayfair.com']
    user_agent = 'Googlebot/2.1 (+http://www.google.com/bot.html)'

    def start_requests(self):
        # These URLs come from http://www.wayfair.com/Browse-By-Brand-C114464.html
        brand_urls = (
            ('Keter', 'http://www.wayfair.com/All-Keter-C1765357.html'),
            ('SUNCAST', 'http://www.wayfair.com/All-Suncast-C447623.html'),
            ('RUBBERMAID', 'http://www.wayfair.com/All-Rubbermaid-C1765008.html'),
            # Rubbermaid Commercial Products as well?
            #    http://www.wayfair.com/Rubbermaid-Commercial-C458511.html
            ('LIFETIME', 'http://www.wayfair.com/All-Lifetime-C445511.html'),
            ('STEP 2', 'http://www.wayfair.com/All-Step2-C472524.html'),
            ('STERILITE', 'http://www.wayfair.com/View-All-C466985.html'),
        )
        for brand, url in brand_urls:
            yield Request(url, meta={'brand': brand}, callback=self.parse)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        items = hxs.select(u'//li[contains(@class, "productbox")]//a[contains(@class, "toplink")]/@href').extract()
        for item in items:
            yield Request(urljoin_rfc(base_url, item),
                          meta=response.meta,
                          callback=self.parse_item)

        next_page = hxs.select(u'//span[@class="pagenumbers"]/a[contains(text(),"Next")]/@href').extract()
        if next_page:
            yield Request(urljoin_rfc(base_url, next_page[0]),
                          meta=response.meta,
                          callback=self.parse)

    def parse_item(self, response):
        hxs = HtmlXPathSelector(response)

        product_loader = ProductLoader(item=Product(), response=response)
        name = hxs.select('//h1/strong/text()').extract()[0]
        name += hxs.select('//h1/text()').extract()[0]
        product_loader.add_value('name', name)

        # SKU #: YEH1020 | Part #: 03958604
        '''
        sku_part = hxs.select('//div[contains(@class, "sku")]/*[contains(text(), "SKU")]/text()').extract()[0]
        sku, part = sku_part.split('|')
        sku = sku.replace('SKU #:', '').strip()
        part = part.replace('Part #:', '').strip()
        '''

        try:
            category = hxs.select('//a[contains(@class, "currentcat")]/text()').extract().pop()
        except:
            category = u''

        try:
            image_url = hxs.select('//img[@id="lgimage"]/@src').extract().pop()
        except:
            image_url = u''

        sku = hxs.select('//div[contains(@class, "pdp_head_info")]/text()').re(r'SKU #:.([\w\d]+)')[0]
        identifier = hxs.select('//span[contains(text(), "Part #")]/text()').re(r':.([\w\d]+)')[0]

        product_loader.add_value('sku', sku)
        product_loader.add_value('identifier', sku)
        product_loader.add_value('brand', response.meta['brand'])
        product_loader.add_value('category', category)
        product_loader.add_value('image_url', image_url)

        price = hxs.select('//*[@class="dynamic_sku_price"]/span/text()').extract()[0]
        price += hxs.select('//*[@class="dynamic_sku_price"]/span/sup/text()').extract()[0]
        product_loader.add_value('price', price)

        product_loader.add_value('url', response.url)

        product = product_loader.load_item()

        metadata = KeterMeta()
        metadata['brand'] = response.meta['brand']
        metadata['reviews'] = []
        product['metadata'] = metadata
        response.meta.update({'product': product})

        for x in self.parse_review(response):
            yield x

    def parse_review(self, response):
        hxs = HtmlXPathSelector(response)
        product = response.meta['product']

        for review in hxs.select(u'//tr[@class="singlereview"]'):
            item = Review()
            date = review.select(u'.//div[contains(@class,"ltbodytext")]/text()').extract()[0]
            date = date.split('/')
            item['date'] = date[1] + '/' + date[0] + '/' + date[2]

            title = review.select(u'.//p[@class="subtitle"]/text()').extract()
            if title: title = title[0]
            else: title = ''
            text = review.select(u'.//div[@class="bodytext"]/p/text()').extract()
            if text: text = text[0]
            else: text = ''
            item['full_text'] = title + '\n' + text

            item['rating'] = int(float(review.select(u'.//div[contains(@class,"rating_avg_sm")]/text()').extract()[0]))

            item['url'] = response.url

            product['metadata']['reviews'].append(item)

        next_url = hxs.select(u'//div[contains(@class,"pagination")]/a[contains(text(),"Next")]/@href').extract()
        logging.error(next_url)
        if next_url:
            yield Request('http://www.wayfair.com/ajax/view_reviews_action.php?prsku=%s&rvpg=%s&rvso=0' % (
                product['sku'], next_url[0].split('curpage=')[1]), meta=response.meta, callback=self.parse_review)
        else:
            yield product
