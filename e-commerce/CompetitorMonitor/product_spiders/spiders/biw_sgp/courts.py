import json
import urlparse
from decimal import Decimal
import os
import re

from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest
from scrapy.spider import BaseSpider
from scrapy.utils.response import get_base_url
from scrapy.utils.url import add_or_replace_parameter

from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader

HERE = os.path.abspath(os.path.dirname(__file__))


class CourtsSpider(BaseSpider):
    name = 'courts.com.sg'
    allowed_domains = ['courts.com.sg']
    start_urls = [
        'http://www.courts.com.sg/',
    ]

    post_data = re.compile('urlOnPageLoad":"(.*?)",')

    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        # categories and subcategories
        for cat_href in hxs.select("//div[@class='sub-nav']//li/a/@href").extract():
            url = urlparse.urljoin(get_base_url(response), cat_href)
            url = add_or_replace_parameter(url, 'page', '100')
            yield Request(url, callback=self.parse_category)

    def parse_category(self, response):
        base_url = get_base_url(response)
        for url in response.xpath('//a[@class="listlink"]/@href').extract():
            yield Request(urlparse.urljoin(base_url, url), callback=self.parse_product)
        return

        post_data = self.post_data.findall(response.body)[0]
        form_data = {}
        for d in post_data.split('&'):
            form_data[d.split('=')[0]] = d.split('=')[1]

        yield FormRequest(
            'http://www.courts.com.sg/home/tempsolrhitpage.html?groupField=variantId&group=true&type=list&isAgent=false&group.field=variantId&start=0&rows=12&group.ngroups=true&outOfInventory=',
            formdata=form_data,
            callback=self.parse_product_list,
            meta={'form_data': form_data},
            dont_filter=True
        )

    def parse_product_list(self, response):
        json_data = json.loads(response.body)
        start_on = int(json_data['responseHeader']['params']['start'])
        new_start_on = 12 + start_on
        max_nr_of_products = int(json_data['grouped']['variantId']['ngroups'])

        if new_start_on < max_nr_of_products:
            yield FormRequest(
                re.sub('&start=\d*', '&start={}'.format(new_start_on), response.url),
                formdata=response.meta['form_data'],
                callback=self.parse_product_list,
                meta={'form_data': response.meta['form_data']}
            )

        for group in json_data['grouped']['variantId']['groups']:
            product_name = group['doclist']['docs'][0]['PRODUCTNAME']
            parent_prod_id = group['doclist']['docs'][0]['parentProductId']

            url = 'http://www.courts.com.sg/{name}-{parent_id}-m.html'.format(
                name=re.sub(' ', '-', product_name),
                parent_id=parent_prod_id
            )
            try:
                yield Request(
                    url,
                    callback=self.parse_product,
                    meta={
                        'name': product_name,
                        'price': group['doclist']['docs'][0]['standardPrice_f'],
                        'sku': group['doclist']['docs'][0]['modelNumber'],
                        'brand': group['doclist']['docs'][0]['brand'],
                        'identifier': group['doclist']['docs'][0]['id']

                    }
                )
            except KeyError:
                self.log("KeyError! group['doclist']['docs'][0] is %s" %group['doclist']['docs'])
                yield response.request

    def parse_product(self, response):
        url = response.url
        l = ProductLoader(item=Product(), response=response)

        # name
        l.add_css('name', '.pro-des::text')

        # price
        price = '.'.join(response.xpath('//div[@class="price-strike"]/div/span//text()').re('\d+'))
        l.add_value('price', price)

        # sku
        l.add_xpath('sku', '//div[@class="short-desc"]/span//text()')

        # identifier
        productid = response.xpath('//input[@id="selectedProductIdd"]/@value').extract()[0]
        priceid = response.xpath('//input[@id="priceId"]/@value').extract()[0]
        identifier = '-'.join((productid, priceid))
        l.add_value('identifier', identifier)

        # category
        l.add_xpath('category', "//div[@class='bread']//li[position() > 1]//text()[not(contains(., '>'))]")

        # product image
        l.add_xpath('image_url', "//meta[@property='og:image']/@content")
        # url
        l.add_value('url', url)
        # brand
        l.add_xpath('brand', '//div[@class="added-item"]/h2/text()')
        # shipping
        shipping_cost = 9.9 if l.get_output_value('price') < 200 else 0
        l.add_value('shipping_cost', shipping_cost)
        product = l.load_item()
        
        if not price:
            storeid = response.xpath('//input[@id="storeId"]/@value').extract()[0]
            url = 'http://www.courts.com.sg/home/addtocart.html?isAdd=true&newProduct=true&productId=%s&selectedCurrency=SGD&quantity=1&cartId=na&addQuantity=true&newQuantity=1&shippingOption=&shippingCity=&deliveryOption=&shippingDate=&cityId=&title=&inventorysensible=yes&priceId=%s&storeId=%s'
            yield Request(url %(productid, priceid, storeid), 
                          callback=self.parse_price_from_cart,
                          meta={'product':Product(product),
                                'dont_merge_cookies': True})
        else:
            yield product

    def parse_price_from_cart(self, response):
        loader = ProductLoader(item=response.meta['product'], response=response)
        loader.replace_xpath('price', '//td[@class="right"]/div[@class="prodetail-price"][1]/text()')
        shipping_cost = 9.9 if loader.get_output_value('price') < 200 else 0
        loader.replace_value('shipping_cost', shipping_cost)
        yield loader.load_item()