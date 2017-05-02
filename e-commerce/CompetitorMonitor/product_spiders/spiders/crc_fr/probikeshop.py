import re

from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest, HtmlResponse
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from product_spiders.utils import extract_price

from product_spiders.spiders.pedalpedal.crcitem import CRCMeta

from product_spiders.items import Product, ProductLoader
from product_spiders.base_spiders.primary_spider import PrimarySpider

class ProBikeShopSpider(PrimarySpider):
    name = 'crc_fr-probikeshop.fr'
    allowed_domains = ['probikeshop.fr', 'www.probikeshop.fr', 'probikeshop.com', 'www.probikeshop.com']
    start_urls = ('http://www.probikeshop.com',)
    csv_file = 'probikeshop_crawl.csv'

    def start_requests(self):
        yield Request('http://www.probikeshop.com', callback=self.change_country)

    def change_country(self, response):
        req = FormRequest.from_response(response, formname='form-customer-preferences',
                                        formdata={'country[countriesId]': '73',
                                                  'currency[id]': '1',
                                                  'language[languagesId]': '20'})
        yield req

    def parse(self, response):
        if not isinstance(response, HtmlResponse):
            return

        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        categories = hxs.select(u'//div[@id="menu_zone"]/ul//a/@href').extract()
        categories += hxs.select(u'//div[@id="menu_cat"]/ul//a/@href').extract()
        for url in categories:
            yield Request(urljoin_rfc(base_url, url))

        # products
        product_urls = hxs.select(u'//div[contains(@class,"product")]/a[span[@class="title"]]/@href').extract()

        for url in product_urls:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product)

        # next page
        next_page = hxs.select('//a[@class="next page-numbers"]/@href').extract()
        if next_page:
            yield Request(urljoin_rfc(base_url, next_page[0]))

    def parse_product(self, response):
        if not isinstance(response, HtmlResponse):
            return

        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        product_code = re.search('/(\d+)\.html', response.url).group(1)
        product_name = hxs.select(u'//div[@id="title_product"]//h1[@class="title"]/text()').extract()
        image_url = hxs.select('//div[@id="prod-img-slider"]//img/@src').extract()
        price = hxs.select(u'//span[@itemprop="price"]/@content').extract()
        if not price:
            price = hxs.select(u'//span[@id="mainprice"]//span[@class="price2"]/text()').extract()
            if price:
                price = re.sub('[^,\d]', '', price[0]).replace(",", ".")
        else:
            price = price[0]
        category = hxs.select('//div[@id="breadcrumb"]/span/a/span/text()').extract()

        brand = hxs.select('//a[@class="logo"]/@title').extract()

        base_rrp = self.extract_rrp(hxs)

        options = hxs.select('//select[@class="variantSelect"]/option')
        for option in options[1:]:
            product_loader = ProductLoader(response=response, item=Product())
            option_id = option.select('./@value')[0].extract()
            product_loader.add_value('identifier', '{}.{}'.format(product_code, option_id))
            product_loader.add_value('sku', product_code)
            option_name = re.sub(' {2,}', ' ', option.select(u'./text()')[0].extract().strip())
            product_loader.add_value('name', u'{} {}'.format(product_name[0], option_name))
            product_loader.add_value('url', response.url)
            base_option_price = float(option.select(u'./@title')[0].extract())
            option_price = '{:.2f}'.format(float(price) + base_option_price)
            product_loader.add_value('price', str(option_price))
            if image_url:
                product_loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
            if len(category) > 1:
                product_loader.add_value('category', category[1].strip())
            if brand:
                product_loader.add_value('brand', brand[0].strip().title())

            product = product_loader.load_item()
            try:
                option_rrp =  '{:.2f}'.format(float(base_rrp) + base_option_price)
            except ValueError:
                option_rrp = 0

            metadata = CRCMeta()
            metadata['rrp'] = option_rrp if option_rrp>0 else ''
            product['metadata'] = metadata
            yield product

        if not options:
            product_loader = ProductLoader(response=response, item=Product())
            product_loader.add_value('name', product_name)
            product_loader.add_value('url', response.url)

            if not price:
                product_loader.add_value('price', '0.00')
            else:
                product_loader.add_value('price', price)

            if image_url:
                product_loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))

            if len(category) > 1:
                product_loader.add_value('category', category[1].strip())

            if brand:
                product_loader.add_value('brand', brand[0].strip().title())

            product_loader.add_value('identifier', product_code)
            product_loader.add_value('sku', product_code)

            product = product_loader.load_item()
            metadata = CRCMeta()
            metadata['rrp'] = base_rrp if base_rrp>0 else ''
            product['metadata'] = metadata
            yield product

    def extract_rrp(self, hxs):
        rrp = hxs.select('//span[@class="aulieu2"]/text()').extract()
        rrp = str(extract_price(rrp[0])) if rrp else ''
        return rrp
