import re
from copy import copy

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from product_spiders.items import Product
from productloader import WindowsCleaningProductLoader


class DetroitSpongeSpider(BaseSpider):
    name = 'detroitsponge.com'
    start_urls = ('http://www.detroitsponge.com/',)

    def parse(self, response):
        BASE = get_base_url(response)
        #categories
        hxs = HtmlXPathSelector(response)
        categories = hxs.select('//a/@href').re('(.*c-\d+.*)')
        for url in categories:
            url = urljoin_rfc(BASE, url)
            yield Request(url)

        # products
        products = hxs.select('//a/@href').re('(.*p-\d+-.*)')
        for url in products:
            yield Request(urljoin_rfc(BASE, url), callback=self.parse_product)


    def parse_product(self, response):
        if not isinstance(response, HtmlResponse):
            return
        identifier = re.search('/p-(\d+)-', response.url).group(1)
        BASE = get_base_url(response)
        # sub products
        hxs = HtmlXPathSelector(response)
        image_url = hxs.select('//img[contains(@id,"ProductPic")]/@src').extract()
        image_url = urljoin_rfc(BASE, image_url[0]) if image_url else None
        category = hxs.select('//span[@id="nevTabLink"]/span/a/text()').extract()

        # compound product
        common_desc = hxs.select('//span[@class="ProductNameText"]/text()').extract()
        if not common_desc:
            common_desc = hxs.select('//h1/text()').extract()
        if not common_desc:
            return
        common_desc = common_desc[0]

        # product list
        product_list_nodes = hxs.select('//table[tr[@class="DarkCell"]]/tr[not(@class="DarkCell")]')
        if product_list_nodes:
            i = 0
            for node in product_list_nodes:
                loader = WindowsCleaningProductLoader(item=Product(), response=response)

                sub_product_id = node.select('.//input[@name="VariantID"]/@value').extract()
                if not sub_product_id:
                   continue
                else:
                    sub_product_id = sub_product_id[0]

                loader.add_value('identifier', '%s.%s' % (identifier, sub_product_id))
                loader.add_value('url', response.url)
                if image_url:
                    loader.add_value('image_url', image_url)
                if category:
                    loader.add_value('category', category)
                name = node.select('.//font/text()').extract()
                if name:
                    name = name[0]
                else:
                    return
                loader.add_value('name', common_desc + ' ' + name)
                price = node.select('.//span[@class="variantprice"]//text()').re('Price:.*?(\d.*)')
                if not price:
                    price = node.select('.//span[@class="SalePrice"]//text()').re('.*?\$(\d.*)')
                price = price[0] if price else '0.00'

                loader.add_value('price', price)
                if not loader.get_output_value('price'):
                    loader.add_value('stock', 0)

                sku = node.select('.//*[contains(text(), "SKU")]/../td[2]/text()').extract()
                if not sku:
                    sku = node.select('.//font/text()').extract()
                    if sku:
                        sku = sku[1]
                    else:
                        return

                loader.add_value('sku', sku)
                yield loader.load_item()
                i += 1
            return

        product_list_nodes =  hxs.select('//table[tr/td[@class="GreyCell"]]')
        if product_list_nodes:
            for node in product_list_nodes:
                loader = WindowsCleaningProductLoader(item=Product(), response=response)
                loader.add_value('url', response.url)
                sub_product_id = node.select('.//input[@name="VariantID"]/@value').extract()
                if not sub_product_id:
                   continue
                else:
                    sub_product_id = sub_product_id[0]

                loader.add_value('identifier', '%s.%s' % (identifier, sub_product_id))
                sub_prod_image = node.select('.//img[@id="ProductPic'+sub_product_id+'"]/@src').extract()
                if sub_prod_image:
                    loader.add_value('image_url', urljoin_rfc(BASE,sub_prod_image[0]))
                if category:
                    loader.add_value('category', category)

                name = node.select('tr/td[@class="DarkCell"]/font/text()').extract()
                if name:
                    name = name[0]
                else:
                    return
                loader.add_value('name', common_desc+ ' ' + name)

                sku = node.select('.//tr[td[contains(text(), "SKU")]]/td[not(contains(text(), "SKU"))]/text()').extract()
                if sku:
                    loader.add_value('sku', sku)

                price = node.select('.//span[@class="variantprice"]/text()').re('([\d\.,]+)')
                price = price if price else '0.00'
                loader.add_value('price', price)
                if not loader.get_output_value('price'):
                    loader.add_value('stock', 0)
                yield loader.load_item()
            return




        sub_products = hxs.select('//select[@name="variants"]/option')
        if sub_products:
            for node in sub_products:
                loader = WindowsCleaningProductLoader(item=Product(), response=response)
                loader.add_value('url', response.url)
                sub_product_id = node.select('@value').extract()
                if not sub_product_id:
                    continue
                else:
                    sub_product_id = sub_product_id[0]

                loader.add_value('identifier', '%s.%s' % (identifier, sub_product_id))
                if image_url:
                    loader.add_value('image_url', image_url)
                if category:
                    loader.add_value('category', category)

                name = common_desc + ' ' + node.select('./text()')[0].extract().split(u'\xa0')[0]
                loader.add_value('name', name)
                price = node.select('./span/text()').re('([\d\.,]+)')
                price = price if price else '0.00'
                loader.add_value('price', price)
                if not loader.get_output_value('price'):
                    loader.add_value('stock', 0)
                yield loader.load_item()
            return

        # simple product
        loader = WindowsCleaningProductLoader(item=Product(), response=response)
        loader.add_value('url', response.url)
        if image_url:
            loader.add_value('image_url', image_url)
        if category:
            loader.add_value('category', category)
        name = common_desc
        loader.add_value('name', name)
        loader.add_value('identifier', identifier)
        price = hxs.select('//span[@class="variantprice"]/text()').re('.*?\$(.*)')
        if not price:
            price = hxs.select('//span[@class="SalePrice"]/text()').re('.*?\$(.*)')
        price = price[0] if price else '0.00'

        loader.add_value('price', price)
        if not loader.get_output_value('price'):
            loader.add_value('stock', 0)
        sku = hxs.select('//td[contains(text(), "SKU")]/../td[2]/text()').extract()
        sku = sku if sku else ''

        loader.add_value('sku', sku)
        size_options = hxs.select('//select[@name="Size"]/option[not(contains(text(),"Size"))]/text()').extract()
        if size_options:
            i = 0
            for size in size_options:
                item = copy(loader.load_item())
                item['identifier'] += '.%s' % i
                item['name'] += ' %s' % size
                yield item
                i += 1
            return
        else:
            yield loader.load_item()
