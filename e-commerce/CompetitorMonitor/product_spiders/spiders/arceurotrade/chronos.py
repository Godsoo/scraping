import re
import os
from decimal import Decimal
from urllib import urlencode

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from scrapy import log

HERE = os.path.abspath(os.path.dirname(__file__))

class ChronosLtdSpider(BaseSpider):
    name = 'chronos.ltd.uk_arceurotrade'
    allowed_domains = ['chronos.ltd.uk', 'www.chronos.ltd.uk']
    start_urls = (u'http://www.chronos.ltd.uk/acatalog/sitemap.html', )

    def parse(self, response):
        if not isinstance(response, HtmlResponse):
            return
        hxs = HtmlXPathSelector(response)

        categories = hxs.select(u'//div[@id="container"]//li/a/@href').extract()
        for url in categories:
            url = urljoin_rfc(get_base_url(response), url)
            yield Request(url)

        for product in self.parse_product(response):
            yield product

    def parse_product(self, response):
        if not isinstance(response, HtmlResponse):
            return
        hxs = HtmlXPathSelector(response)

        products = hxs.select(u'//table[child::tr[child::td[@colspan="2" and child::h2]]]')
        for product in products:
            multiple_options = product.select(u'.//select/option')
            general_price = product.select(u'.//span[@class="actlarge"]/text()').extract()
            if general_price:
                if len(general_price) > 1:
                    multiplier = Decimal("1")
                    general_price = general_price[1]
                else:
                    multiplier = Decimal("1.2")
                    general_price = general_price[0]
                general_price = general_price.replace(u'\xa3', '')
                general_price = Decimal(general_price.replace(",", ""))
                general_price = general_price * multiplier
            else:
                general_price = None
            if not general_price:
                general_price = product.select(u'.//*/text()').re(u'Price inc UK Mainland Carriage.*?\:.*?\xa3([\d\.,]*)')
                general_price = general_price[0] if general_price else None
                log.msg(u'Product with: Price inc UK Mainland Carriage')

            if multiple_options and general_price:
                options_text = u' '.join(product.select(u'.//select/option/text()').extract())
                if u'\xa3' in options_text:
                    log.msg(u'Product with both option and general price: [%s]' % response.url)
            name = product.select(u'.//h2/text()')[0].extract().strip()
            if multiple_options and not general_price:
                idx = 1
                for option in multiple_options:
                    option_text = option.select(u'./text()')[0].extract()
                    loader = ProductLoader(item=Product(), selector=product)

                    price = re.search(u'\xa3([\d\.,]+)inc vat', option_text, re.I)
                    multiplier = Decimal("1")
                    if not price:
                        multiplier = Decimal("1")
                        price = re.search(u'\xa3([\d\.,]+)inc', option_text, re.I)
                    if not price:
                        multiplier = Decimal("1")
                        price = re.search(u'\(\xa3([\d\.,]+)\)?', option_text, re.I)
                    if not price:
                        multiplier = Decimal("1.2")
                        price = re.search(u'\xa3([\d\.,]+)', option_text, re.I)
                    if price:
                        price = Decimal(price.group(1).replace(",", "")) * multiplier
                    else:
                        continue
                    loader.add_value('name', name + u' %s' % option_text.strip())
                    loader.add_value('url', response.url)
                    loader.add_value('price', price)
                    m = re.search(r'\(Ref:\s*([^\)]+)\)', name, re.I)
                    if m:
                        optsku = option_text.strip().lower().replace('code', '').strip('-. ').split('-')[0]
                        # optsku = re.sub(r'\W+','',re.sub(r'.*\(ref:\s*[^\)]+\)','',re.sub(r'\xa3.*','',name.lower().replace('code',''))).strip('-. ').split('-')[0])
                        if optsku:
                            loader.add_value('sku', m.group(1) + optsku)
                        else:
                            loader.add_value('sku', m.group(1) + ".inc" + str(idx))
                            idx += 1
                        loader.add_value('identifier', loader.get_output_value('sku'))
                    yield loader.load_item()
            else:
                loader = ProductLoader(item=Product(), selector=product)
                loader.add_value('url', response.url)
                loader.add_value('name', name)
                if not general_price:
                    continue
                loader.add_value('price', general_price)
                m = re.search(r'\(Ref:\s*([^\)]+)\)', loader.get_output_value('name'), re.I)
                if m:
                    loader.add_value('sku', m.group(1))
                    loader.add_value('identifier', loader.get_output_value('sku'))
                # if loader.get_output_value('price'):
                yield loader.load_item()
