from product_spiders.base_spiders.primary_spider import PrimarySpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader
from urlparse import urljoin as urljoin_rfc
from scrapy.utils.response import get_base_url


class LeisureLakesBikesSpider(PrimarySpider):
    name = 'crc_uk-leisurelakesbikes.com'
    allowed_domains = ['leisurelakesbikes.com']
    start_urls = ('http://www.leisurelakesbikes.com/',)
    csv_file = 'leisurelakesbikes.csv'

    def __init__(self, *args, **kwargs):
        super(LeisureLakesBikesSpider, self).__init__(*args, **kwargs)
        self.identifier_name = {}

    def parse(self, response):
        categories = response.css('.ctrNavigation a::attr(href)').extract()
        for url in categories:
            yield Request(response.urljoin(url), callback=self.parse_list)

    def parse_list(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        #pagination
        next_page = hxs.select('//li[@class="pager-li next"]/a/@href').extract()
        if next_page:
            yield Request(urljoin_rfc(base_url, next_page[0] + '&orderby=5'), callback=self.parse_list)
        #products
        products = response.xpath('//@data-navigationurl').extract()
        for url in products:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product)

    def parse_product(self, response):
        base_url = get_base_url(response)
        image_url = response.xpath('//div[@id="prodInfoLeft"]//@data-image').extract()
        category = response.css('.breadcrumbs.desktop').xpath('.//a/span/text()').extract()[1:]
        category = category[-1] if category else ''
        product_name = response.xpath('//h1[@id="devProductName"]/text()').extract_first()
        identifier = response.xpath('//input[@id="currentProduct"]/@value').extract_first()
        sku = response.xpath('//div[@itemprop="productID"]/text()').extract_first()
        brand = response.xpath('//div[@itemprop="manufacturer"]/text()').extract_first()
        price = response.xpath('//*[@itemprop="price"]/text()').re(r'[\d\.,]+')
        options = response.css('.clAttributeGridContainer').xpath('div')
        for option in options:
            option_id = option.select('.//input[@class="productDetailtQty"]/@id').re('dev-qty-(.*)')[0]
            option_name = option.select('div[@id="attName"]/div/text()').extract_first()
            product_loader = ProductLoader(item=Product(), response=response)

            product_loader.add_value('name', product_name)
            product_loader.add_value('name', option_name)
            product_loader.add_value('identifier', '{}.{}'.format(identifier, option_id))
            product_loader.add_value('shipping_cost', '0.00')
            product_loader.add_value('url', response.url)
            product_loader.add_value('category', category)
            product_loader.add_value('brand', brand)
            option_price = option.select('div[@id="attPrice"]/span[2]/text()').extract_first() or price
            product_loader.add_value('price', option_price)
            product_loader.add_value('sku', sku)

            if option.css('.OutofStockCSS'):
                product_loader.add_value('stock', 0)

            if image_url:
                product_loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))

            prod = product_loader.load_item()

            if prod['identifier'] in self.identifier_name:
                prod['name'] = self.identifier_name[prod['identifier']]
            else:
                self.identifier_name[prod['identifier']] = prod['name']

            yield prod
