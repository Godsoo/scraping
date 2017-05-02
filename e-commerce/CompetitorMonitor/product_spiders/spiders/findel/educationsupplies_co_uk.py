"""
Ticket link: https://www.assembla.com/spaces/competitormonitor/tickets/5097

Monitor all products. Extract all product options.
"""
import scrapy
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader


class EducationsuppliesSpider(scrapy.Spider):
    name = 'findel-educationsupplies.co.uk'
    allowed_domains = ['educationsupplies.co.uk']
    start_urls = ('http://products.educationsupplies.co.uk/search?view=grid&cnt=60',)

    def parse(self, response):
        for url in response.xpath('//div[@class="pages"]//a[@class="next i-next"]/@href').extract():
            yield scrapy.Request(response.urljoin(url), callback=self.parse)

        for url in response.xpath('//div[@class="category-products"]//li//h2/a/@href').extract():
            yield scrapy.Request(response.urljoin(url), callback=self.parse_product)

    @staticmethod
    def parse_product(response):
        identifier = response.xpath('//div[@class="nosto_product"]/span[@class="product_id"]/text()').extract_first()
        name = response.xpath('//div[@class="nosto_product"]/span[@class="name"]/text()').extract_first()
        price =response.xpath('//div[@class="nosto_product"]/span[@class="price"]/text()').extract_first()
        category = response.xpath('//div[@class="nosto_product"]/span[@class="category"]/text()').extract_first()
        category = category.split('/')[1:]
        image_url = response.xpath('//div[@class="nosto_product"]/span[@class="image_url"]/text()').extract_first()
        variations = response.xpath('//a[@class="button btn-cart basket-below"]')
        if variations:
            variations = response.xpath('//*[@id="super-product-table"]/tbody/tr')
            for variant in variations:
                o_name = name
                for option in variant.xpath('./td[@fil-id!=""]/span/text()').extract():
                    if option != 'Yes':
                        o_name += ' ' + option
                o_id = variant.xpath('.//input/@name').extract_first()
                if not o_id:
                    continue
                o_id = o_id.replace('super_group[', '')[:-1]
                o_sku = variant.xpath('.//span[@class="sku"]/text()').extract_first()
                o_price = variant.xpath('.//span[@class="break-price"]/text()').extract_first()
                loader = ProductLoader(item=Product(), response=response)
                loader.add_value('name', o_name)
                loader.add_value('identifier', o_id)
                loader.add_value('sku', o_sku)
                loader.add_value('category', category)
                loader.add_value('url', response.url)
                loader.add_value('image_url', response.urljoin(image_url))
                loader.add_value('price', o_price)
                option_item = loader.load_item()
                yield option_item
        else:
            sku = response.xpath('//span[@class="product-ids"]/text()').extract_first()
            if sku:
                sku = sku.replace('Item code: ', '')
            loader = ProductLoader(item=Product(), response=response)
            loader.add_value('name', name)
            loader.add_value('identifier', identifier)
            loader.add_value('sku', sku)
            loader.add_value('category', category)
            loader.add_value('url', response.url)
            loader.add_value('image_url', response.urljoin(image_url))
            loader.add_value('price', price)
            option_item = loader.load_item()
            yield option_item
