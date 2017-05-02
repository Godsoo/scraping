import exceptions
import demjson
import re
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

def normalize_space(s):
    """ Cleans up space/newline characters """
    import re
    return re.sub('\\s+', ' ', s.replace(u'\xa0', ' ').strip())

def get_properties(data):
    props = {}
    for item in data['properties'].values():
        if 'elementId' in item:
            elid = item.pop('elementId')
            props[elid] = item.values()[0]
    return props

class AllWeathersSpider(BaseSpider):
    name = 'allweathers.co.uk'
    allowed_domains = ['allweathers.co.uk']
    start_urls = ['http://www.allweathers.co.uk']
    errors = []

    def _start_requests(self):
        yield Request('http://www.allweathers.co.uk/outwell-cedar-1800-sleeping-bag-14004-p.asp', callback=self.parse_product)

    def retry(self, response, error="", retries=3):
        meta = response.meta.copy()
        retry = int(meta.get('retry', 0))
        if 'redirect_urls' in meta and meta['redirect_urls']:
            url = meta['redirect_urls']
        else:
            url = response.request.url
        if retry < retries:
            retry = retry + 1
            meta['retry'] = retry
            meta['recache'] = True
            yield Request(url, dont_filter=True, meta=meta, callback=response.request.callback)
        else:
            self.errors.append(error)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        #relative_urls = hxs.select('//*[@id="siteBrandsDrowpDownSelect"]/'
        #                           'option[not(@value="")]/@value').extract()
        relative_urls = hxs.select('//div[@id="siteNav"]/ul/li/a/@href').extract()
        for relative_url in relative_urls:
                url = urljoin_rfc('http://www.allweathers.co.uk', relative_url)
                yield Request(url, callback=self.parse_categories, dont_filter=True)

    def parse_categories(self, response):
        try:
            hxs = HtmlXPathSelector(response)
            sub_categories = hxs.select('//div[@class="category-row"]/div/div/'
                                        'div[@class="category-item-name"]/'
                                        'a/@href').extract()
            if not sub_categories:
                products = hxs.select('//div[@class="wood-product "]')
                for product in products:
                    loader = ProductLoader(item=Product(), selector=product)
                    loader.add_xpath('name', 'div/div/div/'
                                             'div[@class="wood-product-name"]/'
                                             'a/text()')
                    relative_url = product.select('div/div/div/'
                                                  'div[@class="wood-product-name"]/'
                                                  'a/@href').extract()[0]
                    url = urljoin_rfc('http://www.allweathers.co.uk', relative_url)
                    yield Request(url, callback=self.parse_product)
            else:
                relative_urls = hxs.select('//div[@class="category-row"]/div/'
                                            'div/div[@class="category-item-name"]/'
                                            'a/@href').extract()
                for relative_url in relative_urls:
                    url = urljoin_rfc('http://www.allweathers.co.uk', relative_url)
                    yield Request(url, callback=self.parse_categories, dont_filter=True)
        except exceptions.AttributeError:
             if 'ret' in response.meta:
                 if response.meta['ret'] <= 5:
                     yield Request(response.url, callback=self.parse_categories,
                                   dont_filter=True, meta={'ret': response.meta['ret'] + 1})
             else:
                 yield Request(response.url, callback=self.parse_categories,
                               dont_filter=True, meta={'ret': 1})

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)

        def get_json(html):
            data = []
            for line in html.split('\n'):
                if line.startswith('ekmProductVariantData[0]'):
                    data.append("{ 'items' : [")
                elif data:
                    if "'function':function(){" not in line:
                        data.append(line)
                    if line.strip().endswith('}}]}'):
                        data.append('}}]}')
                        data = '\n'.join(data)
                        return demjson.decode(re.sub(r'"stockMessage":.*"addCart"', '"addCart"', data), return_errors=True)[0]
                    if "'function':function(){" in line:
                        data.append('}},{')

            return {}

        data = get_json(response.body)
        found = False
        for item in data.get('items', []):
            found = True
            props = get_properties(item)
            loader = ProductLoader(item=Product(), selector=hxs)
            loader.add_value('identifier', props['_EKM_VARIANTID'])
            loader.add_value('sku', props['_EKM_VARIANTID'])
            loader.add_value('url', response.url)
            loader.add_value('name', normalize_space(' '.join(
                        hxs.select('//h1//text()').extract()
                        + [x['value'] for x in item['selector']]
                        )))
            loader.add_value('price', props['_EKM_PRODUCTPRICE'])
            loader.add_value('category', hxs.select('//*[@itemprop="title"]/text()').extract()[1])
            loader.add_value('image_url', urljoin_rfc(get_base_url(response), props['_EKM_PRODUCTIMAGE_LINK_1']))

            loader.add_value('brand', loader.get_output_value('name').split()[0])
            loader.add_xpath('shipping_cost', '//span[@id="ModelsDisplayStyle1_LblPostageCostValue"]/text()')

            loader.add_value('stock', props['_EKM_PRODUCTSTOCK'])
            if loader.get_output_value('price') < 49.99:
                loader.add_value('shipping_cost', '4.95')
            else:
                loader.add_value('shipping_cost', '0')
            yield loader.load_item()

        if not found:
            loader = ProductLoader(item=Product(), selector=hxs)

            loader.add_xpath('identifier', '//form[@id="product_form"]/@action', re=r'productid=(\d+)')
            loader.add_xpath('sku', '//form[@id="product_form"]/@action', re=r'productid=(\d+)')
            loader.add_value('url', response.url)
            loader.add_value('name', normalize_space(' '.join(
                        hxs.select('//h1//text()').extract()
                        + hxs.select('//option[@class="ekm-productoptions-dropdown-option-withoutborder"]/text()').extract()
                        )))
            loader.add_xpath('price', '//*[@itemprop="price"]/text()')
            try:
                loader.add_value('category', hxs.select('//*[@itemprop="name"]/text()').extract()[-1])
            except:
                self.retry(response, "Unknown error on " + response.url)
            img = hxs.select('//img[@class="ekm-product-image-bradge"]/@src').extract()
            if img:
                loader.add_value('image_url', urljoin_rfc(get_base_url(response), img[0]))

            loader.add_value('brand', loader.get_output_value('name').split()[0])
            loader.add_xpath('shipping_cost', '//span[@id="ModelsDisplayStyle1_LblPostageCostValue"]/text()')

            if hxs.select('//option[contains(text(), "IN STOCK")]'):
                loader.add_value('stock', '1')
            elif loader.get_output_value('price'):
                loader.add_value('stock', '1')

            if loader.get_output_value('price') < 49.99:
                loader.add_value('shipping_cost', '4.95')
            else:
                loader.add_value('shipping_cost', '0')
            yield loader.load_item()



