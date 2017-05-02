import re
import os

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from scrapy import log

HERE = os.path.abspath(os.path.dirname(__file__))

INVALID_PRODUCTS = ['emfs4', 'xp62', '761720..', 'xc178.', 'xc176..', 'erm100',
                    'xc7..', 'xc8..', 'emfs2...', 'emfs4...', 'emfs5...',
                    'xc175', 'xc186', '761720...', 'xc158', 'va6']

class ChronosLtdSpider(BaseSpider):
    name = 'chronos.ltd.uk'
    allowed_domains = ['chronos.ltd.uk', 'www.chronos.ltd.uk']

    start_urls = (u'http://www.chronos.ltd.uk/acatalog/index.html',)

    def parse(self, response):
        if not isinstance(response, HtmlResponse):
            return
        hxs = HtmlXPathSelector(response)

        categories = hxs.select('//div[@id="ContentPage"]/table/tr/td/table/tr/td/strong/a/@href').extract()
        for url in categories:
            url = urljoin_rfc(get_base_url(response), url)
            yield Request(url)

        for product in self.parse_product(response):
            yield product


    def parse_product(self, response):
        if not isinstance(response, HtmlResponse):
            return
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        prod_lists = hxs.select('//div[@class="product_list"]/div/h3/a/@href').extract()
        if prod_lists:
            for url in prod_lists:
                url = urljoin_rfc(get_base_url(response), url)
                yield Request(url)

        products = hxs.select(u'//table[child::tr[child::td[@colspan="2" and child::h2]]]')
        if products:
            try:
                category = hxs.select('//div[@class="page-heading"]/h1/text()').extract()[0].strip()
            except:
                try:
                    category = hxs.select('//div[@id="frag"]//text()').extract()[0].strip()
                except:
                    category = hxs.select('//p[@class="text_breadcrumbs"]//text()').extract().pop()
        for product in products:
            try:
                image_url = urljoin_rfc(base_url, product.select('.//img/@src').extract()[0])
            except:
                image_url = ''
            multiple_options = product.select(u'.//select/option')
            general_price = product.select(u'.//span[@class="actlarge"]/text()').extract()
            general_price = general_price[0] if general_price else None
            if not general_price:
                general_price = product.select(u'.//*/text()').re(u'Price inc UK Mainland Carriage.*?\:.*?\xa3([\d\.,]*)')
                general_price = str(round(float(general_price[0]) / 1.2, 2)) if general_price else None
                log.msg(u'Product with: Price inc UK Mainland Carriage')
            if multiple_options and general_price:
                options_text = u' '.join(product.select(u'.//select/option/text()').extract())
                if u'\xa3' in options_text:
                    log.msg(u'Product with both option and general price: [%s]' % response.url)
            name = product.select(u'.//h2/text()')[0].extract().strip()
            name_complete = ''.join(product.select(u'.//h2//text()').extract())
            if 'special offer' in name.lower():
                special_offer_starts_at = name.lower().index('special offer')
                new_name = name[:special_offer_starts_at].strip()
                if 'ref:' in new_name.lower():
                    self.log("Found special offer")
                    self.log("Before: '%s'" % name)
                    self.log("After: '%s'" % new_name)
                    name = new_name.replace(u'  (Ref', u' \xa0(Ref')
            if multiple_options and not general_price:
                idx = 1
                for option in multiple_options:
                    option_text = option.select(u'./text()')[0].extract()
                    loader = ProductLoader(item=Product(), selector=product)

                    price = re.search(u'\xa3([\d\.,]+)', option_text)
                    if price:
                        price = price.group(1)
                    else:
                        continue
                    regex = r'[\d]{1,2},[\d]{2}'
                    if re.search(regex, price):
                        price = price.replace(',', '.')

                    loader.add_value('name', name + u' %s' % option_text.strip())
                    loader.add_value('category', category)
                    loader.add_value('image_url', image_url)
                    loader.add_value('url', response.url)
                    loader.add_value('price', price)
                    m = re.search(r'\(Ref:\s*([^\)]+)\)', name_complete, re.I)
                    if m:
                        optsku = option_text.strip().lower().replace('code', '').strip('-. ').split('-')[0]
                        if optsku:
                            loader.add_value('sku', m.group(1) + optsku)
                        else:
                            loader.add_value('sku', m.group(1) + ".inc" + str(idx))
                            idx += 1
                        loader.add_value('identifier', loader.get_output_value('sku'))

                    if loader.get_output_value('sku') not in INVALID_PRODUCTS:
                        yield loader.load_item()
            else:
                loader = ProductLoader(item=Product(), selector=product)
                loader.add_value('url', response.url)
                loader.add_value('name', name)
                loader.add_value('category', category)
                loader.add_value('image_url', image_url)
                if not general_price:
                    continue
                regex = r'[\d]{1,2},[\d]{2}'
                if re.search(regex, general_price):
                    general_price = general_price.replace(',', '')
                loader.add_value('price', general_price)
                m = re.search(r'\(Ref:\s*([^\)]+)\)', name_complete, re.I)
                if m:
                    loader.add_value('sku', m.group(1))
                    loader.add_value('identifier', loader.get_output_value('sku'))

                # if loader.get_output_value('price'):
                if loader.get_output_value('sku') not in INVALID_PRODUCTS:
                    yield loader.load_item()
