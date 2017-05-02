# -*- coding: utf-8 -*-

import re
import os
import json

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest, HtmlResponse
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc
from scrapy import log
from scrapy.http import FormRequest
from scrapy.xlib.pydispatch import dispatcher
from scrapy import signals

from productloader import load_product
import csv, codecs, cStringIO

from utils import extract_price

Current_dir = os.path.abspath(os.path.dirname(__file__))

class dyersonline_spider(BaseSpider):
    name = 'dyersonline.com'
    allowed_domains = ['dyersonline.com', 'www.dyersonline.com']
    start_urls = ('http://www.dyersonline.com',)

    download_delay = 0.5

    current_cookie = 0

    @classmethod
    def spider_opened(spider):
        if spider.name == 'dyersonline.com':
            log.msg("opened spider %s" % spider.name)

    @classmethod
    def spider_closed(spider):
        if spider.name == 'dyersonline.com':
            if os.path.exists(os.path.join(Current_dir, 'skus_.csv')):
                try:
                    os.remove(os.path.join(Current_dir, 'skus.csv'))
                except:
                    print log.msg("No sku.csv file!")
                os.rename(os.path.join(Current_dir, 'skus_.csv'), os.path.join(Current_dir, 'skus.csv'))

    def __init__(self, *args, **kwargs):
        super(dyersonline_spider, self).__init__(*args, **kwargs)
        dispatcher.connect(self.spider_opened, signals.spider_opened)
        dispatcher.connect(self.spider_closed, signals.spider_closed)

        # parse the csv file to get the product ids
        self.csv_writer = UnicodeWriter(open(os.path.join(Current_dir, 'skus_.csv'), 'wb'), dialect='excel')

    def parse(self, response):
        if not isinstance(response, HtmlResponse):
            return
        base_url = get_base_url(response)

        # categories
        hxs = HtmlXPathSelector(response)
        category_urls = hxs.select('//div[@class="nav-container"]/ul[@id="nav"]/li/ul/li/a/@href').extract()
        for url in category_urls:
            yield Request(url)

        # pages
        page_urls = hxs.select('//div[@class="pages"]/ol/li/a/@href').extract()
        for page in page_urls:
          yield Request(page)

        acategory_urls = hxs.select('//div[@class="category-image"]/a/@href').extract()
        for aurl in acategory_urls:
          yield Request(aurl)


        # products
        products = hxs.select('//div[@class="category-products"]/ul/li/a/@href').extract()
        for p in products:
            self.current_cookie += 1
            yield Request(p, callback=self.parse_product, meta={'cookiejar': self.current_cookie})

    def parse_product(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)
        res = {}

        name = hxs.select("//div[@class='product-name']/h1/text()").extract()
        url = response.url
        price = "".join(hxs.select("//div[@class='col-right']/div/div[@class='price-block']/span/span[@class='price']/text()").re(r'([0-9\,\. ]+)')).strip()
        if not price:
            price = "".join(hxs.select("//div[@class='col-right']/div/p[@class='special-price']/span[@class='price']/text()").re(r'([0-9\,\. ]+)')).strip()
        if not price:
            price = hxs.select('//*[@itemprop="price"]//text()').re(r'([\d.,]+)')
        if not price:
            try:
                price_popup_hxs = HtmlXPathSelector(text=re.search(r'realPrice = (.*)', response.body).groups()[0].replace('\\n', '').replace('\\t', '').replace('\\', '')[1:-2].strip())
                price = price_popup_hxs.select('//span[@class="price"]/text()').extract()
            except:
                pass
        try:
            sku = hxs.select("//dd[@class='identifier']/text()")[0].extract()
        except:
            sku = ''
        res['url'] = urljoin_rfc(base_url, url)
        res['description'] = sku + ' ' + name[0].strip()
        res['image_url'] = hxs.select('//a[@id="image-link"]/img/@src').extract()
        category = hxs.select('//div[@class="breadcrumbs"]//a/span/text()')
        if category:
            res['category'] = category[-1].extract()
        res['brand'] = hxs.select('//dd[@class="brand"]/text()').extract()
        # res['sku'] = sku
        res['identifier'] = sku
        sku2 = hxs.select("//div[@class='1']/text()").extract()
        if not sku2:
            sku2_ = 0
        else:
            sku2_ = sku2[0]
        sku3 = hxs.select("//div[@class='2']/text()").extract()
        if not sku3:
            sku3_ = 0
        else:
            sku3_ = sku3[0]
        model = hxs.select("//dd[@class='model']/text()").extract()
        if not model:
            self.log('NO MODEL/SKU => %s' % (res['url'],))
            model_ = ''
        else:
            model_ = model[0]
        res['sku'] = model_  # Using model field as SKU
        self.csv_writer.writerow([res['sku'], sku2_, sku3_, model_, name[0].strip()])
        options_select = hxs.select('//div[@id="product-options-wrapper"]//select')
        options_radio = hxs.select('//div[@id="product-options-wrapper"]//ul[@class="options-list"]')
        if options_select:
            form_action = hxs.select('//form[@id="product_addtocart_form"]/@action').extract()[0]
            params = dict(
                zip(hxs.select('//form[@id="product_addtocart_form"]//input/@name').extract(),
                    hxs.select('//form[@id="product_addtocart_form"]//input/@value').extract())
            )
            product_data = json.loads(re.search(r'var spConfig = new Product.Config\((.*)\)', response.body).groups()[0])
            for product in product_data['attributes'].values():
                attr = product['id']
                super_attr_param = u'super_attribute[%s]' % attr
                option_params = []
                for option in product['options']:
                    opt_params = params.copy()
                    opt_params[super_attr_param] = option['id']
                    option_params.append(opt_params)
                opt_params = option_params.pop()
                yield FormRequest(form_action, formdata=opt_params, callback=self.parse_cart,
                    meta={'item': res, 'params': option_params, 'form_action': form_action,
                          'cookiejar': response.meta['cookiejar']}, dont_filter=True)
        elif options_radio:
            form_action = hxs.select('//form[@id="product_addtocart_form"]/@action').extract()[0]
            params = dict(
                zip(hxs.select('//form[@id="product_addtocart_form"]//input[not(@type="radio") and not(@disabled)]/@name').extract(),
                    hxs.select('//form[@id="product_addtocart_form"]//input[not(@type="radio") and not(@disabled)]/@value').extract())
            )
            options = zip(hxs.select('//form[@id="product_addtocart_form"]//input[@type="radio" and not(@disabled)]/@name').extract()[1:],
                          hxs.select('//form[@id="product_addtocart_form"]//input[@type="radio" and not(@disabled)]/@value').extract()[1:])
            option_params = []
            for option in options:
                opt_params = params.copy()
                opt_params.update({option[0]: option[1]})
                option_params.append(opt_params)
            opt_params = option_params.pop()
            yield FormRequest(form_action, formdata=opt_params, callback=self.parse_cart,
                meta={'item': res, 'params': option_params, 'form_action': form_action,
                      'cookiejar': response.meta['cookiejar']}, dont_filter=True)
        elif price:
            res['price'] = price
            yield load_product(res, response)
        else:
            form_action = hxs.select('//form[@id="product_addtocart_form"]/@action').extract()[0]
            params = dict(
                zip(hxs.select('//form[@id="product_addtocart_form"]//input/@name').extract(),
                    hxs.select('//form[@id="product_addtocart_form"]//input/@value').extract())
            )
            yield FormRequest(form_action, formdata=params, callback=self.parse_cart,
                meta={'item': res, 'cookiejar': response.meta['cookiejar']}, dont_filter=True)

    def parse_cart(self, response):
        hxs = HtmlXPathSelector(response)

        '''
        To test...
        
        with open('cart_%s.html' % response.meta['cookiejar'], 'w') as f:
            f.write(response.body)
        '''

        price = hxs.select('//table[@id="shopping-cart-table"]//span[@class="cart-price"]/span[@class="price"]/text()').extract()[-1]
        identifier = hxs.select('//table[@id="shopping-cart-table"]//h2[@class="product-name"]/following-sibling::span/text()').re(r'\d+')[-1]
        try:
            option = hxs.select('//table[@id="shopping-cart-table"]//dl[@class="item-options"]/dd/text()').extract()[-1].strip()
        except:
            option = ''
        item = response.meta['item'].copy()
        item['identifier'] = identifier
        if not item['sku'] in item['description']:
            item['description'] = item['sku'] + ' ' + item['description']
        item['description'] = item['description'] + ' ' + option
        item['price'] = price
        yield load_product(item, response)

        option_params = response.meta.get('params', [])
        if option_params:
            opt_params = option_params.pop()
            form_action = response.meta['form_action']
            yield FormRequest(form_action, formdata=opt_params, callback=self.parse_cart,
                meta={'item': response.meta['item'], 'params': option_params,
                      'form_action': form_action, 'cookiejar': response.meta['cookiejar']}, dont_filter=True)

