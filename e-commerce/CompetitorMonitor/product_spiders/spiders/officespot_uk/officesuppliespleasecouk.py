from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.contrib.loader.processor import TakeFirst, Compose
from urlparse import urljoin
from product_spiders.items import Product, ProductLoader
from decimal import Decimal
import ast
import re
import json


class OfficeSuppliesPleaseSpider(BaseSpider):
    name = u'officesuppliesplease.co.uk'
    allowed_domains = [u'www.officesuppliesplease.co.uk']
    start_urls = [u'http://www.officesuppliesplease.co.uk/acatalog/sitemap.php']

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        anchors = hxs.select('//div[@id="content"]/ul[1]//a')
        for anchor in anchors:
            url = anchor.select('@href').extract().pop()
            cat = anchor.select('text()').extract().pop().strip()
            yield Request(urljoin(base_url, url), callback=self.parse_category, meta={"category": cat})

    def parse_category(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        products_xpath = '//div[@id="content"]//a[@class="product-list-link"]/@href'

        products = hxs.select(products_xpath).extract()
        for url in products:
            yield Request(urljoin(base_url, url), callback=self.parse_product, meta={"category": response.meta['category']})

        # if we have current page then we have pagination
        cur_page = hxs.select('//div[@class="page-controls"]/ul/li[contains(@class, "current-page")]/text()').extract()
        if cur_page:
            cur_page_index = int(cur_page[0])
            next_page_index = cur_page_index + 1
            next_page_xpath = '//div[@class="page-controls"]/ul/li[@class="number" and a/text()="%d"]/a/@href' % next_page_index
            next_page = hxs.select(next_page_xpath).extract()
            if next_page:
                url = next_page[0]
                yield Request(urljoin(base_url, url), callback=self.parse_category, meta={"category": response.meta['category']})

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        #define some common xpaths
        name_xpath = '//div[@id="content"]//h1[1]/text()'

        permutations = hxs.select('//table[@class="permutations"]')

        # Check if we have product options. If yes, we just parse it.
        options = hxs.select('//script[contains(text(), "ProductComponents")]/text()').extract()

        if options:
            self.log("Product has multiple options")
            jstext = options[0]
            codeblock = CodeBlockString(jstext.strip())
            pc = 'ProductComponents'
            self.log("Parsing Javascript codes")
            block = codeblock.findfrom(jstext.index(pc) + len(pc))
            code = block[block.index(' ')+1:]
            self.log("Evalutate json")
            #products = ast.literal_eval(code)
            products = json.loads(code)

            self.log('Parse option names')
            option_dict = {}
            divs = hxs.select('//div[@id="brochure-item-components"]/div[starts-with(@class, "complayout")]')
            for div in divs:
                labels = div.select('label')
                for label in labels:
                    option_name = label.select('input/@name').extract().pop()
                    option_text = label.select('span/text()').extract()
                    if option_text:
                        option_text = option_text[0]
                    else:
                        option_text = 'No label'
                        #self.log("No option text found for option name [%d]" % option_name)
                    option_value = label.select('input/@value').extract()
                    if option_value:
                        option_value = option_value[0]
                    else:
                        option_value = 'No Value'
                        #self.log("No option value found for option name [%d]" % option_name)
                    if not option_name in option_dict:
                        option_dict[option_name] = {}
                    option_dict[option_name][option_value] = option_text

            for pkey in products.keys():
                # product specification is in the details key
                pdetails = products[pkey]['details']
                self.log("Product loading from permutation with identifier %s" % pkey)
                l = ProductLoader(response=response, item=Product())
                name = hxs.select(name_xpath).extract().pop().strip()
                ppermutations = products[pkey]['permutations']
                # Find the option texts for available options and add it as name suffix
                name_suffix = ' '.join([option_dict[k]["%s" % ppermutations[k]] for k in ppermutations.keys()]).strip()
                l.add_value('name', "%s %s" % (name, name_suffix))

                self.load_product_common(response, l)
                l.add_value('price', pdetails['price'])
                l.add_value('identifier', pkey)
                l.add_value('sku', pkey)
                yield l.load_item()

        elif permutations:
            self.log("Product page has permutations of products")
            # Need to parse multiple product
            links = permutations.select('//table[@class="permutations"]//tr/td[@class="ref"]/a/@href').extract()
            for url in links:
                yield Request(urljoin(base_url, url), callback=self.parse_product, meta={"category": response.meta['category']})

        else:
            loader = ProductLoader(response=response, item=Product())

            name = hxs.select(name_xpath).extract().pop().strip()
            loader.add_value('name', name)

            loader.add_xpath('price', '//div[@id="quantity_prices"]/p[@class="good_price"]/span/text()')

            loader.add_xpath(
                'identifier',
                '//div[@class="product_info"]/ul/li[contains(text(), "Product Code:")]/text()',
                TakeFirst(),
                re='Product Code:\s+(\S+)'
            )

            loader.add_xpath(
                'sku',
                '//div[@class="product_info"]/ul/li[contains(text(), "Product Code:")]/text()',
                TakeFirst(),
                re='Product Code:\s+(\S+)'
            )

            self.load_product_common(response, loader)

            yield loader.load_item()

    def load_product_common(self, response, loader):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        quantity = hxs.select('//p[@class="out-of-stock-label"]/text()').extract()
        if quantity and "Out of stock" in quantity.pop():
            loader.add_value('stock', 0)

        loader.add_value('url', urljoin(base_url, response.url))
        loader.add_value('category', response.meta['category'])
        image_urls = hxs.select('//div[@id="extended_info_images"]/img/@src').extract()
        if image_urls:
            loader.add_value('image_url', urljoin(base_url, image_urls[0]))
        else:
            image_urls = hxs.select('//div[@class="first"]/a[@class="lightview"]/img/@src').extract()
            if image_urls:
                loader.add_value('image_url', urljoin(base_url, image_urls[0]))
            else:
                self.log("Image URL cannot parse from <%s>" % response.url)

    def calculate_price(self, value):
        res = re.search(r'[.0-9]+', value)
        if res:
            price = Decimal(res.group(0))
            self.log("Price: %s" % price)
            return round((price) * Decimal('1.2'), 2)  # 20% VAT
        else:
            return None


#Taken from https://github.com/shiplu/utils.py/
class CodeBlockString:
    """CodeBlockString finds blocks of code in a codes. If you have code string

        if(len(x)>len(y)){
            return new GreaterResultType(new GreaterParameter(x), new LesserParameter(y));
        }

    You can extract following strings from it

    1. `new GreaterParameter(x), new LesserParameter(y)`
    2. `return new GreaterResultType(new GreaterParameter(x), new LesserParameter(y));`
    3. `len(x)>len(y)`

    This is specially helpfull when you parse scripts in website (javascript) or custom
    file format that uses specific starting and ending characters.

    This will not work if the starting and ending tokens are longer than one character.

    Usage:
        # Instanciate
        cbs = CodeBlockString("if(len(x)>len(y)){ ...")
        cbs.set_start(['('])
        cbs.set_end([')'])
        block = cbs.findfrom(2)
        # block contains 'len(x)>len(y)' now

    """

    input = ''
    start = ['[', '{', '(']
    end = [']', '}', ')']
    length = 1

    def __init__(self, value):
        self.set(value)

    def set_start(self, start):
        self.start = start

    def set_end(self, end):
        self.end = end

    def set(self, value):
        self.input = list(value)
        self.length = len(value)

    def findfrom(self, index, level=1):
        """Finds string from an index

        Args:
            index: character index where the search should be started from
            level: nested level of next character in the string. Default 1

        Returns:
            The extracted code block string.

        """

        output = ''
        for i in range(index+1, self.length):
            if self.input[i] in self.start:
                level += 1
                output += self.input[i]
            elif self.input[i] in self.end:
                level -= 1
                if level < 1:
                    break
                output += self.input[i]
            else:
                output += self.input[i]

        return output
