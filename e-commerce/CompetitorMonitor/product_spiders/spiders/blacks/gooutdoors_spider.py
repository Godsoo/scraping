import re

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse
from scrapy.http import FormRequest
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader


class GoOutdoorsSpider(BaseSpider):
    name = 'blacks-gooutdoors.co.uk'
    allowed_domains = ['gooutdoors.co.uk']
    start_urls = ['http://www.gooutdoors.co.uk/mens/clothing/coats-and-jackets']

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        products = hxs.select('//div[@class="in"]')
        for product in products:
            relative_url = product.select('h3/a/@href').extract()[0]
            yield Request(urljoin_rfc('http://www.gooutdoors.co.uk/',
                                                relative_url,
                                                response.encoding), callback=self.parse_product)
        next_page = hxs.select('//*[@id="pSrchFtr"]/div/span[@class="n"]/a/@href').extract()
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
                                  meta={'category': category})
            return


        loader = ProductLoader(item=Product(), selector=hxs)

        identifier = hxs.select('//div[@class="code"]/text()').extract()[0]
        loader.add_xpath('sku', '//div[@class="code"]/text()')
        loader.add_value('url', response.url)
        product_name = hxs.select('//div[@class="title"]//h1/text()').extract()[0]


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

        if colours:
            colour = hxs.select('//select[@id="cphMain_ddlColour"]/option[@selected]/text()').extract()[0]
            colour_id = hxs.select('//select[@id="cphMain_ddlColour"]/option[@selected]/@value').extract()[0]
            loader.add_value('identifier', identifier + '-' + colour_id)
            loader.add_value('name', product_name + ' - ' + colour.split(u' - \xa3')[0].strip())
            option_price = re.search(r"\xa3(\d+.\d+)", colour)
            if option_price:
                loader.add_value('price', option_price.group(1))
            else:
                loader.add_value('price', price)
            colour = colour.split(u' - \xa3')[0].strip()
        else:
            colour = hxs.select('//span[@id="cphMain_lblSelectedColour"]/b/text()').extract()
            if colour:
                product_name = product_name + ' - ' + colour[0].strip()
            colour = ''.join(colour)
            loader.add_value('identifier', identifier)
            loader.add_value('name', product_name)
            loader.add_value('price', price)


        image_id = hxs.select('//img[@alt="'+colour.strip().upper()+'"]/@src').re(r'Products/(\d+)-')
        if not image_id:
            image_id = hxs.select('//img[@alt="'+colour.strip()+'"]/@src').re(r'Products/(\d+)-')
        prod_id = re.search(r'ProdId=(.*)&', response.url)
        if prod_id and image_id:
            image_id = image_id[0]
            prod_id = prod_id.group(1)
            product = loader.load_item()
            image_page = 'http://www.gooutdoors.co.uk/ZoomProductImages.aspx?ProductId=%s&ProductImageId=%s' % (prod_id, image_id)
            yield Request(image_page, callback=self.parse_image, meta={'product': product})
        else:
            yield loader.load_item()

    def parse_image(self, response):
        hxs = HtmlXPathSelector(response)
        product = response.meta.get('product')
        image_url = hxs.select('//img[@id="imgThumb"]/@src').extract()
        if image_url:
            product['image_url'] = image_url[0]
        yield product
