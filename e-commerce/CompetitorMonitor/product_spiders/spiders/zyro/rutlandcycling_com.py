from scrapy.spider import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor
from scrapy.selector import HtmlXPathSelector
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from urlparse import urljoin as urljoin_rfc
from scrapy.utils.response import get_base_url
from product_spiders.utils import extract_price
from scrapy.http import Request


class RutlandcyclingSpider(CrawlSpider):
    name = 'zyro-rutlandcycling.com'
    allowed_domains = ['rutlandcycling.com']
    start_urls = ('http://www.rutlandcycling.com',)
    
    rules = (
        Rule(LinkExtractor(restrict_css='.ctrNavigation, #lnkNextTop')),
        Rule(LinkExtractor(restrict_xpaths='//div[@itemtype="http://schema.org/Product"]'), callback='parse_product')
        )

    def _parse(self, response):
        for url in response.css('.ctrNavigation a::attr(href)').extract():
            yield Request(response.urljoin(url), callback=self.parse)

        for url in response.xpath('//div[@itemtype="http://schema.org/Product"]//a/@href').extract():
            yield Request(response.urljoin(url), callback=self.parse_product)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        name = response.xpath('//h1/text()').extract()[0]
        identifier = response.xpath('//*[@id="currentProduct"]/@value').extract()[0]
        sku = response.xpath('//p[contains(., "Code")]/span[@class="seasonCode"]/text()').extract()
        sku = sku[0] if sku else ''
        brand = response.xpath('//p[contains(., "Brand")]/span[@class="seasonCode"]/text()').extract()
        brand = brand[0] if brand else ''
        image_url = response.css('.mainImages ::attr(data-image)').extract()
        category = response.xpath('//div[@class="breadcrumbs"]//a/text()').extract()[1:-1]

        products = response.xpath('//div[@class="clAttributeGridContainer"]/div')

        for product in products:
            product_loader = ProductLoader(item=Product(), selector=product)
            p_name = product.select('div[@id="attName"]/div/text()').extract()[0]
            p_name = name + ' ' + p_name.replace('On Sale - ', '')
            p_identifier = product.select('div[@id="attCode"]/text()').extract()[0]
            price = product.select('div[@id="attPrice"]/span[@id]/text()').extract()[0]
            price = extract_price(price)
            out_of_stock = product.select('div[@id="attStockMessage"]/span[@class="OutofStockCSS"]').extract()

            product_loader.add_value('identifier', identifier + '_' + p_identifier)
            product_loader.add_value('name', p_name)
            product_loader.add_value('sku', sku)
            if image_url:
                product_loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
            product_loader.add_value('price', price)
            if price < 20:
                product_loader.add_value('shipping_cost', 3.49)
            if out_of_stock:
                product_loader.add_value('stock', 0)
            product_loader.add_value('category', category)
            product_loader.add_value('brand', brand)
            product_loader.add_value('url', response.url)
            product = product_loader.load_item()
            yield product