class UTF8Recoder:
    """
    Iterator that reads an encoded stream and reencodes the input to UTF-8
    """
    def __init__(self, f, encoding):
        self.reader = codecs.getreader(encoding)(f)

    def __iter__(self):
        return self

    def next(self):
        return self.reader.next().encode("utf-8")

class UnicodeReader:
    """
    A CSV reader which will iterate over lines in the CSV file "f",
    which is encoded in the given encoding.
    """

    def __init__(self, f, dialect=csv.excel, encoding="utf-8", **kwds):
        f = UTF8Recoder(f, encoding)
        self.reader = csv.reader(f, dialect=dialect, **kwds)

    def next(self):
        row = self.reader.next()
        return [unicode(s, "utf-8") for s in row]

    def __iter__(self):
        return self

class UnicodeWriter:
    """
    A CSV writer which will write rows to CSV file "f",
    which is encoded in the given encoding.
    """

    def __init__(self, f, dialect=csv.excel, encoding="utf-8", **kwds):
        # Redirect output to a queue
        self.queue = cStringIO.StringIO()
        self.writer = csv.writer(self.queue, dialect=dialect, **kwds)
        self.stream = f
        self.encoder = codecs.getincrementalencoder(encoding)()

    def writerow(self, row):
        new_row = []
        for s in row:
            try:
                s = s.encode('utf-8')
            except:
                pass
            new_row.append(s)
        self.writer.writerow(new_row)
        # Fetch UTF-8 output from the queue ...
        data = self.queue.getvalue()
        data = data.decode("utf-8")
        # ... and reencode it into the target encoding
        data = self.encoder.encode(data)
        # write to the target stream
        self.stream.write(data)
        # empty queue
        self.queue.truncate(0)

    def writerows(self, rows):
        for row in rows:
            self.writerow(row)
