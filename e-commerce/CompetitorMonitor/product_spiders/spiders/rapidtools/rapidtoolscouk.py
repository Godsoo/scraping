import re
import ast
from decimal import Decimal
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader


class RapidToolsCoUkSpider(BaseSpider):
    name = 'rapid-tools.co.uk'
    allowed_domains = ['www.rapid-tools.co.uk']
    start_urls = ['http://www.rapid-tools.co.uk/news/a-z/']

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        xpath_str = '//div[@id="content"]//div[@class="entry-content"]//table//li/a/@href'
        pages = hxs.select(xpath_str).extract()

        for page in pages:
            num = re.search('(\d+)\.html', page)
            if num:
                num = int(num.group(1))
                yield Request('http://www.rapid-tools.co.uk/tools/A000%d.cat' % num,
                              callback=self.parse_product)

    def parse_product(self, response):
        content = re.search(r"\s+=\s+({(?:.|\n)+});", response.body).group(1)

        # Fix following line to handle => inside strings, if needed
        content = re.sub(r"=>", r":", content)

        cat = ast.literal_eval(content)
        for k in cat.keys():
            if type(cat[k]) == type({}) and 'REFERENCE' in cat[k].keys():

                product = cat[k]

                try:
                    sku = str(int(product['REFERENCE']))
                except:
                    sku = product['REFERENCE']

                loader = ProductLoader(response=response, item=Product())
                loader.add_value('price', Decimal(product['PRICE']) / Decimal(100))
                loader.add_value('identifier', sku)
                loader.add_value('sku', sku)
                loader.add_value('url', 'http://www.rapid-tools.co.uk/tools/' + cat['PAGE'])
                loader.add_value('name', product['NAME'].decode('latin-1'))
                loader.add_value('image_url', 'http://www.rapid-tools.co.uk/tools/' + product['IMAGE'])
                loader.add_value('category', cat['NAME'])

                yield loader.load_item()



