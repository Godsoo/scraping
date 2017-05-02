import random
import json

from scrapy.spider import SitemapSpider, Rule
from scrapy.linkextractors import LinkExtractor
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc
from product_spiders.items import Product
from tigerchefloader import TigerChefLoader as ProductLoader

from tigerchefitems import TigerChefMeta

class FoodServiceWarehouseSpider(SitemapSpider):
    name = 'foodservicewarehouse.com'
    allowed_domains = ['foodservicewarehouse.com']
    start_urls = ('http://www.foodservicewarehouse.com',)
    sitemap_urls = ['http://www.foodservicewarehouse.com/sitemap_index.xml.gz',
                    'http://www.foodservicewarehouse.com/sitemap_index_aggregate.xml.gz']
    sitemap_rules = [('^(?:(?!/PDFs/|/blog/).)*$', 'parse')]

    PROXIES = ['http://23.19.154.246:3128',
               'http://23.19.154.247:3128',
               'http://23.19.154.248:3128',
               'http://23.19.154.249:3128',
               'http://23.19.154.250:3128',
               'http://23.19.188.247:3128',
               'http://23.19.188.248:3128',
               'http://23.19.188.249:3128',
               'http://23.19.188.250:3128']

    CART_PROXY = 'http://23.19.188.246:3128'
    
    _rules = (
        Rule(LinkExtractor(
            restrict_css='.mega-menu, .category-slider, .categories'), process_request='proxy_request',
            callback='parse_products',
            follow=True
            ),
        )

    def proxy_request(self, request):
        request.meta['proxy'] = random.choice(self.PROXIES)
        log.msg('Processing request to %s using proxy %s' % (request.url, request.meta['proxy']))
        return request

    def _start_requests(self):
        req = Request('http://www.foodservicewarehouse.com')
        yield self.proxy_request(req)

    def parse(self, response):
        data = response.xpath('//script/text()').re("products', (\[{.+}\])")
        if not data:
            return
        list_of_data = json.loads(data[0])
        for data in list_of_data:
            loader = ProductLoader(item=Product(), response=response, spider_name=self.name)
            loader.add_xpath('url', '//link[@rel="canonical"]/@href')
            loader.add_value('sku', data['sku'])
            loader.add_value('identifier', str(data['sqlProductID']) + '_' + data['sku'])
            loader.add_value('name', data['name'])
            loader.add_value('price', data['price'])
            category = response.css('.breadcrumb a::text').extract()
            loader.add_value('category', category[-1])
            loader.add_value('brand', data['manufacturer'])
            loader.add_xpath('image_url', '//meta[@property="og:image"]/@content')
            loader.add_value('stock', int(data['inventoryStatus'] != 3))
            yield loader.load_item()

    def parse_subcats(self, response):
        hxs = HtmlXPathSelector(response)
        # subcategories
        cats = hxs.select('//ul[contains(@class,"block-grid")]//li//a/@href').extract()
        cats += hxs.select('//div[contains(@class,"I1")]//a/@href').extract()
        cats += hxs.select('//*[@class="amch2"]/a/@href').extract()
        # pagination
        cats += hxs.select('//div[@class="pagination"]//li/a/@href').extract()
        for cat in cats:
            req = Request(urljoin_rfc(get_base_url(response), cat), self.parse_subcats)
            yield self.proxy_request(req)
        for product in self.parse_products(response, hxs):
            yield product

    def parse_products(self, response, hxs):
        products = response.css('.product-result')
        for product in products:
            loader = ProductLoader(selector=product, item=Product(), spider_name=self.name)
            url = product.select('.//a/@href').extract()
            if not url:
                self.log('ERROR: no product URL found! URL:{}'.format(response.url))
                continue
            else:
                url = urljoin_rfc(get_base_url(response), url[0])
                loader.add_value('url', url)

            sku = product.select('.//a/text()').re('\((.*?)\)')
            if not sku:
                self.log('ERROR: no SKU found!')
            else:
                loader.add_value('sku', sku[0])
                product_id = product.select('.//a/@href').re('p(\d+)\.aspx')
                if not product_id:
                    self.log('ERROR: no product ID found!')
                else:
                    loader.add_value('identifier', product_id[0] + '_' + sku[0])
            product_image = product.select('.//a/img/@psrc').extract()
            if not product_image:
                product_image = product.select('.//div/img/@src').extract()
                if not product_image:
                    self.log('ERROR: no product Image found!')
            if product_image:
                image = urljoin_rfc(get_base_url(response), product_image[0].strip())
                loader.add_value('image_url', image)
            price = ''.join(product.select('./div[contains(@class,"-price")]/text()').extract()).strip()
            check_cart = False
            if 'Instant Rebate' in price or 'Add to Cart' in price:
                price = '0.0'
                check_cart = True
            if not price:
                price = ''.join(product.select('./div[contains(@class,"-price")]/span/text()').extract()).strip()
                if not price:
                    self.log('ERROR: no price found! URL:{} Product URL:{}'.format(response.url, url))
                    continue
            loader.add_value('price', price.strip())
            category = product.select('//div[contains(@class, "content")]/h1/text()').extract()
            if not category:
                self.log("ERROR: category not found")
            else:
                loader.add_value('category', category[0].strip())

            name = product.select('.//a/text()').extract()[0]
            loader.add_value('name', name)

            brand = name.split(' (')[0]

            loader.add_value('brand', brand)

            sold_as = product.select('div//span[@class="unit-of-sale"]/text()').extract()
            sold_as = sold_as[0].split('/')[-1] if sold_as else '1 ea'

            metadata = TigerChefMeta()
            metadata['sold_as'] = sold_as

            if check_cart:
                sku_id = product.select('div[@class="adcWinnowedItem"]/button/@atc-skuid').extract()[0]
                add_cart_url = "https://www.foodservicewarehouse.com/ViewCart/AddSkuToCart?skuID=" + sku_id + "&quantity=1"
                req = Request(add_cart_url, dont_filter=True, callback=self.parse_cart, meta={'loader':loader, 'metadata':metadata, 'sku_id': sku_id})
                req.meta['proxy'] = self.CART_PROXY
                yield req
                req = Request('https://www.foodservicewarehouse.com/ViewCart/RemoveAll/', dont_filter=True, callback=self.parse_cart, meta={'clean_cart':True})
                req.meta['proxy'] = self.CART_PROXY
                yield req
            else:
                product = loader.load_item()
                product['metadata'] = metadata
                yield product

    def parse_cart(self, response):
        hxs = HtmlXPathSelector(response)
        meta = response.meta
        if not meta.get('clean_cart', False):
            loader = meta['loader']
            loader.selector = hxs
            sku_id = meta.get('sku_id')
            qty = hxs.select('//div[@class="row" and div/input[@name="' + sku_id + '"]]/div[@class="large-4 columns text-right"]/input[@class="intInput cqty"]/@value').extract()[0]
            if qty == '1':
                price = ''.join(hxs.select('//div[@class="row" and div/input[@name="' + sku_id + '"]]/div[@class="large-4 columns text-right red-bold-font totalPrice"]/span/text()').extract()).strip().replace(',', '')
                loader.add_value('price', price)
                product = loader.load_item()
                product['metadata'] = meta.get('metadata')
                yield product
