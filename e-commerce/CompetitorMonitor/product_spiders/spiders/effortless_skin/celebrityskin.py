# -*- coding: utf-8 -*-
import re

from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.utils.url import  urljoin_rfc

from product_spiders.items import Product, ProductLoader
from product_spiders.base_spiders.primary_spider import PrimarySpider

class CelebritySkinSpider(PrimarySpider):
    name = "www.celebrity-skin.co.uk"
    allowed_domains = ["http://www.celebrity-skin.co.uk/"]
    start_urls = (
        "http://www.celebrity-skin.co.uk/",
    )

    products_parsed = []
    links_parsed = []
    #download_delay = 5
    download_timeout = 300

    csv_file = 'celebrityskin_crawl.csv'

    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        categories = []

        #Gets the links to the categories and subcategories, returns full hrefs
        #categories = hxs.select('//div[@id="az_category_menu"]//ul/li[@class="az_menu_item"]//a/@href').extract()
        categories = hxs.select('//div[@id="column-left"]//ul[@class="box-category"]/li//a/@href').extract()

        for cat in categories:
            self.log("CAT")
            self.log(cat)
            request = Request(cat, callback=self.parse_listing, dont_filter=True)
            request.meta['yield'] = True
            yield request

    def parse_listing(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        self.log("PARSING LISTING")

        #Check for products
        #products = hxs.select('//div[@class="az_pgrid"]//span[@class="az_pimg"]/a/@href').extract()

        product_urls = hxs.select('//div[@class="product-list"]/div[@class="product-container"]/div/div[@class="name"]/a/@href').extract()


        for product in product_urls:

            self.log("open product: " + product)

            request = Request(product, callback=self.parse_product, dont_filter=True)
            yield request

        #Check for pagination
        #pages = hxs.select('//div[@class="az_label"]//a[@class="az_steps"]')
        pages = hxs.select('//div[@class="pagination"]/div[@class="links"]/a')


        self.log("PAGES: " + str(len(pages)))
        for page in pages:
            self.log(page.select('@href').extract()[0])

        if pages:
            #Follow the arrow 
            if ' > ' in pages[-1].select('text()').extract():
                link = pages[-1].select('@href').extract()[0]
                if link not in self.links_parsed:
                    self.links_parsed.append(link)

                    self.log("open page1: " + link)

                    request = Request(link, callback=self.parse_listing, dont_filter=True)
                    request.meta['yield'] = True
                    yield request
            #If there is no arrow, just follow the last links
            else:
                if response.meta['yield']:
                    for page in pages:
                        link = page.select('@href').extract()[0]
                        if link not in self.links_parsed:
                            self.links_parsed.append(link)

                            self.log("open page2: " + link)

                            request = Request(link, callback=self.parse_listing, dont_filter=True)
                            request.meta['yield'] = False
                            yield request

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)

        if response.url in self.products_parsed:
            return
        self.products_parsed.append(response.url)

        loader = ProductLoader(response=response, item=Product() )
        base_url = get_base_url(response)

        self.log("parse_product " + response.url)

        price = None
        category = None
        crumbs = None
        brand = None

        #price = hxs.select('//div[@class="az_infomodel az_infoprice1"]//h2/text()').extract()[0][1:]
        #if not price:
        #    special_price = hxs.select('//div[@class="az_infomodel az_infoprice1"]//div[@class="az_info_special"]/text()').extract()
        #    if special_price:
        #        price = special_price[0][1:]
        #    else:
        #        price = "No price"

        loader.add_value('url', response.url)

        price = hxs.select('//div[@class="product-info"]/div[@class="right"]/div[@class="price"]/div/text()').extract()
        if not price:
            self.log("ERROR price not found")
            return
            #
            # if response.meta.get('retries', 0) < 3:
            #     self.log("trying again: " + str(response.meta.get('retries', 0)))
            #
            #     yield Request(response.url, callback=self.parse_product, dont_filter=True,
            #               meta={'retries': response.meta.get('retries', 0) + 1})
            #     return
            # else:
            #     self.log("ERROR price not found: failed")
            #     return

        else:
            #Price: £32.00
            p = price[0].strip()
            m = re.search('((?<= )(.*))', p)
            if not m:
                self.log("ERROR price not found2: " + p)
                return
            else:
                loader.add_value("price", m.group(1).strip())

            #loader.add_value('price', price[0])

        #name = hxs.select('//div[@class="az_infoname"]//h1/text()').extract()[0]
        name = hxs.select('//div[@class="product-info"]/div[@class="left"]/h2/text()').extract()
        if not name:
            self.log("ERROR name not found")
            return
        else:
            loader.add_value('name', name[0].strip())

        categories = hxs.select('//div[@id="content"]/div[@class="breadcrumb"]/a/text()').extract()
        if not categories:
            self.log("ERROR categories not found")
        else:
            if len(categories)>=2:
                category = categories[-2]
            else:
                category = categories[-1]

            loader.add_value('category', category)


        img = hxs.select('//div[@class="left"]/div[@class="image"]/a/img/@src').extract()
        if not img:
            self.log("ERROR img not found")
        else:
            loader.add_value("image_url",urljoin_rfc(get_base_url(response), img[0]))

        #crumbs = hxs.select('//div[@class="az_header_bottom_sub1"]')
        #try:
        #    identifier = crumbs.select('a[last()]/text()').extract()[0]
        #    #An identifier is not always present
        #except IndexError:
        #    identifier = None
        #category = crumbs.select('a[last()-1]/text()').extract()[0]

        #img_url = hxs.select('//div[@class="contentText"]//a//img/@src').extract()[0]
        #img_url = hxs.select('//img[@id="product_medium_image"]/@src').extract()[0]

        #final_im_url = urljoin_rfc(base_url, img_url)




        id = hxs.select('//input[@name="product_id"]/@value').extract()
        if not id:
            self.log("ERROR id not found")
        else:
            loader.add_value('identifier', id[0])

        #loader.add_value('image_url', final_im_url)

        #if identifier:
        #    loader.add_value('metadata', 'Product ID: %s' % identifier)


        #if brand:
        #    loader.add_value('brand', brand)
        #loader.add_value('shipping_cost', 'N/A')

        is_fade = hxs.select("//img[@alt='In Stock']/@class").extract()
        oos_fade = hxs.select("//img[@alt='Out of Stock']/@class").extract()
        if not oos_fade or is_fade:
            stock = '0'
        else:
            stock = None

        loader.add_value('stock', stock)

        brand = hxs.select("//div[@class='brand']/a/img/@alt").extract()
        if brand:
            loader.add_value('brand', brand[0])

        yield loader.load_item()

