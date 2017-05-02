import re
import os.path

from urlparse import urljoin
from urllib import quote as url_quote

from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.item import Item, Field

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.spiders.comms_express.utils import CommsBaseSpider

sku_regex = re.compile(r"^fe(.+)$", re.I)

HERE = os.path.abspath(os.path.dirname(__file__))

class CommsMeta(Item):
    manufacturers_no = Field()

class CommsExpressSpider(CommsBaseSpider):
    name = 'comms-express.com'
    allowed_domains = ['comms-express.com']
    handle_httpstatus_list = [500]

    def start_requests(self):
        manuf_sku_field = None
        comms_sku_field = None
        desc_field = None

        if self.rows:
            temp_row = self.rows[0]
        else:
            self.log("No rows!")
            return

        for field in temp_row:
            if 'Manufac pt n.o'.lower() in field.lower():
                manuf_sku_field = field
            elif 'Our Pt.n.o'.lower() in field.lower():
                comms_sku_field = field
            elif 'Description'.lower() in field.lower():
                desc_field = field

        for i, row in enumerate(self.rows, 1):
            sku1 = row[manuf_sku_field].strip()
            sku2 = row[comms_sku_field].strip()

            sku1 = sku1.replace("/", "`")
            sku2 = sku2.replace("/", "`")

            # Remove region code from D-Link products
            if sku1.endswith('/B'): sku1 = sku1[:-2]
            if sku2.endswith('/B'): sku2 = sku2[:-2]

            self.log('Searching: %s' % sku1)
            yield Request('http://www.comms-express.com/search/%s/' % url_quote(sku1, ''), callback=self.parse_product, meta={'dont_retry': True})

            self.log('Searching: %s' % sku2)
            yield Request('http://www.comms-express.com/search/%s/' % url_quote(sku2, ''), callback=self.parse_product, meta={'dont_retry': True})

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)

        warning = ''.join(hxs.select('//div[@class="InfoBanner" and contains(text(), "has returned 0 results")]//text()').extract())
        if not warning:
            warning = ''.join(hxs.select('//div[@class="noSearchResultsFound"]/text()').extract())

        if warning:
            self.log(warning)
            return

        many = hxs.select('//div[@id="SearchResults"]//div[@class="categoryGridTitle"]/a/@href').extract()
        if many:
            for url in many:
                yield Request(urljoin(get_base_url(response), url), callback=self.parse_product)
            return

        if hxs.select('//div[@class="color:red" and contains(text(), "this item is no longer available")]'):
            self.log('Item not available [%s]' % (response.url))
            return

        loader = ProductLoader(item=Product(), selector=hxs)

        comms_no = hxs.select('//tr[td[contains(text(), "Part No:")]]/td[not(@class)]/span/text()').extract()[0].upper()

        loader.add_value('identifier', comms_no)
        loader.add_value('url', response.url)
        loader.add_xpath('name', '//div[@id="productTitle"]//text()')
        loader.add_xpath('price', '//div[@id="productMainPrice"]/span[@id="price"]/text()')
        loader.add_xpath('sku', '//tr[td[contains(text(), "Part No:")]]/td[not(@class)]/span/text()')

        category = hxs.select('//div[@class="newbreadcrumbText"]//text()').extract()[1:-1]
        loader.add_value('category', category)
        img = hxs.select('//span[@id="mainImage"]/a/img/@src').extract()

        if len(img[0])<255:
            loader.add_value('image_url', urljoin(get_base_url(response), img[0]))
        else:
            loader.add_value('image_url', '')

        loader.add_xpath('brand', '//div[@id="supplierLogo"]/img/@title')
        if not loader.get_output_value('brand'):
            loader.add_value('brand', loader.get_output_value('name').split()[0])

        if loader.get_output_value('price') < 20:
            loader.add_value('shipping_cost', '2.95')
        else:
            loader.add_value('shipping_cost', '0')
        in_stock = 'IN STOCK' in ''.join(hxs.select('//div[@id="stockCheck"]/div/text()').extract()).upper()
        if in_stock:
            loader.add_value('stock', '1')
        else:
            loader.add_value('stock', '0')

        manufacturers_no = hxs.select('//span[@id="manufactNo"]/text()').extract()
        if not manufacturers_no:
            manufacturers_no = hxs.select('//tr[td[contains(text(), "Manufacturer No:")]]/td[not(@class)]/text()').extract()
        if not manufacturers_no:
            manufacturers_no = hxs.select('//tr[td[contains(text(), "Manufacturer No:")]]/td[2]//text()').extract()
        if not manufacturers_no:
            manufacturers_no = hxs.select('//tr[td[contains(text(), "Part No:")]]/td[not(@class)]/span/text()').extract()
        manufacturers_no = manufacturers_no[0].strip()
        m = sku_regex.search(manufacturers_no)
        if m:
            manufacturers_no = m.group(1)

        product = loader.load_item()

        product['metadata'] = {'manufacturers_no': manufacturers_no}

        self.yield_item_with_metadata(product)
        return
