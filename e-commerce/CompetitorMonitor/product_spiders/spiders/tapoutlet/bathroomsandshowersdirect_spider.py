import re
from decimal import Decimal
import xml.etree.ElementTree as et

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader


class BathroomsSDSpider(BaseSpider):
    name = 'bathroomsandshowersdirect.co.uk'
    allowed_domains = ['bathroomsandshowersdirect.co.uk']
    #user_agent = 'Googlebot/2.1 (+http://www.google.com/bot.html)'
    start_urls = ('http://www.bathroomsandshowersdirect.co.uk',)

    download_delay = 0.1

    url = 'http://www.bathroomsandshowersdirect.co.uk/AfcTool/Ajax/AjaxProductSearchGet.cfm'

    tries = {}
    max_tries = 10

    formdata = {'ChannelCode': '3076',
                'CurrentBuyIcon': '2007NXtMedBuyButtonBig.png',
                'CurrentLA': 'En',
                'CurrentPriceColor': 'fa0000',
                'bFirstSearch':'true',
                'cfs': '',
                'cst':'338',
                'iPriceFrom': '',
                'iPriceTo':'0',
                'iSearchSortBy':'0',
                'iStartRow':'1',
                'sChannels': '',
                'sSearchWord':'-',
                'sTopics':''}

    def start_requests(self):
        req = FormRequest(self.url, method='POST', dont_filter=True, formdata=self.formdata, meta={'start_row': 1})
        yield req

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        meta = response.meta

        body = response.body
        tree = et.fromstring(body)
        items = tree.findall('item')
        if items:
            for item in items:
                urls = item.findall('link')
                for url in urls:
                    yield Request(urljoin_rfc(base_url, url.text), callback=self.parse_product)
            start_row = meta.get('start_row') + 40
            formdata = self.formdata
            formdata['iStartRow'] = str(start_row)

            yield FormRequest(self.url, dont_filter=True, formdata=formdata, meta={'start_row': start_row}, callback=self.parse)
        
    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        hxs = HtmlXPathSelector(response)
        loader = ProductLoader(item=Product(), response=response)
        loader.add_xpath('image_url', '//img[@id="img1"]/@src')
        try:
            brand, text, sku, category = hxs.select('//title/text()').extract()[0].split(' | ')
        except:
            brand, sku, category = ['', '', '']

        sku = hxs.select('//div[contains(text(), "Product Code")]/text()').extract()
        if sku:
            sku = sku[0].strip().replace('Product Code: ', '')
        else:
            sku = ''
        if category:
            category = category.split(' - ')[0]

        loader.add_value('category', category)
        loader.add_value('brand', brand)
        loader.add_value('url', response.url)
        loader.add_xpath('name', '//h1/text()')
        identifier = hxs.select('//div[contains(@class, "priceCSS") and div[@class="THT369"]]/@class').extract()
        price = hxs.select('//div[contains(@class, "price")]/div/span/text()').extract()
        if price:
            price = price[0]

        if not identifier:
            identifier = hxs.select('//div[contains(@class, "priceCSS") and div[@class="THT364"]]/@class').extract()
            price = hxs.select('//div[contains(@class, "priceCSS")]/div[@class="THT364"]/text()').extract()
            if price:
                price = price[0].split(u'\xa3')[-1].split()[0]

        if not identifier:
            if not response.url in self.tries:
                self.tries[response.url] = 0
            self.tries[response.url] += 1
            if self.tries[response.url] < self.max_tries:
                r = Request(response.url, callback=self.parse_product, dont_filter=True)
                yield r
            return

        identifier = identifier[0].replace('priceCSS', '')
 
        if not price:
            price = '0.0'

        loader.add_value('identifier', identifier)
        loader.add_value('sku', sku.replace(' ', ''))
        loader.add_value('price', self.calculate_price(price))
        yield loader.load_item()


    def calculate_price(self, value):
        res = re.search(r'[.0-9]+', value)
        if res:
            price = Decimal(res.group(0))
            self.log("Price: %s" % price)
            return round((price) / Decimal('1.2'), 2)  # 20% EXC VAT
        else:
            return None
