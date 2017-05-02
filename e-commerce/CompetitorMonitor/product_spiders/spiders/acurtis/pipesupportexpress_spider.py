import itertools

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest

from product_spiders.items import Product, ProductLoader

from product_spiders.utils import extract_price


class PipeSupportExpressSpider(BaseSpider):
    name = "acurtis-pipesupportexpress.com"
    allowed_domains = ["pipesupportexpress.com"]
    start_urls = ('http://pipesupportexpress.com',)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        categories = hxs.select('//div[@id="categoryGrid"]/table/tr/td/div[@class="title"]/a')
        for category in categories:
            category_name = category.select('text()').extract()[0]
            category_url = category.select('@href').extract()[0]
            yield Request(category_url, meta={'category_name': category_name})

        products = hxs.select('//div[@class="productContainer"]/div/div[@class="title"]/a/@href').extract()
        for product_url in products:
            yield Request(product_url, callback=self.parse_product, meta=response.meta)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        image_url = hxs.select('//meta[@itemprop="image"]/@content').extract()
        image_url = image_url[0] if image_url else ''

        brand = hxs.select('//meta[@itemprop="brand"]/@content').extract()
        brand = brand[0] if brand else ''
 
        category = response.meta.get('category_name')
        sku = ''.join(hxs.select('//div[@itemprop="sku"]/text()').extract()).strip()

        product_id = hxs.select('//input[@name="productID"]/@value').extract()[0]
        name = ''.join(hxs.select('//h2[@itemprop="name"]/text()').extract()).strip()
      
        base_price = extract_price(''.join(hxs.select('//div[@id="price" and @class="form-field"]/text()').extract()).strip())
        options = self.get_options(response)
        if options:
            for option in options:
                loader = ProductLoader(item=Product(), response=response)
                loader.add_value('name', name + ' ' + option[1])
                loader.add_value('brand', brand)
                loader.add_value('category', category)
                loader.add_value('sku', sku)
                loader.add_value('identifier', product_id + option[0])
                loader.add_value('url', response.url)
                loader.add_value('image_url', image_url)
                final_price = base_price + option[2]
                loader.add_value('price', final_price)
                if final_price<0:
                    loader.add_value('stock', 0)
                yield loader.load_item()
        else:
            loader = ProductLoader(item=Product(), response=response)
            loader.add_value('name', name)
            loader.add_value('brand', brand)
            loader.add_value('category', category)
            loader.add_value('sku', sku)
            loader.add_value('identifier', product_id)
            loader.add_value('url', response.url)
            loader.add_value('image_url', image_url)
            loader.add_value('price', base_price)
            if base_price<0:
                loader.add_value('stock', 0)
            yield loader.load_item()

    def get_options(self, response):
        hxs = HtmlXPathSelector(response)
        options = []
        options_containers =  hxs.select('//div[contains(@class, "personalizationContainer")]')

        combined_options = []
        for options_container in options_containers:
            option_list = options_container.select('div/select[contains(@id, "persInput")]')
            option_label = options_container.select('div[contains(@id, "personalizationLabel")]/text()').extract()[0].strip()
            element_options = []
            for option in option_list.select('option[@value!=""]'):
                option_id = option.select('@value').extract()[0]
                option_split = option.select('text()').extract()[0].split(' (')
                option_desc = option_split[0]
                if len(option_split)>1:
                    price = extract_price(option_split[1])
                else:
                    price = 0
                element_options.append((option_id, option_label + ' ' + option_desc, price))
            combined_options.append(element_options)
            
        combined_options =  list(itertools.product(*combined_options))
        for combined_option in combined_options:
            name, price, option_id = '', 0, ''
            for option in combined_option:
                option_id = option_id + '-' + option[0]
                name = name + ' - ' + option[1]
                price = price + option[2]
            options.append((option_id, name, price))
        return options
