from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from urlparse import urljoin as urljoin_rfc
from scrapy.utils.response import get_base_url
from product_spiders.utils import extract_price
from scrapy.http import Request
import json
import re


class MacysComSpider(BaseSpider):
    name = 'macys.com'
    allowed_domains = ['macys.com']
    start_urls = (
        'http://www.macys.com',
        # 'http://www1.macys.com/shop/kitchen/calphalon?id=7558&edge=hybrid&viewall=true&intnl=true&intnl=true',
        # 'http://www1.macys.com/shop/dining-entertaining/flatware-silverware?id=7919&edge=hybrid&viewall=true&intnl=true',
    )
    total_page_regex = re.compile('totalPageCount: (\d*)')
    id_regex = re.compile('id=(\d+)')
    product_ids_regex = re.compile('<div id="metaProductIds" class="hidden">(\[.*\])')
    number = re.compile('(\d+)')

    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        categories_ids = hxs.select('//div[@id="globalMastheadFlyout"]//li/@id').extract()
        for id__ in categories_ids:
            cat_id = id__.split('_')[-1]
            yield Request(
                "http://www1.macys.com/shop/for-the-home/home-decor/Pageindex,Productsperpage/1,60?id={category_id}".format(
                    category_id=cat_id
                ),
                callback=self.parse_category,
            )

    def parse_category(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        # products
        products = hxs.select("//div[@class='shortDescription']//a/@href").extract()
        for url in products:
            yield Request(
                urljoin_rfc(base_url, url),
                callback=self.parse_product
            )

        # next page , if there is one
        for next_page in hxs.select('//div[@id="paginateTop"]/a[contains(@class, "arrowRight")]/@href').extract():
            yield Request(next_page, callback=self.parse_category)
        nr_of_pages = self.total_page_regex.findall(response.body)
        if nr_of_pages and 'thumbnail' not in response.url:
            cat_id = self.id_regex.findall(response.url)[0]
            for i in range(int(nr_of_pages[0])):
                yield Request(
                    "http://www1.macys.com/catalog/category/facetedmeta?edge=hybrid&categoryId=%s&facet=false&dynamicfacet=true&pageIndex=%d&productsPerPage=60&" %(cat_id, i+1),
                    callback=self.parse_next_page_product_ids,
                    meta={'category_id': cat_id}
                )

    def parse_next_page_product_ids(self, response):
        hxs = HtmlXPathSelector(response)
        # self.log(str(self.product_ids_regex.findall(response.body)))
        products_text = self.product_ids_regex.findall(response.body)
        self.log(str(products_text))
        cat_id = response.meta['category_id']
        if products_text:
            products_ids = self.number.findall(products_text[0])
            products = ["{cat}_{prod}".format(cat=cat_id, prod=p) for p in products_ids]
            self.log(str(products))
            yield Request(
                'http://www1.macys.com/shop/catalog/product/thumbnail/1?edge=hybrid&limit=none&categoryId={}&ids={}'.format(
                    cat_id,
                    ','.join(products)
                ),
                callback=self.parse
            )
            for product_id in products_ids:
                yield Request('http://www1.macys.com/shop/product?ID=%s' %product_id, callback=self.parse_product)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        name = hxs.select('//h1[@id="productTitle"]/text()').extract()
        if not name:
            return
        price = hxs.select('//div[@id="productDescription"]/div[@id="priceInfo"]//meta[@itemprop="price"]/@content').extract()
        if not price:
            price = hxs.select('//div[@id="priceInfo"]/div[@class="standardProdPricingGroup"]/span/text()').extract()

        identifier = hxs.select('//input[@id="productId"]/@value').extract().pop()
        sku = identifier

        category = " > ".join(hxs.select('//div[@id="breadCrumbsDiv"]/a/text()').extract())

        # Options for this and all related products
        upcmap = hxs.select('//script[contains(text(), "MACYS.pdp.upcmap")]').re('MACYS.pdp.upcmap\["([0-9]+)"\] = (.*);')
        if len(upcmap) > 1:
            upcmap = dict(zip(upcmap[0::2], upcmap[1::2]))
        else:
            upcmap = {}
        # Images for options
        images = hxs.select('//script[contains(text(), "MACYS.pdp.primaryImages")]').re('MACYS.pdp.primaryImages\[([0-9]+)\] = (.*);')
        if len(images) > 1:
            images = dict(zip(images[0::2], images[1::2]))
        else:
            images = {}

        # Options
        if identifier in upcmap:
            product = Product()
            product['name'] = name.pop()
            product['sku'] = identifier
            product['url'] = response.url
            product['category'] = category
            if price:
                product['price'] = extract_price(price.pop())
                if "This product is currently unavailable"  in hxs.select('//ul[@class="similarItems"]/li/span/text()').extract():
                    product['stock'] = 0
                else:    
                    product['stock'] = 1
                for item in self.parse_options(product, upcmap[identifier], images[identifier]):
                    yield item
        # Related products
        related = hxs.select('//div[contains(@class, "memberProducts")]')
        for product in related:
            name = product.select('.//div[@id="prodName"]/text()').extract().pop()
            identifier = product.select('.//div[@class="tfc-fitrec-product"]/@id').extract().pop()
            price = extract_price(product.select('.//meta[@itemprop="price"]/@content').extract().pop())
            product = Product()
            product['name'] = name
            product['sku'] = identifier
            product['url'] = response.url
            product['price'] = price
            product['category'] = category
            for item in self.parse_options(product, upcmap[identifier], images[identifier]):
                yield item

    def parse_options(self, product, options, images):
        options = json.loads(options)
        images = json.loads(images)
        name = product['name']
        for option in options:
            name_add = []
            if option['color']:
                name_add.append(option['color'])
            if option['size']:
                name_add.append(option['size'])
            if option['type']:
                name_add.append(option['type'])

            product['name'] = "%s %s" % (name, " ".join(name_add))
            product['identifier'] = "%s-%s" % (product['sku'], option['upcID'])
            #if option['availabilityMsg'].lower().startswith("in stock"):
            loader = ProductLoader(item=product, selector="")
            if option['color'] in images:
                image_url = "http://slimages.macys.com/is/image/MCY/products/" + images[option['color']]
                loader.add_value('image_url', image_url)
            yield loader.load_item()
