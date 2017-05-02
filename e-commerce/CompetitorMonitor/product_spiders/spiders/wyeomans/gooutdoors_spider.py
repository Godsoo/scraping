import re

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse, FormRequest
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

from scrapy import log

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader


class GoOutdoorsSpider(BaseSpider):
    name = 'gooutdoors.co.uk'
    allowed_domains = ['gooutdoors.co.uk']
    start_urls = ['http://www.gooutdoors.co.uk']

    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        categories = hxs.select('//div[@id="hdrNav"]/ul/li/a/@href').extract()
        for url in categories:
            yield Request(url)

        relative_urls = hxs.select('//*[@id="catNav"]/ul//a/@href').extract()
        for relative_url in relative_urls:
            url = urljoin_rfc('http://www.gooutdoors.co.uk/',
                              relative_url,
                              response.encoding)

            yield Request(url)

        products = hxs.select('//div[@class="in"]')
        for product in products:
            relative_url = product.select('h3/a/@href').extract()[0]
            yield Request(urljoin_rfc('http://www.gooutdoors.co.uk/',
                                                relative_url,
                                                response.encoding), callback=self.parse_product)
        next_page = hxs.select('//*[@id="pSrchFtr"]/div/span/a/@href').extract()
        if next_page:
            url = urljoin_rfc('http://www.gooutdoors.co.uk/',
                              next_page[0],
                              response.encoding)
            yield Request(url)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)

        category = hxs.select('//div[@id="bCrumb"]/span/a/text()').extract()
        category = category[-1] if category else response.meta.get('category', '')

        colours = hxs.select('//select[@id="cphMain_ddlColour"]/option[@value!="0"]/@value').extract()
        no_option_selected = hxs.select('//select[@id="cphMain_ddlColour"]/option[@value="0" and @selected]/@value')
        if colours and no_option_selected:
            for colour in colours:
                formdata = {}
                inputs = hxs.select('//form[@id="frmMain"]//input')
                for input in inputs:
                    name = ''.join(input.select('@name').extract())
                    value = ''.join(input.select('@value').extract())
                    formdata[name] = value
                formdata['ctl00$cphMain$ddlColour'] = colour
                form_url = hxs.select('//form[@id="frmMain"]/@action').extract()[0]
                yield FormRequest(form_url,
                                  dont_filter=True,
                                  method='POST',
                                  formdata=formdata,
                                  callback=self.parse_product,
                                  meta={'category': category, 'colour': colour})
            return


        sizes = hxs.select('//select[@id="cphMain_ddlSize"]/option[@value!="0"]/@value').extract()
        no_option_selected = hxs.select('//select[@id="cphMain_ddlSize"]/option[@value="0" and @selected]')
        if sizes and no_option_selected:
            for size in sizes:
                formdata = {}
                inputs = hxs.select('//form[@id="frmMain"]//input')
                for input in inputs:
                    name = ''.join(input.select('@name').extract())
                    value = ''.join(input.select('@value').extract())
                    formdata[name] = value

                formdata['ctl00$cphMain$ddlSize'] = size
                colour = response.meta.get('colour', None)
                if colour:
                    formdata['ctl00$cphMain$ddlColour'] = colour
                form_url = hxs.select('//form[@id="frmMain"]/@action').extract()[0]
                yield FormRequest(form_url,
                                  dont_filter=True,
                                  method='POST',
                                  formdata=formdata,
                                  callback=self.parse_product,
                                  meta={'category': category, 'formdata':formdata})
            return


        loader = ProductLoader(item=Product(), selector=hxs)

        identifier = hxs.select('//div[@class="code"]/text()').extract()[0]
        loader.add_xpath('sku', '//div[@class="code"]/text()')
        loader.add_value('url', response.url)
        product_name = hxs.select('//div[@class="title"]//h1/text()').extract()[0]

        colour = hxs.select('//span[@id="cphMain_lblSelectedColour"]/b/text()').extract()
        if colour:
            product_name = product_name + ' - ' + colour[0].strip()


        loader.add_value('category', category)
        img = hxs.select('//img[@id="cphMain_imgThumb"]/@src').extract()
        if img:
            loader.add_value('image_url', urljoin_rfc(get_base_url(response), img[0]))

        loader.add_xpath('brand', '//span[@class="brand"]/text()')
        loader.add_value('stock', '1')
        if loader.get_output_value('price') < 50.00:
            loader.add_value('shipping_cost', '4.95')
        else:
            loader.add_value('shipping_cost', '0')

        price = hxs.select('//span[@class="price"]/text()').extract()

        if colours or sizes:
            colour = hxs.select('//select[@id="cphMain_ddlColour"]/option[@selected and @value!="0"]')

            option_price = None
            if colour:
                colour_id = colour.select('@value').extract()[0]
                colour_desc = colour.select('text()').extract()[0]
                identifier = identifier + '-' + colour_id
                product_name = product_name + ' - ' + colour_desc.split(u' - \xa3')[0].strip()
                option_price = re.search(r"\xa3(\d+.\d+)", colour_desc)

            size = hxs.select('//select[@id="cphMain_ddlSize"]/option[@selected and @value!="0"]')
            if size:
                size_id = size.select('@value').extract()[0]
                size_desc = size.select('text()').extract()[0].strip()
                identifier = identifier + '-' + size_id
                colour = hxs.select('//span[@id="cphMain_lblSelectedColour"]/b/text()').extract()
                product_name = product_name + ' - ' + size_desc

            loader.add_value('identifier', identifier )
            loader.add_value('name', product_name.replace(' - Collect Only', ''))

            if option_price:
                loader.add_value('price', option_price.group(1))
            else:
                loader.add_value('price', price)
        else:
            loader.add_value('identifier', identifier)
            loader.add_value('name', product_name.replace(' - Collect Only', ''))
            loader.add_value('price', price)

        yield loader.load_item()
