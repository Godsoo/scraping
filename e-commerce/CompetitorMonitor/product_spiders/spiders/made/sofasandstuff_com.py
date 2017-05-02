import re
import json
from scrapy import Spider, Request, FormRequest
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.utils import extract_price


def retry_decorator(callback):
    def new_callback(obj, response):
        if response.status in obj.retry_codes:
            yield obj._retry_request(response.request)
        else:
            res = callback(obj, response)
            if res:
                for r in res:
                    yield r
    return new_callback


class SofasandstuffSpider(Spider):
    name = 'made-sofasandstuff.com'
    allowed_domains = ['sofasandstuff.com']
    start_urls = ('http://www.sofasandstuff.com/sofas/',
                  'http://www.sofasandstuff.com/corner-sofas/',
                  'http://www.sofasandstuff.com/sofa-beds/',
                  'http://www.sofasandstuff.com/small-sofas/',
                  'http://www.sofasandstuff.com/products/cant-wait/',
                  'http://www.sofasandstuff.com/in-stock/',
                  'http://www.sofasandstuff.com/on-order/',
                  'http://www.sofasandstuff.com/armchairs/',
                  'http://www.sofasandstuff.com/stools/',
                  'http://www.sofasandstuff.com/beds/products/')
    rotate_agent = True

    sitemap_url = 'http://www.sofasandstuff.com/sitemap.xml'

    handle_httpstatus_list = [500, 501, 502, 503, 504, 400, 408, 404, 403]
    max_retry_times = 10

    def start_requests(self):
        self.retry_codes = self.handle_httpstatus_list
        yield Request(self.sitemap_url, callback=self.parse_sitemap)

    def parse_sitemap(self, response):
        self._sitemap_urls = re.findall(r'<loc>(.*)</loc>', response.body)
        for url in self.start_urls:
            yield Request(url)

    @retry_decorator
    def parse(self, response):
        for item in self.parse_model(response):
            yield item
        # parse categories
        urls = response.xpath('//ul[contains(@class, "product-listing")]/li//a/@href').extract()
        for url in urls:
            yield Request(response.urljoin(url), callback=self.parse)
        urls = response.xpath('//li[contains(@class, "product")]//a/@href').extract()
        for url in urls:
            yield Request(response.urljoin(url), callback=self.parse)
        urls = response.xpath('//article[@class="product"]//a/@href').extract()
        for url in urls:
            yield Request(response.urljoin(url), callback=self.parse)
        urls = response.xpath('//article[@class="stock-fabric-samples-wrapper"]//a/@href').extract()
        for url in urls:
            yield Request(response.urljoin(url), callback=self.parse)
        urls = response.xpath('//div[@class="tabs-wrapper tabs-wrapper-model"]//a/@href').extract()
        for url in urls:
            yield Request(response.urljoin(url), callback=self.parse)

        for url in urls:
            for sm_url in filter(lambda u: url in u.decode('utf-8'), self._sitemap_urls):
                yield Request(sm_url, callback=self.parse)

        products = response.xpath('//div[@class="fabric-swatch" or contains(@class,"fabric-swatch ")]')
        if products:
            p_name = response.xpath('//h1[@class="h2"]/text()').extract()[0].strip()
            for product in products:
                url = product.xpath('./a/@id').extract()
                if url:
                    url = product.xpath('./a/@href').extract()
                    yield Request(response.urljoin(url[0]), callback=self.parse_product)
                else:
                    product_loader = ProductLoader(item=Product(), response=response)
                    identifier = product.xpath('.//input[@name="swatchNodeId"]/@value').extract()[0]
                    identifier += '_' + product.xpath('.//input[@name="swatchCurrentSize"]/@value').extract()[0]
                    product_loader.add_value('identifier', identifier)
                    name = product.xpath('.//input[@name="swatchDescription"]/@value').extract()[0]
                    product_loader.add_value('name', p_name + ' ' + name)
                    product_loader.add_value('sku', identifier)
                    image_url = product.xpath('./a/@href').extract()
                    if image_url:
                        product_loader.add_value('image_url', response.urljoin(image_url[0]))
                    price = product.xpath('.//input[@name="swatchPrice"]/@value').extract()[0]
                    price = extract_price(price)
                    product_loader.add_value('price', price)
                    product_loader.add_value('shipping_cost', 49)
                    category = response.xpath('//div[@class="breadcrumbs"]//a/text()').extract()[1:]
                    product_loader.add_value('category', category)
                    product_loader.add_value('url', response.url)
                    product = product_loader.load_item()
                    yield product
        else:
            options = response.xpath('//div[@class="step-2-radio-options"]//a')
            if options:
                p_name = response.xpath('//h1[@class="h2"]/text()').extract()[0].strip()
                image_url = response.xpath('//ul[@class="classic-images-gallery"]//img/@src').extract()
                category = response.xpath('//div[@class="breadcrumbs"]//a/text()').extract()[1:]
                sub_options = response.xpath('//div[contains(@class, "radio-group ")]')
                for option, sub_options in zip(options, sub_options):
                    name1 = option.xpath('./text()').extract()[0]
                    identifier1 = sub_options.xpath('.//input[@type="hidden"]/@value').extract()[0]
                    for option2 in sub_options.xpath('.//div[@class="form-field-wrapper radio"]'):
                        identifier2 = option2.xpath('.//input[@type="radio"]/@id').extract()[0]
                        name2 = option2.xpath('.//h5/text()').extract()[0]
                        price = option2.xpath('.//span[@class="green"]/text()').extract()[0]
                        product_loader = ProductLoader(item=Product(), response=response)
                        product_loader.add_value('identifier', identifier1 + '_' + identifier2)
                        product_loader.add_value('name', p_name + ' ' + name1 + ' ' + name2)
                        product_loader.add_value('sku', identifier1 + '_' + identifier2)
                        if image_url:
                            product_loader.add_value('image_url', response.urljoin(image_url[0]))
                        price = extract_price(price)
                        product_loader.add_value('price', price)
                        product_loader.add_value('shipping_cost', 49)
                        product_loader.add_value('category', category)
                        product_loader.add_value('url', response.url)
                        product = product_loader.load_item()
                        yield product
            else:
                options = response.xpath('//ul[@class="classic-tabs bx-thumbails"]/li/a/@onclick').extract()
                if options:
                    product_loader = ProductLoader(item=Product(), response=response)
                    p_name = response.xpath('//h1[@class="h2 productTitle"]/text()').extract()[0].strip()
                    product_loader.add_value('name', p_name)
                    product_loader.add_value('shipping_cost', 49)
                    category = response.xpath('//div[@class="breadcrumbs"]//a/text()').extract()[1:]
                    product_loader.add_value('category', category)
                    product_loader.add_value('url', response.url)
                    product = product_loader.load_item()
                    for option in options:
                        # slider.goToSlide(2);UpdateFilters(101916, 2);
                        node_id = option.split('UpdateFilters(')[1].split(',')[0]
                        formdata = {'nodeId': node_id}
                        yield FormRequest('http://www.sofasandstuff.com/static/fabriclisting.ashx',
                                          method='POST', callback=self.parse_product2,
                                          meta={'product': product}, formdata=formdata)

                else:
                    identifier = response.xpath('//input[@name="nodeId"]/@value').extract()
                    if identifier:
                        product_loader = ProductLoader(item=Product(), response=response)
                        product_loader.add_value('identifier', identifier[0])
                        name_parts = response.xpath('//div[@class="tabs-wrapper"]//li[@class="active"]//div/text()').extract()
                        name2 = ' '.join([part.strip() for part in name_parts])
                        name1 = ''.join(response.xpath('//h1[@class="productTitle"]//text()').extract())
                        product_loader.add_value('name', name1 + ' ' + name2)
                        product_loader.add_value('sku', identifier[0])
                        image_url = response.xpath('//div[@class="sofa-images"]/img/@src').extract()
                        if image_url:
                            product_loader.add_value('image_url', response.urljoin(image_url[0]))
                        price = response.xpath('//div[@class="cost"]/div[@class="now"]/text()').extract()[0]
                        price = extract_price(price)
                        product_loader.add_value('price', price)
                        product_loader.add_value('shipping_cost', 49)
                        category = response.xpath('//div[@class="breadcrumbs1"]//a/text()').extract()
                        category = [c.replace(' >', '').strip() for c in category]
                        product_loader.add_value('category', category)
                        product_loader.add_value('url', response.url)
                        product = product_loader.load_item()
                        yield product

    @retry_decorator
    def parse_model(self, response):
        self.log('parse_model')
        version = re.findall(r'var version = "(\d+)";', response.body)
        sizes_url = 'http://www.sofasandstuff.com/static/products/GetProductInfo.ashx?' \
                    'action=size&modelId={model_id}&fabricId='
        model_id = response.xpath('//input[@type="hidden" and @id="modelId"]/@value').extract()
        if model_id:
            yield Request(sizes_url.format(model_id=model_id[0]),
                          callback=self.parse_size,
                          meta={'model_id': model_id[0],
                                'version': version[0] if version else ''})

    @retry_decorator
    def parse_size(self, response):
        self.log('parse_size')
        data = json.loads(response.body)
        fabric_url = 'http://www.sofasandstuff.com/static/fabric/GetFabricListNpp.ashx?' \
                     'modelId={model_id}&sizeId={size_id}'
        for size in data[0]['ProductSizeList']:
            yield Request(fabric_url.format(model_id=response.meta.get('model_id'),
                                            size_id=size['Id']),
                          meta={'model_id': response.meta.get('model_id'),
                                'size_id': size['Id'],
                                'version': response.meta.get('version')},
                          callback=self.parse_fabric)

    @retry_decorator
    def parse_fabric(self, response):
        self.log('parse_fabric')
        product_url = 'http://www.sofasandstuff.com/static/products/GetProductInfo.ashx?' \
                      'productId=&modelId={model_id}&size={size_id}&fabricId={fabric_id}&version={version}'
        fabrics = response.xpath('//a[contains(@href, "setColourFilter")]/@href').re('ColourFilter\((.*)\);')
        for fabric_id in fabrics:
            yield Request(product_url.format(model_id=response.meta['model_id'],
                                             size_id=response.meta['size_id'],
                                             fabric_id=fabric_id,
                                             version=response.meta['version']),
                          callback=self.parse_product3)

    @retry_decorator
    def parse_product(self, response):
        product_loader = ProductLoader(item=Product(), response=response)
        identifier = response.xpath('//input[@name="nodeId"]/@value').extract()
        if not identifier:
            return
        product_loader.add_value('identifier', identifier[0])
        name1 = response.xpath('//div[@class="title-wrapper"]/h1/text()').extract()[0]
        name2 = response.xpath('//div[@class="title-wrapper"]/p/text()').extract()[0]
        product_loader.add_value('name', name1 + ' ' + name2)
        product_loader.add_value('sku', identifier[0])
        image_url = response.xpath('//div[@class="image-wrapper"]/img/@src').extract()
        if image_url:
            product_loader.add_value('image_url', response.urljoin(image_url[0]))
        price = response.xpath('//div[@class="title-wrapper"]/p/span//text()').extract()[-1]
        price = extract_price(price)
        product_loader.add_value('price', price)
        product_loader.add_value('shipping_cost', 49)
        category = response.xpath('//div[@class="breadcrumbs"]//a/text()').extract()[1:]
        product_loader.add_value('category', category)
        product_loader.add_value('url', response.url)
        product = product_loader.load_item()
        yield product

    @retry_decorator
    def parse_product2(response):
        prod = response.meta['product']
        products = response.xpath('//div[@class="fabric-swatch" or contains(@class,"fabric-swatch ")]')
        for product in products:
            p = Product(prod)
            p['identifier'] = product.xpath('.//input[@name="nodeId"]/@value').extract()[0]
            p['name'] += ' ' + product.xpath('.//input[@name="description"]/@value').extract()[0]
            p['sku'] = p['identifier']
            image_url = product.xpath('./a/@href').extract()
            if image_url:
                p['image_url'] = response.urljoin(image_url[0])
            p['price'] = extract_price(product.xpath('.//input[@name="price"]/@value').extract()[0])
            yield p

    @retry_decorator
    def parse_product3(self, response):
        data = json.loads(response.body)
        product_loader = ProductLoader(item=Product(), response=response)
        product_loader.add_value('identifier', data['Id'])
        product_loader.add_value('sku', data['Id'])
        product_loader.add_value('name', '{} {}'.format(data['StyleName'], data['ProductDescription']))
        product_loader.add_value('price', re.findall(r'[\d\,.]+', data['Price'])[-1])
        product_loader.add_value('url', response.urljoin(data['Url']))
        product_loader.add_value('image_url', response.urljoin(data['ProductImage']))
        product_loader.add_value('shipping_cost', 49)
        yield product_loader.load_item()


    def _retry_request(self, request):
        retries = request.meta.get('retry_times', 0)
        max_retry = request.meta.get('max_retry', self.max_retry_times)

        if retries < max_retry:
            retries += 1
            retryreq = request.copy()
            retryreq.meta['retry_times'] = retries
            retryreq.meta['recache'] = True
            retryreq.dont_filter = True
            return retryreq
        else:
            self.blocked_urls.append(request.url)
            self.log('Gave up retrying %(request)s (failed %(retries)d times)' %
                     {'request': request, 'retries': retries})
