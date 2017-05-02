import re
import copy
import json
from decimal import Decimal

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

from product_spiders.utils import extract_price
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader


class SinksTapsSpider(BaseSpider):
    name = 'sinks-taps.com'
    allowed_domains = ['sinks-taps.com']
    start_urls = ['http://www.sinks-taps.com/',
                  'http://www.sinks-taps.com/search.aspx?manufacturerid=0&categoryid=0&minprice=0&maxprice=0&code=']

    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        for category in hxs.select(u'//div[@class="contentleft"]//a[contains(@href,"category")]'):
            url = category.select(u'./@href')[0].extract()
            yield Request(urljoin_rfc(get_base_url(response), url),
                          meta={'category': category.select(u'./@title')[0].extract()})

        for subcategory in hxs.select(u'//div[@class="categorylisting"]/a/@href').extract():
            yield Request(urljoin_rfc(get_base_url(response), subcategory), meta=response.meta)

        for product in hxs.select(u'//div[@class="clsItemListingTextProductNameDiv"]'):
            price = product\
                .select('./following-sibling::div[@class="clsItemListingTextPricesFromDiv"]'
                        '/strong/text()')\
                .extract()
            meta = response.meta.copy()
            meta['price'] = price

            url = product.select('.//a/@href').extract()[0]
            yield Request(urljoin_rfc(get_base_url(response), url),
                          meta=meta,
                          callback=self.parse_product)

        # for page in hxs.select(u'').extract():
            # yield Request(urljoin_rfc(get_base_url(response), page), meta=response.meta)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)

        loader = ProductLoader(item=Product(), selector=hxs)
        identifier = re.search(u'item-(.*)-', response.url).group(1)
        loader.add_value('identifier', identifier)
        sku = hxs.select(u'//span[contains(text(),"Product Code")]/strong/text()').extract()
        if sku:
            sku = sku[0]
            loader.add_value('sku', sku.replace(' ', ''))
        loader.add_value('url', response.url)
        name = hxs.select(u'//div[@class="clsItemDescriptionHeader"]/h2/text()').extract()
        loader.add_value('name', name[0].strip())
        price = response.meta.get('price')
        if not price:
            price = hxs.select(u'//span[@class="itemsalaprice"]/text()').extract()
        if price:
            price = re.sub(u'[^\d\.]', u'', price[0].strip())
            loader.add_value('price', str(round(Decimal(price) / Decimal(1.2), 2)))
        loader.add_value('category', response.meta.get('category'))

        img = hxs.select(u'//img[@class="itemimage"]/@src').extract()
        if img:
            loader.add_value('image_url', urljoin_rfc(get_base_url(response), img[0]))

        brand = hxs.select('//a[@id="MainContent_manufacturerhref"]/text()').extract()
        if brand:
            brand = brand[0].split('See all ')[-1].split(' products')[0]
        else:
            brand = ''
        loader.add_value('brand', brand)
        options = hxs.select(u'//select[@name="MainContent:ddlOptions"]/option[not(starts-with(text(),"Select..."))]')
        option_type = u'MainContent:ddlOptions'
        if not options:
            options = hxs.select(u'//input[@type="radio" and @name="MainContent:rblOptions"]')
            option_type = u'MainContent:rblOptions'
        if not options:
            yield loader.load_item()
        elif not response.meta.get('already_explored'):
            i = 1
            for option in options:
                if option_type == 'MainContent:ddlOptions':
                    option_name = option.select(u'./text()').extract()
                else:
                    option_name = option.select(u'../label/text()').extract()
                option_name = option_name[0]
                option = option.select(u'./@value')[0].extract()
                formdata = {'ProductSearch:txtFindExactModel': '',
                            '__EVENTARGUMENT': '',
                            '__EVENTTARGET': option_type,
                            'stSearch:Categories': '0',
                            'stSearch:Manufacturers': '0',
                            'stSearch:Prices': 'minprice=0&maxprice=0'}
                formdata['__VIEWSTATE'] = hxs.select(u'//form//input[@type="hidden" and @name="__VIEWSTATE"]/@value')[0].extract()
                formdata[option_type] = option
                url = hxs.select(u'//form/@action')[0].extract()
                loader = ProductLoader(item=Product(), selector=hxs)
                loader.add_value('identifier', u'%s.%s' % (identifier, str(i)))
                loader.add_value('url', response.url)
                loader.add_value('name', u'%s %s' % (name[0].strip(), option_name.strip()))
                loader.add_value('category', response.meta.get('category'))
                loader.add_value('image_url', urljoin_rfc(get_base_url(response), img[0]))
                loader.add_value('brand', brand)
                meta = response.meta
                meta.update({'product_loader': loader, 'already_explored': True})
                yield FormRequest(urljoin_rfc(get_base_url(response), url), formdata=formdata, meta=meta, callback=self.parse_price)
                i += 1

    def parse_price(self, response):
        hxs = HtmlXPathSelector(response)
        loader = response.meta.get('product_loader')
        price = hxs.select(u'//span[@class="itemsalaprice"]/text()').extract()
        if price:
            price = re.sub(u'[^\d\.]', u'', price[0].strip())
            loader.add_value('price', str(round(Decimal(price) / Decimal(1.2), 2)))
        sku = hxs.select(u'//span[contains(text(),"Product Code")]/text()').extract()
        if len(sku) > 1:
            sku = sku[1]
            loader.add_value('sku', sku.replace(' ', ''))
        yield loader.load_item()
