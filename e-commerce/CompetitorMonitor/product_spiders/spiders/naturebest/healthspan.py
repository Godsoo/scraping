
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from product_spiders.items import (
    Product,
    ProductLoaderWithNameStrip as ProductLoader
)


class HealthSpanSpider(BaseSpider):
    name = 'healthspan.co.uk'
    allowed_domains = ['healthspan.co.uk']
    start_urls = ('http://www.healthspan.co.uk/products/',)

    current_session = 0

    '''
    def start_requests(self):
        yield Request('http://www.healthspan.co.uk/products/cod-liver-oil-and-evening-primrose-oil', callback=self.parse_options)
    '''

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        products = hxs.select('//div[@class="item-details"]/h3/a/@href').extract()
        for url in products:
            self.current_session += 1
            yield Request(urljoin_rfc(base_url, url),
                          meta={'cookiejar': self.current_session},
                          callback=self.parse_options)


        waypoints = hxs.select('//div[@class="a-z-waypoints"][1]/ul/li/a/@href').extract()
        for url in waypoints:
            yield Request(urljoin_rfc(base_url, url))


    def parse_options(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        current_meta = response.meta.copy()

        options_select = hxs.select('//div[@class="product-selection"]//div[@class="select-dropdown"]/select')
        if options_select:

            option_selected_name = response.meta.get('option_name')
            option_selected_id = response.meta.get('option_id')
            if option_selected_name and option_selected_id:
                for item in self.parse_product(response):
                    yield item

            options_ids = hxs.select('//div[@class="product-selection"]//div/select/@name').extract()
            try:
                options_value_name = response.meta['options']
            except:
                options_value_name = zip(options_select.select('option/@value').extract(),
                                         options_select.select('option/text()').extract())

            if options_value_name:
                opt_val, opt_name = options_value_name.pop()

                opt_form_data = dict([(opt_id, opt_val) for opt_id in options_ids])
                for k in opt_form_data.keys():
                    opt_form_data[k.replace('$ddlVariants', '$txtQuantity')] = '1'

                current_meta.update(
                    {'option_name': opt_name,
                     'option_id': opt_val,
                     'options': options_value_name})

                yield FormRequest.from_response(response,
                    formdata=opt_form_data,
                    meta=current_meta,
                    callback=self.parse_options, dont_filter=True)
        else:
            for item in self.parse_product(response):
                yield item

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        name = hxs.select('//*[@itemprop="name"]/text()').extract()

        if name:
            option_name = response.meta.get('option_name', '')
            option_id = response.meta.get('option_id', '')

            if option_id == 'My dog weighs':
                return

            if option_name:
                name += ' - ' + option_name

            sku = option_id
            if not sku:
                sku = hxs.select('//input[@name="middle_0$product_0$skuCode"]/@value').extract()

            if sku:
                loader = ProductLoader(item=Product(), response=response)
                loader.add_value('name', name)
                loader.add_xpath('price', '//span[@class="product-price"]/*/text()')
                loader.add_value('identifier', sku)
                loader.add_value('sku', sku)
                loader.add_value('url', response.url)

                yield loader.load_item()
