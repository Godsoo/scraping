# from scrapy.spider import BaseSpider
# from scrapy.contrib.spiders import SitemapSpider
from product_spiders.base_spiders.bigsitemethodspider import BigSiteMethodSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from urlparse import urljoin as urljoin_rfc
from scrapy.utils.response import get_base_url
from product_spiders.utils import extract_price
import itertools

from scrapy import log

import re


class SlingsbySpider(BigSiteMethodSpider):
    name = 'arco-a-slingsby.com'
    allowed_domains = ['slingsby.com']

    start_urls = ('http://www.slingsby.com/',)

    '''
    sitemap_urls = ['http://www.slingsby.com/ProductSitemap1.xml']
    sitemap_rules = [
        ('/', 'parse_product'),
    ]
    '''

    website_id = 361

    def full_run_required(self):
        # Always full run
        return True

    def parse_full(self, response):
        '''
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        categories_urls = hxs.select('//div[@class="HEADNAV"]/div/ul/li/span/a/@href').extract()
        for url in categories_urls:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product_list)
        '''

        yield Request('http://www.slingsby.com/ProductSitemap1.xml', callback=self.parse_sitemap)

    def parse_sitemap(self, response):
        for url in re.findall(r'<loc>(.*)</loc>', response.body):
            yield Request(url, callback=self.parse_product)

    def parse_product_list(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        products_urls = hxs.select('//ol[@class="LIST"]/li/h2/a/@href').extract()
        for url in products_urls:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product)

        next = hxs.select('//span[@class="NEXTPG"]/a/@href').extract()
        if next:
            yield Request(urljoin_rfc(base_url, next[0]), callback=self.parse_product_list)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)


        formdata = {}
        inputs = hxs.select('//input')
        for input_value in inputs:
            name = input_value.select('@name').extract()[0]
            value = input_value.select('@value').extract()
            value = value[0] if value else ''
            formdata[name] = value

        options_lists = hxs.select('//select')
        is_option = response.meta.get('is_option', False)
        options = []
        if not is_option:
            for option_list in options_lists[0:1]:
                element_options = []
                for option in option_list.select('option'):
                    value = ''.join(option.select('@value').extract())
                    if value:
                        element_options.append((option_list.select('@name').extract()[0], value))
                options.append(element_options)

            total_options = options = list(itertools.product(*options))
            for total_option in total_options:
                option_formdata = dict(formdata)
                for option in total_option:
                    select_name = option[0]
                    option_formdata[select_name] = option[1]
                option_formdata['ctl00$cph1$pD$ctrl0$tbQty'] = '1'

                yield FormRequest(url=response.url,
                                  method='POST',
                                  dont_filter=True,
                                  formdata=option_formdata,
                                  callback=self.parse_product,
                                  meta={'is_option': True,
                                        'cookies': [{}],
                                        'url': response.url,
                                        'formdata':option_formdata})

        if not options or is_option:
            product_loader = ProductLoader(item=Product(), selector=hxs)

            name = hxs.select('//div[@id="CENTERCOLUMN"]/h1/text()').extract()
            if not name:
                return

            name = name[0]

            ext_name = hxs.select('//option[@selected]/text()').extract()
            ext_name = ' - '.join(ext_name)

            category = hxs.select('//div[@class="BREAD"]/ol/li/a/text()').extract()[-1]
            image_url = hxs.select('//a[@class="MagicZoomPlus"]/@href').extract()
            if image_url:
                image_url = urljoin_rfc(base_url, image_url[0])

            sku = hxs.select('//div[@class="PCODE"]/span/span/text()').extract()
            sku = sku[-1] if sku else ''

            product_loader = ProductLoader(item=Product(), selector=hxs)
            product_loader.add_value('category', category)
            if ext_name:
                name = name + ' - ' + ext_name
            product_loader.add_value('name', name)
            product_loader.add_value('url', response.url)
            product_loader.add_value('identifier', sku)

            product_loader.add_value('sku', sku)
            price = hxs.select('//span[@class="RTB-PRICE PRICE"]/text()').extract()
            if price:
                price = extract_price(price[0])
                product_loader.add_value('price', price)
                if price <= 0:
                    product_loader.add_value('stock', 0)
            product_loader.add_value('image_url', image_url)
            if sku:
                yield product_loader.load_item()
