
import demjson
import re

from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest
from scrapy.utils.url import urljoin_rfc, url_query_parameter
from scrapy.utils.response import get_base_url

from product_spiders.base_spiders.primary_spider import PrimarySpider
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.utils import extract_price

from scrapy import log

def re_strip(s):
    return re.sub(r'\s+', ' ', s.strip())


from scrapy.item import Item, Field
class Meta(Item):
    photoluminescence = Field()
    size = Field()
    material = Field()
    thickness = Field()

class SetonCoUkSpider(PrimarySpider):
    name = 'seton.co.uk'
    allowed_domains = ['seton.co.uk']
    start_urls = ('http://www.seton.co.uk/',)
    _idents = []

    # PrimarySpider config
    csv_file = 'seton_crawl.csv'
    json_file = 'seton_crawl.json-lines'
    errors = []

    def _start_requests(self):
        yield Request('http://www.seton.co.uk/qg100-num.html', callback=self.parse_product)

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
        base_url = get_base_url(response)
        # check for new categories
        links = set(response.xpath('//div[@id="menu"]//a/@href').extract())
        products = set(response.css('.product-name a::attr(href)').extract())
        categories = links - products
        for url in categories:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product_list)
    
    def parse_product_list(self, response):
        if response.meta.get('ajax', False):
            try:
                data = demjson.decode(response.body)
            except:
                log.msg('Wrong json format')
                log.msg(str(response.body))
                return
            hxs = HtmlXPathSelector(text=data['content'])
        else:
            hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        # pagination
        pages = response.css('.pages a::attr(href)').extract()
        for page in pages:
            yield Request(page, self.parse_product_list)
            
        next_page = hxs.select('//a[contains(@class, "i-next") and @title="Next"]/@href').extract()
        if next_page:
            ajax_url = 'http://www.seton.co.uk/endecasearch/result/refresh/?mode=grid'

            form_data = {}
            for line in hxs.response.body.split('\n'):
                if '{"N":' in line:
                    data = demjson.decode(line.strip()[:-1].replace('data-navigation=', ''))
                    if 'category_id' in data:
                        form_data = data
            form_data['Nrpp'] = '40'
            form_data['isAjax'] = 'true'
            form_data['mode'] = 'grid'

            headers = {'X-Requested-With': 'XMLHttpRequest',
                       'Accept': 'text/javascript, text/html, application/xml, text/xml, */*'}

            url = next_page[0]

            page_no = url_query_parameter(url, 'p')
            if form_data:
                form_data['No'] = str(page_no)
                form_data = dict([(unicode(k), unicode(v)) for k, v in form_data.items()])
                self.log('>>> Form Request Data: %r' % form_data)
                yield FormRequest(ajax_url,
                                  formdata=form_data,
                                  headers=headers,
                                  meta={'ajax': True},
                                  callback=self.parse_product_list)

        # parse products list
        products_urls = response.css('.products-grid a::attr(href)').extract()
        for url in products_urls:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        redirected_urls = response.meta.get('redirect_urls', None)
        if redirected_urls:
            log.msg('Skips product, redirected url: ' + str(redirected_urls[0]))
            return

        product_id = response.xpath('//*[@id="product-id"]/@value').extract()
        if product_id:
            product_id = product_id[0]
        else:
            log.msg('Product without identifier: ' + response.url)
            return
        category = response.xpath('//div[@class="breadcrumbs"]/ol/li[2]/a/span/text()').extract()
        category = category[0] if category else ''

        brand = ' '.join(response.xpath('//script/text()').re('product_brand":\["(.+?)"\]'))
        if len(brand) > 100:
            brand = ' '.join(set(re.findall(r'\w+', brand)))

        product_name = response.xpath('//h1/span[@itemprop="name"]/text()').extract()
        if product_name:
            product_name = product_name[0]
        else:
            log.msg('Product without name: ' + response.url)
            return

        brand_in_name = False
        for w in re.findall('([a-zA-Z]+)', product_name):
            if w.upper() in brand.upper():
                brand_in_name = True

        if brand.upper() not in product_name.upper() and not brand_in_name:
            product_name = brand + ' ' + product_name

        def data(th):
            g = re.search('"%s","attribute_value":"([^"]*)"' % th, response.body)
            if g:
                return g.group(1)
            g = response.xpath('//th[text()="%s"]/following-sibling::td[1]/text()' %th).extract_first()
            if g:
                return g.strip()
            return ''

        meta = Meta()
        meta['photoluminescence'] = data("Photoluminescence")
        meta['size'] = data("Size \(H x W\)")
        meta['material'] = data("Material")
        meta['thickness'] = data("Thickness")

        image_url = response.xpath('//*[@id="image"]/@src').extract()[0]
        script = response.xpath('//*[@id="product-options-wrapper"]/script[1]/text()').extract()
        script = script[0].strip() if script else None
        url = response.url.split('/')[-1]
        url = 'http://www.seton.co.uk/' + url
        if script:
            # multiple options product
            ajax_url = 'http://www.seton.co.uk/oi/ajax/list/?id=%s' % product_id
            product_loader = ProductLoader(item=Product(), selector=hxs)
            product_loader.add_value('category', category)
            product_loader.add_value('name', product_name)
            product_loader.add_value('brand', brand)
            product_loader.add_value('url', url)
            product_loader.add_value('image_url', urljoin_rfc(base_url, image_url))
            product = product_loader.load_item()
            product['metadata'] = meta
            yield Request(ajax_url,
                          self.parse_options,
                          meta={'product': product})
        else:
            # no options
            product_loader = ProductLoader(item=Product(), selector=hxs)
            product_loader.add_value('category', category)
            product_loader.add_value('image_url', urljoin_rfc(base_url, image_url))
            product_loader.add_value('name', product_name)
            product_loader.add_value('brand', brand)
            product_loader.add_value('url', url)
            identifier = product_id
            product_loader.add_value('identifier', identifier)
            sku = re.findall('"sku":"([^"]+)"', response.body)
            if not sku:
                self.retry(response, "SKU not found on " + response.url)
                return
            product_loader.add_value('sku', sku.pop())
            price = hxs.select('//div[@id="add-to-box"]//span[@class="price"]/text()').extract()[0].strip()
            product_loader.add_value('price', extract_price(price))
            product = product_loader.load_item()
            product['metadata'] = meta
            if product['identifier'] not in self._idents:
                self._idents.append(product['identifier'])
                yield product

    def parse_options(self, response):
        hxs = HtmlXPathSelector(response)

        options = hxs.select('//table[@id="super-product-table"]/tbody/tr')
        headers = hxs.select('//thead/tr/th/text()').extract()

        for option in options:
            if 'No options of this product are available'.lower() in option.select('td/text()').extract()[0].lower():
                continue
            attributes = {}
            product = Product(response.meta['product'])
            for i, title in enumerate(headers):
                attributes[title.upper()]  = ''.join(option.select('./td[position()='+str(i+1)+']/text()').extract()).strip()

            product['name'] += ', ' + ', '.join((re_strip(s) for s in option.select('./td[position()>1 and position()<last()-1]/text()').extract()))
            product['sku'] = option.select('./td/input[contains(@name, "qty-item-")]/@name').extract().pop().replace("qty-item-", "")
            product['price'] = extract_price(
                option.select('.//span[@class="price-excluding-tax"]/span/text()')[0].extract().strip())
            identifier = option.select('.//input[@id="product-item"]/@value').extract()
            if not identifier:
                identifier = option.select('.//div/@data-product-id').extract()

            product['identifier'] = identifier[0].strip()

            if attributes.get('MATERIAL', None):
                product['metadata']['material'] = attributes.get('MATERIAL')
            if attributes.get('SIZE', None):
                product['metadata']['size'] = attributes.get('SIZE')
            if attributes.get('THICKNESS', None):
                product['metadata']['thickness'] = attributes.get('THICKNESS')
            if attributes.get('PHOTOLUMINESCENCE', None):
                product['metadata']['photoluminescence'] = attributes.get('PHOTOLUMINESCENCE')




            if product['identifier'] not in self._idents:
                self._idents.append(product['identifier'])
                yield product
