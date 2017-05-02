import re
from decimal import Decimal
import itertools

from scrapy import log
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader


class WayFairComSpider(BaseSpider):
    name = 'tapoutlet-wayfair.com'
    allowed_domains = ['wayfair.co.uk']
    user_agent = 'Googlebot/2.1 (+http://www.google.com/bot.html)'
    start_urls = ('http://www.wayfair.co.uk/Lighting-C234985.html', 
                  'http://www.wayfair.co.uk/Mira-C1770905.html',
                  'http://www.wayfair.co.uk/Bathroom-Lighting-C235548.html')

    download_delay = 0.1


    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        categories = hxs.select('//div[@class="catnav bgdot_lg bgdot_bottom"]/a[not(contains(@href, "Shop-All"))]/@href').extract()
        for category in categories:
            yield Request(category)

        items = hxs.select(u'//li[contains(@class, "productbox")]//a[contains(@class, "toplink")]/@href').extract()
        if items:
            category = hxs.select('//div[@class="js-page-header"]/h1/text()').extract()
            if not category:
                category = hxs.select('//span[@class="breadcrumb note ltbodytext"]/a/h1/text()').extract()
            category = category[0] if category else ''
            for item in items:
                yield Request(urljoin_rfc(base_url, item),
                              meta={'category': category},
                              callback=self.parse_item)

        next_page = hxs.select(u'//span[@class="pagenumbers"]/a[contains(text(),"Next")]/@href').extract()
        if next_page:
            yield Request(urljoin_rfc(base_url, next_page[0]),
                          meta=response.meta,
                          callback=self.parse)

    def parse_item(self, response):
        hxs = HtmlXPathSelector(response)

        meta = response.meta

        try:
            sku = hxs.select('//span[@class="bodytext referencetext"]/text()').extract()[0].split(':      ')[-1].strip()
        except:
            sku = u''

        try:
            image_url = hxs.select('//img[@id="lgimage"]/@src').extract().pop()
        except:
            image_url = u''

        total_skus = len(sku.split(', '))

        if total_skus < 2:
            sku = sku.replace(' ', '')
        else:
            sku = ''
            
        name = hxs.select('//h1/strong/text()').extract()[0]
        name += hxs.select('//h1/text()').extract()[0]
        brand = hxs.select('//div[@class="prodnameshare"]/h1/strong/text()').extract()[0]
        options = []
        dropdown_options = hxs.select('//table[@class="kit_table"]//select[@class="stdselect yui3-pp-pricing"]/option[@value!="XXXXXXXXXX"]')
        '''
        if not dropdown_options:
            dropdown_options = hxs.select('//select[@class="stdselect yui3-pp-pricing"]/option[@value!="XXXXXXXXXX"]')
            if not dropdown_options:
                dropdown_options = hxs.select('//div[@class="pdinfoblock"]/div/div/div/select/option[@value!="XXXXXXXXXX"]')
                if not dropdown_options:
                    dropdown_options = hxs.select('//div[@class="pdinfoblock"]/div/div/select/option[@value!="XXXXXXXXXX"]')
        '''
        option_elements = []
        options = []
        if dropdown_options:
            for dropdown_option in dropdown_options: 
                option = {}
                option['identifier'] = dropdown_option.select('@value').extract()[0]
                option['sku'] = ''
                option['desc'] = dropdown_option.select('text()').extract()[0].split('-')[0]
                option['cost'] = dropdown_option.select('@cost').extract()[0]
                options.append(option)
            option_elements.append(options)
        else:
            dropdown_elements = hxs.select('//div[@class="pdinfoblock"]/div[@class="fl"]//select')
            for dropdown_options in dropdown_elements:
                options = []
                for dropdown_option in dropdown_options.select('option[@value!="XXXXXXXXXX"]'):
                    option = {}
                    option['identifier'] = dropdown_option.select('@value').extract()[0]
                    option['sku'] = ''
                    option['desc'] = dropdown_option.select('.//text()').extract()[0].split('-')[0]
                    option['cost'] = dropdown_option.select('@cost').extract()[0]
                    options.append(option)
                option_elements.append(options)
                
        image_options = hxs.select('//div[@class="fl"]/div/div/a')
        if image_options:
            options = []
            for image_option in image_options: 
                option = {}
                option['identifier'] = image_option.select('@data-pi-id').extract()[0]
                option['sku'] = ''
                option['desc'] = image_option.select('@data-name').extract()[0]
                option['cost'] = image_option.select('@data-cost').extract()[0]
                options.append(option)
            option_elements.append(options)

        if option_elements:
            if len(option_elements)>1:
                combined_options = list(itertools.product(*option_elements))
                options = []
                for combined_option in combined_options:
                    final_option = {}
                    for option in combined_option:
                        final_option['desc'] = final_option.get('desc', '') + ' - ' + option['desc']
                        final_option['cost'] = final_option.get('cost', 0) + float(option['cost'])
                        final_option['identifier'] = final_option.get('identifier', '') + ' - ' + option['identifier']
                    options.append(final_option)
            else:
                options = option_elements[0]

            for option in options:
                product_loader = ProductLoader(item=Product(), response=response)
                product_loader.add_value('name', name + ' ' + option['desc'])
                product_loader.add_value('sku', sku)
                identifier = hxs.select('//input[@name="sku"]/@value').extract()[0]
                product_loader.add_value('identifier', identifier + '-' + option['identifier'])
                product_loader.add_value('brand', brand)
                product_loader.add_value('category', meta.get('category'))
                product_loader.add_value('image_url', image_url)
                product_loader.add_value('url', response.url)

                price = hxs.select('//*[@class="dynamic_sku_price"]/span/text()').extract()[0]
                price += hxs.select('//*[@class="dynamic_sku_price"]/span/sup/text()').extract()[0]

                product_loader.add_value('price', self.option_price(price, str(option['cost'])))
                yield product_loader.load_item()
        else:
            product_loader = ProductLoader(item=Product(), response=response)
            product_loader.add_value('name', name)
            product_loader.add_value('sku', sku.replace(' ', ''))
            product_loader.add_xpath('identifier', '//input[@name="sku"]/@value')
            product_loader.add_value('brand', brand)
            product_loader.add_value('category', meta.get('category'))
            product_loader.add_value('image_url', image_url)

            price = hxs.select('//*[@class="dynamic_sku_price"]/span/text()').extract()[0]
            price += hxs.select('//*[@class="dynamic_sku_price"]/span/sup/text()').extract()[0]

            product_loader.add_value('price', self.calculate_price(price))

            product_loader.add_value('url', response.url)

            yield product_loader.load_item()

    def calculate_price(self, value):
        res = re.search(r'[,.0-9]+', value)
        if res:
            price = Decimal(res.group(0).replace(',', ''))
            self.log("Price: %s" % price)
            return round((price) / Decimal('1.2'), 2)  # 20% EXC VAT
        else:
            return None

    def option_price(self, base_price, cost):
        res = re.search(r'[.0-9,]+', base_price)
        cost_res = re.search(r'[.0-9,]+', cost)
        if res:
            price = Decimal(res.group(0).replace(',', ''))
            cost = Decimal(cost_res.group(0).replace(',', ''))
            self.log("Price: %s" % price)
            return round(((price) + cost) / Decimal('1.2'), 2)  # 20% EXC VAT
        else:
            return None



