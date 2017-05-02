"""
Ticket link: https://www.assembla.com/spaces/competitormonitor/tickets/5173

Extract all products including product options.
"""
import scrapy
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
import itertools
from scrapy.utils.url import add_or_replace_parameter
import json


class DoorsworldSpider(scrapy.Spider):
    name = 'leaderstores-doorsworld.co'
    allowed_domains = ['doorsworld.co']
    download_delay = 2
    start_urls = ('http://www.doorsworld.co/c/All_Internal_Doors.htm',
                  'http://www.doorsworld.co/c/All_Exterior_Doors.htm',
                  'http://www.doorsworld.co/c/All_Door_Accessories.htm',
                  'http://www.doorsworld.co/c/Patio_Doors.htm',
                  'http://www.doorsworld.co/c/Double_Glazed_Doors.htm',
                  'http://www.doorsworld.co/c/Fire_Doors.htm',
                  'http://www.doorsworld.co/c/Top_Offers.htm')

    def parse(self, response):
        for url in response.xpath('//div[@class="pagination"]/a/@href').extract():
            yield scrapy.Request(response.urljoin(url), callback=self.parse)

        for url in response.css('div.products-list-item-container h2.product_description a::attr(href)').extract():
            yield scrapy.Request(response.urljoin(url), callback=self.parse_product)

    def parse_product(self, response):
        item_id = response.xpath('//*[@id="item_details_item_id"]/@value').extract_first()
        image_url = response.xpath('//*[@id="imageMain"]/@src').extract_first()
        category = response.xpath('//div[@class="ws-breadcrumb shared-width"]//a/text()').extract()
        url = 'http://www.doorsworld.co/ajax.get_exact_product.php?instart_disable_injection=true'
        url = add_or_replace_parameter(url, 'item_id', item_id)
        options_containers = response.xpath('//div[@class="option_container clearfix"]//select')
        if options_containers:
            combined_options = []
            for options_container in options_containers:
                element_options = []
                for option in options_container.xpath('./option[@value!=""]'):
                    option_id = options_container.xpath('./@id').extract_first().rsplit('_',1)[0]
                    option_name = option.xpath('./@value').extract_first()
                    element_options.append((option_id, option_name))
                combined_options.append(element_options)
            if len(options_containers) > 1:
                combined_options = list(itertools.product(*combined_options))
                for combined_option in combined_options:
                    option_url = url
                    for option in combined_option:
                        option_url = add_or_replace_parameter(option_url, 'attributes[{}]'.format(option[0]), option[1])
                    yield scrapy.Request(option_url, callback=self.parse_product_data, meta={'image_url': image_url,
                                                                                             'url': response.url,
                                                                                             'category': category})
            else:
                for option in combined_options[0]:
                    option_url = add_or_replace_parameter(url, 'attributes[{}]'.format(option[0]), option[1])
                    yield scrapy.Request(option_url, callback=self.parse_product_data, meta={'image_url': image_url,
                                                                                             'url': response.url,
                                                                                             'category': category})
        else:
            yield scrapy.Request(url, callback=self.parse_product_data, meta={'image_url': image_url,
                                                                              'url': response.url,
                                                                              'category': category})

    @staticmethod
    def parse_product_data(response):
        data = json.loads(response.body)['data']
        if data:
            brand = data.get('brand')
            category = response.meta.get('category')
            if 'product_name' in data:
                if data.get('item_name') in data.get('product_name'):
                    name = data.get('product_name')
                else:
                    name = data.get('item_name') + ' ' + data.get('product_name')
            else:
                name = data.get('item_name')
            identifier = "{}_{}".format(data.get('item_id'), data.get('id'))
            price = data.get('ourprice')
            image_url = response.meta['image_url']
            url = response.meta['url']
            loader = ProductLoader(item=Product(), response=response)
            loader.add_value('name', name)
            loader.add_value('identifier', identifier)
            loader.add_value('sku', identifier)
            loader.add_value('brand', brand)
            loader.add_value('brand', category)
            loader.add_value('url', url)
            loader.add_value('image_url', response.urljoin(image_url))
            loader.add_value('price', price)
            option_item = loader.load_item()
            yield option_item