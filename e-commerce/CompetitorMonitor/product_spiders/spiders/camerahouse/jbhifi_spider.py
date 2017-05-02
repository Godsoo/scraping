import re

from scrapy import log
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc, add_or_replace_parameter

from product_spiders.items import (
    Product,
    ProductLoaderWithNameStrip as ProductLoader,
)


class JbhifiSpider(BaseSpider):
    name = 'jbhifi.com.au'
    allowed_domains = [
        'jbhifi.com.au',
        'jbhifihome.com.au']
    start_urls = ('http://www.jbhifi.com.au')

    def __init__(self, *args, **kwargs):
        super(JbhifiSpider, self).__init__()
        self.idents = set()

    def start_requests(self):
        # Parse main
        yield Request('https://www.jbhifi.com.au/General/Sitemap/', callback=self.parse_jbhifi)

        # Parse Home
        yield Request('https://www.jbhifihome.com.au/Pages/Sitemap/', callback=self.parse_jbhifihome)

    '''
    JBHIFI
    '''

    def parse_jbhifi(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        cats = hxs.select('//div[@class="cms-content"]//a/@href').extract()
        for url in cats:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_jbhifi_cat)

    def parse_jbhifi_cat(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        try:
            category = hxs.select('//*[@id="breadcrumb"]//li[@property="breadcrumb"]/text()').extract()[-1].strip()
        except:
            category = None

        products = hxs.select('//*[@id="productsContainer"]//div[contains(@class, "product-tile")]')
        for product in products:
            loader = ProductLoader(item=Product(), selector=product)
            loader.add_xpath('name', '@title')
            image_url = product.select('.//div[@class="image"]/img/@data-high').extract()
            image_url = urljoin_rfc(base_url, image_url[0]) if image_url else ''
            loader.add_value('image_url', image_url)
            loader.add_xpath('url', './/a[@class="link"]/@href', lambda l: urljoin_rfc(base_url, l[0]))
            loader.add_xpath('brand', './/div[@class="info"]//div[@class="brand"]//img/@alt')
            if category:
                loader.add_value('category', category)
            price = ''.join([s.strip() for s in product.select(
                './/div[@class="footer"]//span[contains(@class, "amount") '
                'and contains(@class, "regular")]//text()').extract()]).strip() or \
                    ''.join([s.strip() for s in product.select(
                        './/div[@class="footer"]//span[contains(@class, "amount") '
                        'and contains(@class, "onSale")]//text()').extract()]).strip() or \
                    ''.join([s.strip() for s in product.select(
                        './/div[@class="footer"]//span[contains(@class, "offer")]//text()').extract()]).strip()

            if not price:
                import ipdb; ipdb.set_trace()
            loader.add_value('price', price)
            sku = re.findall('\/(\d+)\/', loader.get_output_value('url'))
            if sku:
                loader.add_value('sku', sku[-1])
            loader.add_xpath('identifier', './/input[@class="hiddenProductId"]/@value')

            item = loader.load_item()
            if item['identifier'] not in self.idents:
                self.idents.add(item['identifier'])
                yield item

        for page in hxs.select('//div[@class="pagingContainer"]//a/@href').extract():
            yield Request(urljoin_rfc(base_url, page),
                          callback=self.parse_jbhifi_cat)

    '''
    JBHIFI HOME
    '''

    def parse_jbhifihome(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        cats = hxs.select('//ul[contains(@class, "sitemap")]//a/@href').extract()
        for url in cats:
            url = urljoin_rfc(base_url, url)
            url = add_or_replace_parameter(url, 'FL', 'True')
            yield FormRequest(url, callback=self.parse_jbhifihome_cat)

    def parse_jbhifihome_cat(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        def load_product(name, price, url, identifier, sku='', image_url='', category='', brand=''):
            if type(identifier) == type([]):
                identifier = identifier[0]
            if identifier not in self.idents:
                loader = ProductLoader(response=response, item=Product())

                loader.add_value('name', name)
                loader.add_value('url', url)
                loader.add_value('price', price)
                loader.add_value('identifier', identifier)
                loader.add_value('sku', sku)
                loader.add_value('image_url', image_url)
                loader.add_value('category', category)
                loader.add_value('brand', brand)

                self.idents.add(identifier)
                return loader.load_item()

            return None

        for label in hxs.select('//ul[contains(@class, "pagination")]'
                                    '/li[@class="label"]/a/text()').extract():
            try:
                page = int(label)
            except:
                pass
            else:
                url = response.url
                if 'DS=AS2EERTK' not in url:
                    url = add_or_replace_parameter(url, 'DS', 'AS2EERTK')
                yield FormRequest(url=url,
                                  formdata={u'page_state[page]': unicode(page),
                                            u'page_state[section]': u'',
                                            u'page_state[showing]': u'12',
                                            u'page_state[sort]': u'low-to-high',
                                            u'postData': u'{"section":"","filters":[],'
                                            u'"sort":"low-to-high","showing":"12",'
                                            u'"direction":"Next","page":"' + unicode(page) + u'"}'},
                                  callback=self.parse_jbhifihome_cat)

        products = hxs.select('//ul[contains(@class, "products")]//div[@class="inner"]')

        for product in products:
            try:
                name = product.select('.//*[@class="product-title"]/text()')\
                    .extract().pop().strip()
                url = urljoin_rfc(base_url,
                                  product.select('.//a[@class="product-link"]'
                                                 '/@href').extract().pop().strip())
                price = ''.join(product.select('.//*[contains(@class, "price")]'
                                               '/text()').extract())
                if not price:
                    import ipdb; ipdb.set_trace()
                brand = ''.join(product.select('.//span[@class="brand-name"]'
                                               '/text()').extract())
                category = hxs.select('//ul[@class="breadcrumbs"]/li/text()').extract()
                if category:
                    category = category[0].strip()
                img = product.select('.//div[@class="product-image"]/img/@src').extract()
                if img:
                    image_url = urljoin_rfc(base_url, img[0])
                else:
                    image_url = ''
                try:
                    sku = product.select('.//span[@class="model-number"]/text()').extract()
                    identifier = sku
                except e:
                    self.log('NO SKU | NO IDENTIFIER | %s' % (response.url))
                    raise e
            except:
                pass
            else:
                yield load_product(name=name,
                                   price=price,
                                   url=url,
                                   sku=sku,
                                   identifier=identifier,
                                   brand=brand,
                                   image_url=image_url,
                                   category=category)
