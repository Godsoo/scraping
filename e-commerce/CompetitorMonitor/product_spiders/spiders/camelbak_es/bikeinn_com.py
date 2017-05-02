import scrapy
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.utils import extract_price


class BikeinnSpider(scrapy.Spider):
    name = 'camelbak_es-bikeinn.com'
    allowed_domains = ['bikeinn.com']
    start_urls = ('https://www.bikeinn.com/bike',)

    def parse(self, response):
        form_data = {'options': '180'}
        yield scrapy.FormRequest.from_response(response,
                                               formname='paises',
                                               formdata=form_data,
                                               callback=self.parse2,
                                               dont_filter=True)

    def parse2(self, response):
        yield scrapy.Request(
            'https://www.bikeinn.com/index.php?action=listado_productos_subfamilia&id_marca=36&idioma=eng',
            callback=self.parse_categories)

    def parse_categories(self, response):
        for url in response.xpath('//div[@class="paginadoTop"]//a/@href').extract():
            yield scrapy.Request(response.urljoin(url), callback=self.parse_categories)

        for url in response.xpath('//div[contains(@class,"boxProd")]//p[@class="BoxPriceName"]/a/@href').extract():
            yield scrapy.Request(response.urljoin(url), callback=self.parse_product)

    @staticmethod
    def parse_product(response):

        name = response.xpath('//h1[@class="name"]/text()').extract()[0]
        identifier = response.xpath('//meta[@itemprop="sku"]/@content').extract()[0]
        image_url = response.xpath('//*[@id="zoom_01"]/@src').extract()
        category = response.xpath('//*[@id="wayProd"]//a/span/text()').extract()[-3:]
        price = response.xpath('//*[@id="total_dinamic"]/span/text()').extract()[0]
        price = extract_price(price)

        products = response.xpath('//*[@id="datesBuy"]//select[@name="talla_color"]/option')
        for product in products:
            product_loader = ProductLoader(item=Product(), selector=product)
            p_name = product.select('./text()').extract()[0]
            p_name = name if p_name == '- ' else name + ' ' + p_name
            p_identifier = product.select('./@value').extract()[0]
            product_loader.add_value('identifier', identifier + '_' + p_identifier)
            product_loader.add_value('name', p_name)
            product_loader.add_value('sku', identifier + '_' + p_identifier)
            if image_url:
                product_loader.add_value('image_url', response.urljoin(image_url[0]))
            product_loader.add_value('price', price)
            product_loader.add_value('category', category)
            product_loader.add_value('brand', 'CamelBak')
            product_loader.add_value('url', response.url)
            product = product_loader.load_item()
            yield product
