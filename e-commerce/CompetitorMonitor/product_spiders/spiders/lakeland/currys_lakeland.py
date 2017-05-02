import urlparse
import os
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.spider import BaseSpider
from scrapy.utils.response import get_base_url

from product_spiders.base_spiders import PrimarySpider
from product_spiders.items import Product, ProductLoader
from product_spiders.utils import extract_price

HERE = os.path.abspath(os.path.dirname(__file__))


class CurrysLakelandSpider(PrimarySpider):
    name = 'currys-lakeland'
    allowed_domains = ['currys.co.uk']
    csv_file = 'lakeland_currys_as_prim.csv'
    start_urls = ['http://www.currys.co.uk/gbuk/household-appliances-35-u.html',
                  'http://www.currys.co.uk/gbuk/home-appliances-36-u.html',
                  ]
    # start_urls = [
    #     'http://www.currys.co.uk/gbuk/household-appliances/cooking-335-c.html',
    #     'http://www.currys.co.uk/gbuk/household-appliances/cookware-400-c.html',
    #     'http://www.currys.co.uk/gbuk/household-appliances/cookware/baking/400_3405_32027_xx_xx/xx-criteria.html',
    #     'http://www.currys.co.uk/gbuk/utensils-and-gadgets/cookware/food-preparation-and-kitchen-accessories/400_4410_32112_xx_ba00011155-bv00309140/xx-criteria.html',
    #     'http://www.currys.co.uk/gbuk/household-appliances/cookware/food-and-drink-storage/400_4411_32113_xx_xx/xx-criteria.html',
    #     'http://www.currys.co.uk/gbuk/household-appliances/cookware/food-preparation-and-kitchen-accessories/400_4410_32112_xx_xx/xx-criteria.html',
    #
    #     'http://www.currys.co.uk/gbuk/household-appliances/small-kitchen-appliances/kitchen-accessories/336_3166_30254_xx_xx/xx-criteria.html',
    #
    #     'http://www.currys.co.uk/gbuk/household-appliances/cooking/cooking-accessories/335_4408_32087_xx_xx/xx-criteria.html',
    #
    #     'http://www.currys.co.uk/gbuk/household-appliances/small-kitchen-appliances/toasters/336_3157_30245_xx_xx/xx-criteria.html',
    #     'http://www.currys.co.uk/gbuk/household-appliances/small-kitchen-appliances/kettles/336_3156_30244_xx_xx/xx-criteria.html',
    #     'http://www.currys.co.uk/gbuk/household-appliances/small-kitchen-appliances/food-and-drink-preparation-3164-m.html',
    #     'http://www.currys.co.uk/gbuk/household-appliances/small-kitchen-appliances/small-cooking-appliances-3155-m.html',
    #     'http://www.currys.co.uk/gbuk/household-appliances/small-kitchen-appliances/coffee-machines-and-accessories-3159-m.html',
    #     'http://www.currys.co.uk/gbuk/coffee-buying-guide-776-commercial.html',
    #
    #     'http://www.currys.co.uk/gbuk/heaters/heating-and-cooling/heaters/339_3176_30264_xx_ba00011175-bv00309163/xx-criteria.html',
    #     'http://www.currys.co.uk/gbuk/fans/heating-and-cooling/heating-and-cooling/339_3176_30264_xx_ba00011175-bv00309164/xx-criteria.html',
    #
    #     'http://www.currys.co.uk/gbuk/household-appliances/refrigeration/refrigeration-accessories/333_3536_31281_xx_xx/xx-criteria.html',
    #     'http://www.currys.co.uk/gbuk/household-appliances/laundry-dishwashers/laundry-dishwasher-accessories/332_3535_31262_xx_xx/xx-criteria.html',
    #
    #     'http://www.currys.co.uk/gbuk/household-appliances/laundry/laundry-accessories/332_3535_31262_xx_xx/xx-criteria.html',
    #
    #     'http://www.currys.co.uk/gbuk/home-appliances/vacuum-cleaners-337-c.html',
    #     'http://www.currys.co.uk/gbuk/household-appliances/small-kitchen-appliances-336-c.html',
    #     'http://www.currys.co.uk/gbuk/home-appliances/fans-air-conditioning-340-c.html',
    #     'http://www.currys.co.uk/gbuk/home-appliances/ironing-338-c.html',
    #
    #     'http://www.currys.co.uk/gbuk/home-appliances/heating-and-cooling-339-c.html',
    #
    #     'http://www.currys.co.uk/gbuk/upright-vacuum-cleaners/floorcare/vacuum-cleaners/337_3169_30257_xx_ba00011174-bv00309152/xx-criteria.html',
    #     'http://www.currys.co.uk/gbuk/cylinder-vacuum-cleaners/floorcare/vacuum-cleaners/337_3169_30257_xx_ba00011174-bv00309153/xx-criteria.html',
    #     'http://www.currys.co.uk/gbuk/cordless-vacuum-cleaners/floorcare/vacuum-cleaners/337_3169_30257_xx_ba00011174-bv00309154/xx-criteria.html',
    #     'http://www.currys.co.uk/gbuk/home-appliances/floorcare/wet-and-dry-cleaners/337_3171_30259_xx_xx/xx-criteria.html',
    #     'http://www.currys.co.uk/gbuk/home-appliances/floorcare/vacuum-accessories/337_3172_30260_xx_xx/xx-criteria.html',
    #     'http://www.currys.co.uk/gbuk/floorcare-buying-guide-345-commercial.html',
    #     'http://www.currys.co.uk/gbuk/home-appliances/ironing/irons/338_3173_30261_xx_xx/xx-criteria.html',
    #     'http://www.currys.co.uk/gbuk/steam-generator-irons/ironing/irons/338_3173_30261_xx_ba00011158-bv00309160/xx-criteria.html',
    #
    # ]

    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        # categories and subcategories
        for cat_href in hxs.select("//div[@class='DSG_wrapper']//li/a/@href").extract():
            yield Request(
                urlparse.urljoin(get_base_url(response), cat_href.strip())
            )

        # subcategories
        sub_categories = hxs.select('//ul[@class="nav-blocks"]/li//a[h3]/@href').extract()
        sub_categories += hxs.select("//aside/nav[1]//a/@href").extract()
        sub_categories += response.xpath('//section[@id="categories"]//a/@href').extract()
        sub_categories += response.xpath('//section[@id="navi"]//a/@href').extract()
        for cat_href in sub_categories:
            yield Request(
                urlparse.urljoin(get_base_url(response), cat_href.strip())
            )

        # products
        products = hxs.select('//article//a[@class="in"]/@href').extract()
        products += hxs.select('//article//a[div[@class="in"]]/@href').extract()
        for product in products:
            yield Request(
                product.strip(),
                callback=self.parse_product
            )

        # products next page
        for next_page in set(hxs.select("//a[@class='next']/@href").extract()):
            yield Request(
                next_page.strip()
            )

        is_product = hxs.select('//meta[@property="og:type"]/@content').extract()

        if is_product:
            for product in self.parse_product(response):
                yield product


    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)

        url = response.url
        l = ProductLoader(item=Product(), response=response)

        # name
        name_l = hxs.select("//div[contains(@class,'product-page')]//h1[@class='page-title nosp']//text()").extract()
        name = ' '.join([x.strip() for x in name_l if x.strip()])
        l.add_value('name', name)

        # price
        price = hxs.select("//meta[@property='og:price:amount']/@content").extract()
        price = extract_price("".join(price))
        l.add_value('price', price)

        # sku
        sku = hxs.select("//div[contains(@class,'product-page')]//meta[@itemprop='identifier']/@content").extract()
        if sku:
            sku = sku[0].split(":")[-1]
            l.add_value('sku', sku)

        # identifier
        identifier = response.url.split('-')[-2]
        l.add_value('identifier', identifier)

        # category
        l.add_xpath('category', "//div[@class='breadcrumb']//a[position() > 1]/span/text()")

        # product image
        l.add_xpath('image_url', "//meta[@property='og:image']/@content")
        # url
        l.add_value('url', url)
        # brand
        l.add_xpath('brand', "//span[@itemprop='brand']/text()")
        # stock
        if hxs.select("//div[contains(concat('', @class,''), 'oos')]") \
                or hxs.select("//li[@class='unavailable']/i[@class='dcg-icon-delivery']"):
            l.add_value('stock', 0)
        else:
            l.add_value('stock', 1)

        product = l.load_item()

        meta_data = hxs.select("//div[@class='prd-amounts']//strong[@class='offer']//text()").extract()
        product['metadata'] = {}
        if meta_data:
            product['metadata']['promotional_data'] = meta_data[0].strip()
        else:
            product['metadata']['promotional_data'] = ''
        yield product
