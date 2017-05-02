from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc
from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader
import re
import json
from decimal import Decimal


class JohnsonrosstackleSpider(BaseSpider):
    name = u'johnsonrosstackle.co.uk'
    allowed_domains = [ u'johnsonrosstackle.co.uk']
    start_urls = [
        u'http://johnsonrosstackle.co.uk/sitemap.php',
    ]

    brands = []

    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        self.brands = response.xpath('//select[@id="manufacturer_list"]/option[@value!="0"]/text()').extract()
        self.brands.sort(key=lambda b: len(b), reverse=True)

        categories = response.css('div.categTree').xpath('.//li[not(ul)]/a/@href').extract()
        for category in categories:
            url = urljoin_rfc(get_base_url(response), category)
            # Request all products to be listed. Set number of products parameter to enough high
            yield Request(url, callback=self.parse_category)

    def parse_category(self, response):
        hxs = HtmlXPathSelector(response)

        products_xpath = '//ul[@id="product_list"]/li//h3/a/@href'

        products = response.css('div.product_list h5 a::attr(href)').extract()
        for url in products:
            yield Request(url, callback=self.parse_product)


        pages = response.css('ul.pagination a::attr(href)').extract()
        for page in pages:
            yield Request(response.urljoin(page), callback=self.parse_category)

    def parse_product_base(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        image_xpath = '//div[@id="image-block"]//img[@itemprop="image"]/@src'

        breadcrumb = response.css('div.breadcrumb a span::text').extract()
        if len(breadcrumb) > 0:
            category = breadcrumb.pop().strip()
        else:
            category = ''

        try:
            name = response.css('div.primary_block h1::text').extract_first().strip()
        except:
            return

        product_brand = ''
        for brand in self.brands:
            if brand.lower() in category.lower() or name.lower().startswith(brand.lower()):
                product_brand = brand
                break

        allow_buy_out_stock = re.search('var allowBuyWhenOutOfStock = true;', response.body)

        image = hxs.select(image_xpath).extract().pop()
        product_url = urljoin_rfc(base_url, response.url)
        image_url = urljoin_rfc(base_url, image)

        # "var quantityAvailable = 7" means there are in total 7 products available in stock
        quantity = re.search('var quantityAvailable\D+(\d+)', response.body)
        product_id = re.search('var id_product\D+(\d+)', response.body)

        price = response.xpath('//span[@id="our_price_display"]//text()').extract()

        if price:
            price = price.pop()
        else:
            price = '0.00'

        loader = ProductLoader(response=response, item=Product())
        loader.add_value('url', product_url)
        loader.add_value('name', name)
        loader.add_value('brand', product_brand)
        loader.add_value('image_url', image_url)
        loader.add_value('price', price.replace(' ', '').replace(',', '.'))
        loader.add_value('category', category)
        loader.add_xpath('sku', '//p[@id="product_reference"]/span/text()')

        if product_id:
            loader.add_value('identifier', product_id.group(1))
        else:
            loader.add_xpath('identifier', '//form//input[@name="id_product"]/@value')

        stock = response.xpath('//span[@id="availability_value"]/text()').extract_first()
        
        if stock and stock.title() != 'In Stock':
            loader.add_value('stock', 0)

        return loader.load_item()

    def parse_product(self, response):
        prod = self.parse_product_base(response)
        currencyRate = re.search('var currencyRate\D+([\d\.]+)', response.body)
        if currencyRate:
            currencyRate = Decimal(currencyRate.group(1))
        else:
            currencyRate = 1

        productPriceTaxExcluded = re.search("var productPriceTaxExcluded\D+([\d\.]+)", response.body)
        if productPriceTaxExcluded:
            productPriceTaxExcluded = Decimal(productPriceTaxExcluded.group(1))
        else:
            productPriceTaxExcluded = 0

        idDefaultImage = re.search('var idDefaultImage=(\d+)', response.body)
        if idDefaultImage:
            idDefaultImage = idDefaultImage.group(1)

        data = response.xpath('//script/text()').re_first('var combinations=({.+?});')
        if not data:
            yield prod
            return
        
        data = json.loads(data)
        for identifier in data:
            loader = ProductLoader(Product(), response=response)
            loader.add_value(None, prod)
            loader.replace_value('identifier', '-'.join((prod['identifier'], identifier)))
            loader.replace_value('sku', data[identifier]['reference'])
            loader.replace_value('stock', data[identifier]['quantity'])
            option_price = Decimal(data[identifier]['price'])
            if option_price != 0:
                price = (option_price * Decimal('1.2')).quantize(Decimal('0.01'))
                loader.replace_value('price', price)
            attr_values = data[identifier]['attributes_values']
            for attr in sorted(attr_values):
                loader.add_value('name', attr_values[attr])
            image_url = prod['image_url'].replace(idDefaultImage, str(data[identifier]['id_image']))
            yield loader.load_item()
            