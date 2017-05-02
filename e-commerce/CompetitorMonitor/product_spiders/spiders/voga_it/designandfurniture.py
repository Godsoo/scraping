import re
from decimal import Decimal
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc
from product_spiders.items import Product, ProductLoader
from product_spiders.utils import extract_price_eu
from difflib import SequenceMatcher

class DesignAndFurniture(BaseSpider):
    name = 'designandfurniture.com'
    allowed_domains = ['designandfurniture.com']
    start_urls = ['http://www.designandfurniture.com/it/']

    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        for url in hxs.select('//*[@id="left_column"]//a/@href').extract():
            yield Request(url)

        for url in hxs.select('//*[@id="pagination_next"]/a/@href').extract():
            yield Request(url)

        for url in hxs.select('//*[@id="product_list"]//h3/a/@href').extract():
            yield Request(url, callback=self.parse_product)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)

        product_found = hxs.select('//div[@id="primary_block"]')
        if not product_found:
            return

        product_id = hxs.select('//input[@name="id_product"]/@value').extract()[0]
        name = hxs.select('//div[@id="dfCenter"]//h1/text()').extract()[0]
        category = hxs.select('//div[@class="breadcrumb"]/a/text()').extract()[1:]
        image_url = hxs.select('//img[@id="bigpic"]/@src').extract()
        if image_url:
            image_url = image_url[0]
        product_url = response.url
        product_brand = hxs.select('//div[@id="short_description_content"]//p[1]//text()').extract()[0]
        product_brand = product_brand.replace(' di ', ' da ')
        product_brand = product_brand.replace(' by ', ' da ')
        try:
            if len(product_brand) > 20:
                product_brand = re.search(' da.+?[,.]', product_brand).group(0)
        except:
            pass
        product_brand = product_brand.split(' da ')[-1]
        product_brand = product_brand.strip().strip('.,')
        if len(product_brand) > 20:
            title = hxs.select('//title/text()').extract()[0]
            s = SequenceMatcher(a=product_brand.title(), b=title.title())
            m = s.find_longest_match(0, len(s.a), 1, len(s.b))
            product_brand = s.a[m[0]:m[0]+m[-1]].strip()
        if len(product_brand) < 7 or ' ' not in product_brand:
            product_brand = None
        currencyRate = re.search('var currencyRate\D+([\d\.]+)', response.body)
        if currencyRate:
            currencyRate = Decimal(currencyRate.group(1))
        else:
            currencyRate = 1

        taxRate = re.search("var taxRate\D+([\d\.]+)", response.body)
        if taxRate:
            taxRate = Decimal(taxRate.group(1))
        else:
            taxRate = 0

        reduction_percent = re.search("var reduction_percent\D+([\d\.]+)", response.body)
        if reduction_percent:
            reduction_percent = Decimal(reduction_percent.group(1))
        else:
            reduction_percent = 0

        reduction_price = re.search("var reduction_price\D+([\d\.]+)", response.body)
        if reduction_price:
            reduction_price = Decimal(reduction_price.group(1))
        else:
            reduction_price = 0

        productPriceTaxExcluded = re.search("var productPriceTaxExcluded\D+([\d\.]+)", response.body)
        if productPriceTaxExcluded:
            productPriceTaxExcluded = Decimal(productPriceTaxExcluded.group(1))
        else:
            productPriceTaxExcluded = 0

        idDefaultImage = re.search('var idDefaultImage = (\d+)', response.body)
        if idDefaultImage:
            idDefaultImage = idDefaultImage.group(1)

        
        if re.search('addCombination.*?;', response.body):
            # here we parse option tags for more product options.
            option_value_xpath = '//div[@id="attributes"]//select/option/@value'
            option_values = hxs.select(option_value_xpath).extract()
            option_text_xpath = '//div[@id="attributes"]//select/option//text()'
            option_texts = hxs.select(option_text_xpath).extract()

            # build the lookup table.
            options = {}
            for i in range(len(option_values)):
                options[option_values[i]] = option_texts[i]

            # addCombination(5631, new Array('259'), 11, 109.99, 0, -1, 'GGT3050', 0.00, 1);
            for x in re.finditer('addCombination\((.*?)\);', response.body):
                s = x.group(0).split(',')
                offset = Decimal(s[-6])

                # determining place of options keys
                option_key_start = 1
                option_key_end = len(s) - 7

                # parsing option keys
                option_texts = []
                opt = ''
                for i in range(option_key_start, option_key_end):
                    try:
                        opt = re.sub('[^\d]+', '', s[i])
                        option_text = options[opt]
                    except:
                        pass
                    if len(option_text) > 0:
                        option_texts.append(option_text.strip())

                price = productPriceTaxExcluded + offset * currencyRate
                tax = (taxRate / Decimal('100')) + 1
                price = price * tax
                reduction = Decimal('0')
                if reduction_price or reduction_percent:
                    reduction = price * (reduction_percent / Decimal('100')) + reduction_price
                    price = price - reduction
                price = round(price, 2)
                loader = ProductLoader(response=response, item=Product())
                loader.add_value('url', product_url)
                loader.add_value('name', name + ' ' + ' '.join(option_texts))

                image_id = s[-4].strip(" '")
                if image_url and image_id != "-1" and image_id != idDefaultImage:
                    loader.add_value('image_url', image_url.replace('-' + idDefaultImage + '-', '-' + image_id + '-'))
                else:
                    loader.add_value('image_url', image_url)

                loader.add_value('brand', product_brand)
                loader.add_value('price', price)
                loader.add_value('category', category)
                loader.add_value('identifier', '%s-%s' % (product_id, re.search(r'(\d+)', s[0]).group(1)))
                loader.add_value('sku', s[-3].strip("' ").decode('utf8'))

                yield loader.load_item()
        else:
            loader = ProductLoader(response=response, item=Product())
            loader.add_value('url', product_url)
            loader.add_value('name', name)
            loader.add_value('image_url', image_url)
            loader.add_xpath('price', '//*[@id="our_price_display"]/text()', lambda x: extract_price_eu(x[0]) if x else Decimal('0'))
            loader.add_value('category', category)
            loader.add_value('identifier', product_id)
            loader.add_xpath('sku', '//*[@id="product_reference"]/span/text()')
            loader.add_value('brand', product_brand)

            yield loader.load_item()


