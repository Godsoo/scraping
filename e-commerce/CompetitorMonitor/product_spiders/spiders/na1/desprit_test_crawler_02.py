# -*- coding: utf-8 -*-
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.contrib.loader import ItemLoader
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from scrapy.http import Request, FormRequest
import re, json


class AudioSpider(BaseSpider):
    name = "sxpro_new_new"
    allowed_domains = ["sxpro.co.uk"]
    start_urls = ["http://sxpro.co.uk/brands/"]

    def parse(self, response):
        '''Parse home page and extract all categories from side menu'''

        hxs = HtmlXPathSelector(response)
        brand_links = hxs.select("//div[@class='brandsdiv']//a/@href").extract()

        for brand_link in brand_links:
            yield Request((brand_link), callback=self.parse_brand)

    def parse_brand(self, response):
        '''Parse page of particular brand'''

        hxs = HtmlXPathSelector(response)
        brand = hxs.select('//div[@id="BrandBreadcrumb"]//li/text()').extract()[-1].title()
        try:
            pages = hxs.select("//div[@class='FloatRight']/a/@href").extract()
        except:
            pages = []
        items = hxs.select("//ul[@class='ProductList']/li/div[@class='ProductDetails']//a/@href").extract()

        for item in items:
            yield Request((item), callback=self.parse_item, meta={'brand': brand})

        for page in pages:
            yield Request((page), callback=self.parse_brand)

    def parse_item(self, response):
        '''Parse page of particular product'''

        hxs = HtmlXPathSelector(response)
        page_title = hxs.select("//title/text()").extract()[0]
        product_category = hxs.select("//div[@id='ProductBreadcrumb']/ul/li/a/text()").extract()[1]
        product_name = hxs.select("//div[@id='ProductDetails']//h1/text()").extract()[0]
        product_price = hxs.select("//span[@class='ProductDetailsPriceIncTax']/text()").extract()
        product_id = hxs.select("//input[@name='product_id']/@value").extract()[0]
        product_brand = product_brand = response.meta['brand']
        product_image = hxs.select("//div[@class='ProductThumbImage']/a/img/@src").extract()[0]

        product_details = hxs.select("//form[@id='productDetailsAddToCartForm']").extract()
        options_to_check = []
        possible_options = {}
        product_option_attributes = []

        if product_price:
                product_price = product_price[0].encode('utf-8')
                price_pattern = '[0-9,]+\.[0-9]{2}'
                product_price = re.findall(re.compile(price_pattern), product_price)[0]
                product_price = float(re.sub(',', '', product_price))
                stock_status = 1
        else:
            product_price = 0.00
            stock_status = 0


        if product_details:
            product_options = hxs.select("//form[@id='productDetailsAddToCartForm']//div[@class='productOptionViewSelect']")
            product_attribute_labels = hxs.select("//form[@id='productDetailsAddToCartForm']//div[@class='productAttributeLabel']//span[@class='name']/text()").extract()
            product_attribute_labels = [re.compile(r'[\n\r\t]').sub('', product_attribute_label) for product_attribute_label in product_attribute_labels]

            for num, product_option in enumerate(product_options):

                product_option_attribute = product_option.select("select[@class='validation']/@name").extract()[0]
                product_option_attributes.append(product_option_attribute)

                product_option_data = product_option.select("*/option[not(@value='') and not(contains(text(), 'None'))]").extract()
                product_option_values_set = [''.join(re.findall(re.compile('value=\"(.+?)\"'), i))  for i in product_option_data]
                product_option_titles_set = [''.join(re.findall(re.compile('>(.+?)<\/option>'), i)) for i in product_option_data]

                possible_options[str(num + 1)] = product_option_values_set + ['']

                for a in range(len(product_option_values_set)):
                    tmp_dict = {}
                    tmp_dict[product_option_titles_set[a]] = product_option_values_set[a]
                    options_to_check.append(tmp_dict)

            # On the website there only products with 0, 1 and 2 numbers of options
            if len(product_option_attributes) == 2:
                for value_01 in possible_options.get('1'):
                    for value_02 in possible_options.get('2'):
                        post_data = {'actions': 'add',
                                     'product_id': product_id,
                                      product_option_attributes[0]: value_01,
                                      product_option_attributes[1]: value_02,
                                     'w': 'getProductAttributeDetails'}

                        yield FormRequest('http://www.sxpro.co.uk/remote.php',
                                      formdata=post_data,
                                      method='POST',
                                      callback=self.handle_json_response,
                                      meta={'value_01':      value_01,
                                                  'value_02':      value_02,
                                                  'num_options':   2,
                                                  'options':       options_to_check,
                                                  'product_name':  product_name,
                                                  'product_id':    product_id,
                                                  'stock_status':  stock_status,
                                                  'product_url':   response.url,
                                                  'product_image': product_image,
                                                  'category':      product_category,
                                                  'product_brand': product_brand},
                                      dont_filter=True)

            elif len(product_option_attributes) == 1:
                for value_01 in possible_options.get('1'):
                    post_data = {'actions': 'add',
                                 'product_id': product_id,
                                  product_option_attributes[0]: value_01,
                                 'w': 'getProductAttributeDetails'}

                    yield FormRequest('http://www.sxpro.co.uk/remote.php',
                                  formdata=post_data,
                                  method='POST',
                                  callback=self.handle_json_response,
                                  meta={'value_01':      value_01,
                                              'num_options':   1,
                                              'options':       options_to_check,
                                              'product_name':  product_name,
                                              'product_id':    product_id,
                                              'stock_status':  stock_status,
                                              'product_url':   response.url,
                                              'product_image': product_image,
                                              'category':      product_category,
                                              'product_brand': product_brand},
                                  dont_filter=True)

            else:
                l = ProductLoader(item=Product(), response=response)

                l.add_value('price', product_price)
                l.add_value('stock', stock_status)
                l.add_value('identifier', product_id)
                l.add_value('category', product_category)
                l.add_value('url', response.url)
                l.add_value('name', product_name)
                l.add_value('image_url', product_image)
                l.add_value('brand', product_brand)

                yield l.load_item()

    def handle_json_response(self, response):
        data = json.loads(response.body)

        if response.meta['num_options'] == 2:
            key_01, key_02 = '', ''
            for option_to_check in response.meta['options']:
                for k, v in option_to_check.iteritems():
                    if v == response.meta['value_01']:
                        key_01 = k
                    if v == response.meta['value_02']:
                        key_02 = k

            l = ProductLoader(item=Product(), response=response)
            l.add_value('identifier', response.meta['product_id'] + str(response.meta['value_01']) + str(response.meta['value_02']))
            l.add_value('name', response.meta['product_name'] + ' ' + key_01 + ' ' + key_02)


        elif response.meta['num_options'] == 1:
            key_01 = ''
            for option_to_check in response.meta['options']:
                for k, v in option_to_check.iteritems():
                    if v == response.meta['value_01']:
                        key_01 = k

            l = ProductLoader(item=Product(), response=response)
            l.add_value('identifier', response.meta['product_id'] + str(response.meta['value_01']))
            l.add_value('name', response.meta['product_name'] + ' ' + key_01)


        l.add_value('price', float(data['details']['unformattedPrice']) * 1.2)
        l.add_value('stock', response.meta['stock_status'])
        l.add_value('category', response.meta['category'])
        l.add_value('url', response.meta['product_url'])
        l.add_value('image_url', response.meta['product_image'])
        l.add_value('brand', response.meta['product_brand'])

        yield l.load_item()
