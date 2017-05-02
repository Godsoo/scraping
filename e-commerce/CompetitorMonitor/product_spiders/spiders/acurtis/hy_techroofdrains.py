import re
import json
import itertools

from scrapy.selector import HtmlXPathSelector
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc
from scrapy.spider import BaseSpider
from scrapy.http import Request, HtmlResponse, FormRequest

from product_spiders.items import Product, ProductLoader
from product_spiders.utils import extract_price


from scrapy import log
from decimal import Decimal

try:
    import json
except ImportError:
    import simplejson as json


class HyTechroofdrainsSpider(BaseSpider):

    name = 'hy-techroofdrains'
    allowed_domains = ['hy-techroofdrains.com']
    start_urls = [
        'http://www.hy-techroofdrains.com',
        'http://www.hy-techroofdrains.com/manufacturers/wizards-workshop',
        'http://hy-techroofdrains.com/drains/roof-drains'
    ]


    def parse(self, response):

        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        chk_opts_categories = [
            'hy-techroofdrains.com/manufacturers/wizards-workshop',
            'hy-techroofdrains.com/drains/roof-drains'
        ]

        chk_opts = False
        for cat in chk_opts_categories:
            if cat in response.url:
                chk_opts = True
                break

#        if chk_opts:
#            categories = hxs.select('//div[contains(@class, "category-description")]//a/@href').extract()
#            for url in categories:
#                yield Request(urljoin_rfc(base_url, url),
#                              callback=self.parse_products, meta={'chk_opts': True})
        if chk_opts:
            categories = hxs.select('//a[text()="Manufacturers"]/following::ul[1]//a/@href').extract()
            for url in categories:
                yield Request(urljoin_rfc(base_url, url),
                              callback=self.parse_products, meta={'chk_opts': True})
        else:
            categories = hxs.select('//ul[@id="secondNav"]/li/a/@href').extract()
            for url in categories:
                yield Request(urljoin_rfc(base_url, url), callback=self.parse_products)


    def parse_products(self, response):

        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        sub_cats = hxs.select('//ul[@class="subcats"]/li/a/@href').extract()
        for sub_cat in sub_cats:
            yield Request(urljoin_rfc(base_url, sub_cat), callback=self.parse_products, meta=response.meta)

        products = hxs.select('//h2[@class="product-name"]/a/@href').extract()

        if products:

            category = hxs.select('//div[contains(@class, "category-title")]/h1/text()').extract()
            category = category[0] if category else ''
            meta = response.meta.copy()
            meta['category'] = category
            for url in products:
                yield Request(
                    urljoin_rfc(base_url, url),
                    callback=self.parse_item,
                    meta=meta
                )

        next = hxs.select('//a[contains(@class, "next")]/@href').extract()
        if next:
            yield Request(next[0], callback=self.parse_products, meta=response.meta)


    def parse_item(self, response):

        hxs = HtmlXPathSelector(response)
        image_url = hxs.select('//img[@id="image-main"]/@src').extract()
        image_url = image_url[0] if image_url else ''
        identifier = hxs.select('//input[@name="product"]/@value').extract()
        identifier = identifier[0] if identifier else ''

        brands = hxs.select('//li/a[contains(@href, "manufacturers")]/text()').extract()

        category = response.meta.get('category', "")

        items = hxs.select("//div[@class='product-view']")
        for item in items:
            product_name = item.select("//div[@class='product-name']/h1/text()").extract()[0].strip()
            url = response.url
            price = item.select(".//div[@class='price-box']//"
                                "span[@class='price']/text()").extract()
            if not price:
                price = item.select('.//*[@class="price-from"]/*[@class="price"]/text()').extract()
            if not price:
                price = item.select(".//form/div[@id='pageTitle']/"
                                    "div[@id='addToCart']//"
                                    "div[@class='price-box']/"
                                    "span[@class='price']/text()").extract()
            price = price[0].strip()

            if response.meta.get('chk_opts', True):
                select_options = hxs.select('//*[@id="product-options-wrapper"]/dl/dt[contains(label/text(), "Select Size") or contains(label/text(), "Select Outlet Type") or contains(label/text(), "Select Dome Option") or contains(label/text(), "Select Mounting Option")]/following-sibling::dd[1]//select')
                if select_options:
                    product_loader = ProductLoader(item=Product(), response=response)
                    product_loader.add_value('identifier', identifier)
                    product_loader.add_value('name', product_name)
                    brand = self._get_brand(brands, product_name)
                    product_loader.add_value('brand', brand)
                    product_loader.add_value('url', url)
                    if brand and brand.upper() != category.upper():
                        category = category.replace(brand, '').strip()
                    product_loader.add_value('category', category)
                    product_loader.add_value('image_url', image_url)
                    product_loader.add_value('price', price)
                    product = product_loader.load_item()

                    yield product

                    all_options = []
                    for select_input in select_options:
                        option_name_selected = select_input.select('parent::div/parent::dd/preceding-sibling::dt/label/text()').extract()[-1]
                        # if 'select outlet type' in option_name_selected.lower():
                        #     all_options.append(zip(select_input.select('option[contains(text(), "No Hub Outlet")]/@value').extract(),
                        #                            select_input.select('option[contains(text(), "No Hub Outlet")]/text()').extract()))
                        # elif 'select dome options' in option_name_selected.lower():
                        #     all_options.append(zip(select_input.select('option[contains(text(), "Cast Iron Dome")]/@value').extract(),
                        #                            select_input.select('option[contains(text(), "Cast Iron Dome")]/text()').extract()))
                        # else:
                        if "mounting option" in option_name_selected.lower():
                            all_options.append(zip(select_input.select('option/@value').extract()[1:] + ["nomounting"],
                                                   select_input.select('option/text()').extract()[1:] + ["No Mounting Options"]))
                        else:
                            all_options.append(zip(select_input.select('option/@value').extract()[1:],
                                                   select_input.select('option/text()').extract()[1:]))
                    for options in itertools.product(*all_options):
                        # Remove unselected options
                        options_cleaned = filter(lambda opt: opt[0], options)
                        if options_cleaned:
                            new_item = Product(product)
                            current_identifier = new_item['identifier']
                            current_name = new_item['name']
                            current_price = float(new_item['price'])
                            for value, desc in options_cleaned:
                                opt_price = re.search(r'(\+\$([\d.,]+))', desc)
                                if opt_price:
                                    current_price += float(opt_price.groups()[1])
                                    desc = desc.replace(opt_price.groups()[0], '').strip()
                                current_identifier += '-' + value
                                current_name += ' ' + desc
                            new_item['identifier'] = current_identifier
                            new_item['name'] = current_name
                            new_item['price'] = Decimal(str(current_price))
                            yield new_item
            else:
                product_config_reg = re.search('var spConfig = new Product.Config\((\{.*\})\);', response.body)

                if product_config_reg:
                    products = json.loads(product_config_reg.group(1))
                    for identifier, product in products['childProducts'].items():
                        product_loader = ProductLoader(item=Product(), response=response)
                        if identifier:
                            product_loader.add_value('identifier', identifier)

                        product_loader.add_value('price', product[u'finalPrice'])
                        option_name = product_name
                        for attr_id, attribute in products[u'attributes'].items():
                            for option in attribute['options']:
                                if identifier in option['products']:
                                    option_name += ' ' + option['label']

                        product_loader.add_value('name', option_name)
                        product_loader.add_value('url', url)
                        brand = self._get_brand(brands, option_name)
                        product_loader.add_value('brand', brand)
                        if brand and brand.upper() != category.upper():
                            category = category.replace(brand, '').strip()
                        product_loader.add_value('category', category)
                        # l.add_value('sku', sku)
                        product_loader.add_value('image_url', image_url)
                        yield product_loader.load_item()

                       # self.save_attr(attr_codes)
                else:
                    product_loader = ProductLoader(item=Product(), response=response)
                    product_loader.add_value('identifier', identifier)
                    product_loader.add_value('name', product_name)
                    brand = self._get_brand(brands, product_name)
                    product_loader.add_value('brand', brand)
                    product_loader.add_value('url', url)
                    if brand and brand.upper() != category.upper():
                        category = category.replace(brand, '').strip()
                    product_loader.add_value('category', category)
                    product_loader.add_value('image_url', image_url)
                    product_loader.add_value('price', price)
                    yield product_loader.load_item()

    def save_attr(self, attr):
        handle = open('attrs', 'w+')
        if isinstance(attr, list):
            for line in attr:
                handle.write(line)
                handle.write("\n")
        else:
            handle.write(attr)
            handle.write("\n")
        handle.close()

    def _get_brand(self, brands, name):
        for b in brands:
            if b.upper() in name.upper():
                return b
        return ''
