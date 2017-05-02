from scrapy.spider import BaseSpider
from scrapy.selector import Selector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from urlparse import urljoin as urljoin_rfc
from product_spiders.utils import extract_price
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
import json


class WexParkcamerasSpider(BaseSpider):
    name = 'wexphotographic_new-parkcameras.com'
    allowed_domains = ['parkcameras.com']

    start_urls = ['https://www.parkcameras.com']

    def parse(self, response):
        base_url = get_base_url(response)
        cnames = response.xpath('//ul[@class="free-wall"]/li/a/text()').extract()
        urls = response.xpath('//ul[@class="free-wall"]/li/a/@href').extract()
        for cname, url in zip(cnames, urls):
            if cname == 'Brands' or '/used' in url:
                continue
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_products_list)

    def parse_products_list(self, response):
        base_url = get_base_url(response)

        for url in response.xpath('//div[@class="category_tree"]//h3[text()="Category Links"]/../../div//a/@href').extract():
            if '/used' in url:
                continue
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_products_list)

        categories = response.xpath('//ul[@class="breadcrumbs"]/li/a/span/text() | //ul[@class="breadcrumbs"]/li[@class="here"]/text()').extract()[1:]

        for product in response.xpath('//article[@class="product summary stamp 3"]'):
            url = product.xpath('./a/@href').extract()[0]
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product, meta={'categories': categories})

        # pagination
        total_pages = response.xpath('//input[@id="TotalPages"]/@value').extract()
        if not total_pages:
            return
        total_pages = int(total_pages[0])
        page = 2
        if page <= total_pages:
            arrayskini = response.xpath('//input[@id="arrayskini"]/@value').extract()[0]
            filterskini = response.xpath('//input[@id="filterskini"]/@value').extract()[0]
            pagskini = response.xpath('//input[@id="pagskini"]/@value').extract()[0]
            searchid = response.xpath('//input[@id="searchId"]/@value').extract()[0]
            searchstring = response.xpath('//input[@id="searchstring"]/@value').extract()[0]
            signature = response.xpath('//input[@id="signature"]/@value').extract()[0]
            form_data = {
                'action': "pagechange",
                'arrayskini': arrayskini,
                'expanded': [],
                'filters': [],
                'filterskini': filterskini,
                'groupBy': "",
                'max': -1,
                'me': "p",
                'min': -1,
                'page': str(page),
                'pageSize': -1,
                'pagskini': pagskini,
                'rating': -1,
                'refreshFilters': 1,
                'refreshPagination': 1,
                'searchId': searchid,
                'searchstring': searchstring,
                'searchtype': "3",
                'signature': signature,
                'sortBy': -1,
                'top': 0,
                'view': ""
            }
            # self.log('Total pages: {}, Page: {}, Data: {}'.format(total_pages, page, form_data))
            yield Request('https://www.parkcameras.com/ajax/paginationFilter/post',
                          callback=self.parse_products_list_json,
                          body=json.dumps(form_data),
                          headers={'Content-Type': 'application/json',
                                   'Accept': 'application/json',
                                   'X-Requested-With': 'XMLHttpRequest'},
                          method='POST',
                          dont_filter=True,
                          meta={'json': True, 'form_data': form_data, 'categories': categories})

    def parse_products_list_json(self, response):
        base_url = get_base_url(response)
        data = json.loads(response.body)
        if 'There are no products that can be displayed.' in data['Products']:
            return
        categories = response.meta.get('categories')
        hxs = Selector(text=data['Products'])

        for product in hxs.xpath('//article[@class="product summary stamp 3"]'):
            url = product.xpath('./a/@href').extract()[0]
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product, meta={'categories': categories})

        # pagination
        total_pages = int(data['TotalPages'])
        page = int(data['currentPage'])
        page += 1
        if page <= total_pages:
            form_data = response.meta.get('form_data')
            form_data['page'] = str(page)
            # self.log('Total pages: {}, Page: {}, Data: {}'.format(total_pages, page, form_data))
            yield Request('https://www.parkcameras.com/ajax/paginationFilter/post',
                          callback=self.parse_products_list_json,
                          body=json.dumps(form_data),
                          headers={'Content-Type': 'application/json',
                                   'Accept': 'application/json',
                                   'X-Requested-With': 'XMLHttpRequest'},
                          method='POST',
                          dont_filter=True,
                          meta={'json': True, 'form_data': form_data, 'categories': categories})

    def parse_product(self, response):
        base_url = get_base_url(response)
        loader = ProductLoader(response=response, item=Product())
        url = response.url
        loader.add_value('url', urljoin_rfc(base_url, url))
        identifier = url.split('/')[4]
        loader.add_value('identifier', identifier)
        loader.add_value('sku', identifier)
        image_url = response.xpath('//div[@class="prodImg-main"]//img[@class="prodImg"]/@src').extract_first()
        loader.add_value('image_url', image_url)
        name = response.xpath('//h1[@itemprop="name"]/text()').extract()[0]
        loader.add_value('name', name)
        price = extract_price(response.xpath('//meta[@itemprop="price"]/@content').extract()[0])
        loader.add_value('price', price)
        if price < 50:
            loader.add_value('shipping_cost', 2.5)
        categories = response.meta.get('categories')
        categories = response.css('ul.breadcrumbs span::text').extract()[1:-1]
        loader.add_value('category', categories)
        product = loader.load_item()
        yield product