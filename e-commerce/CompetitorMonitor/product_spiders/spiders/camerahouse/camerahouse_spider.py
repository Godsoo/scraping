import csv
import os
import os.path
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.fuzzywuzzy import process
from product_spiders.fuzzywuzzy import fuzz
import re

HERE = os.path.abspath(os.path.dirname(__file__))

from scrapy import log

m_brands_dict = {
    "productbrandlogo-sandisk.jpg" : "SanDisk",
    "bushnell_lisitinglogo.jpg" : "Bushnell",
    "rode_logo_main.jpg":"Rode",
    "productbrandlogo-canon.jpg":"Canon",
    "productbrandlogo-olympus.jpg":"Olympus",
    "productbrandlogo-pentax.jpg":"Pentax",
    "manfrotto_lisitinglogo.jpg":"Manfrotto",
    "tamrac_logo_main.jpg":"Tamrac",
    "tamron_lisitinglogo.jpg":"Tamron",
    "sigma_lisitinglogo.jpg":"Sigma",
    "productbrandlogo-lowepro.jpg":"Lowepro",
    "productbrandlogo-wambam.jpg":"Wam Bam",
    "productbrandlogo-fujifilm.jpg":"Fujifilm",
    "nikonlogo.jpg":"Nikon",
    "pinnacle_logo_main.jpg":"Pinnacle",
    "productbrandlogo-kaiserbaas.jpg":"Kaiser Baas",
    "adobe_logo_main.jpg":"Adobe",
    "productbrandlogo-jvc.jpg":"JVC",
    "oregon_lisitinglogo.jpg":"Oregon",
    "polaroid_lisitinglogo.jpg":"Polaroid",
    "astak_logo_product_list_item.jpg":"astak",
    "productbrandlogo-sony.jpg":"Sony",
    "fatgecko_logo_main.jpg":"Fat Gecko",
    "digiframe_logo_main2.jpg":"DigiFrame",
    "productbrandlogo-panasonic.jpg":"Panasonic",
    "productbrandlogo-samsung.jpg":"Samsung",
    "casio_lisitinglogo.jpg":"Casio",
    "productbrandlogo-gopro.jpg":"Go Pro",
    "hahnel_logo_main.jpg":"hahnel",
    "impossible_logo_main.jpg":"Impossible",
    "lisitinglogo_garyfong.jpg":"Gary Fong",
    "matin_logo_main.jpg":"Matin",
    "optex_logo_main.jpg":"Optex",
    "que_logo_product_list_item.jpg":"Que",
    "productbrandlogo-agfaphoto.jpg":"AgfaPhoto",
    "speedo_logo_product_list_item.jpg":"Speedo",
    "contour_logo_main.jpg":"Contour",
    "tasco_lisitinglogo.jpg":"Tasco",
    "gorillapod_logo_main.jpg":"Gorillapod",

}

class CameraHouseSpider(BaseSpider):
    name = 'camerahouse.com.au'
    allowed_domains = ['camerahouse.com.au']
    start_urls = ['http://www.camerahouse.com.au/products.aspx']

    def __init__(self, *args, **kwargs):
        super(CameraHouseSpider, self).__init__(*args, **kwargs)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        categories = hxs.select('//div[@class="left_menu"]/div/ul/li/a/@href').extract()
        for category_url in categories:
            url = urljoin_rfc(get_base_url(response), category_url)
            yield Request(url)

        sub_categories = hxs.select('//div[@class="desc"]/h3/a/@href').extract()
        for sub_category_url in sub_categories:
            url = urljoin_rfc(get_base_url(response), sub_category_url)
            yield Request(url)

        products = hxs.select('//div[@class="box_product"]')
        if products:
            for product in products:
                url = urljoin_rfc(get_base_url(response), product.select('a/@href').extract()[0])
                loader = ProductLoader(item=Product(), response=response)
                # loader.add_value('sku', response.meta['sku'])
                # loader.add_value('identifier', response.meta['sku'].lower())
                name = product.select('a/h3/text()').extract()[0]
                loader.add_value('name', name)

                loader.add_value('url', url)
                #loader.add_value('price', 0)
                yield Request(url=loader.get_output_value('url'),
                              meta={"loader": loader},
                              callback=self.parse_product)

            next_page = hxs.select('//a[contains(text(), "Next")]/@href').extract()
            if next_page:
                url = urljoin_rfc(get_base_url(response), next_page[-1])
                yield Request(url)

    def parse_product(self, response):

        hxs = HtmlXPathSelector(response)
        loader = response.meta['loader']

        brand_img_url = hxs.select('//img[@id="ContentPlaceHolderDefault_CameraHouseMasterContentPlaceHolder_EntryControl_4_ctl00_imgLogoThumb"]/@src').extract()
        if not brand_img_url:
            self.log("ERROR brand_img_url not found")
        else:
            brand_filename = brand_img_url[0].split('/')[-1]
            if not brand_filename in m_brands_dict:
                self.log("ERROR brand not found: " + brand_filename)
            else:
                loader.add_value("brand", m_brands_dict[brand_filename])


        category = hxs.select('(//div[@class="breadcrumb"]/ul[@class="navlist"]/li/a)[last()]/text()').extract()
        if not category:
            self.log("ERROR category not found")
        else:
            loader.add_value('category', category[0])

        img = hxs.select('//img[@id="ImgProductSmall"]/@src').extract()
        if not img:
            self.log("ERROR img not found")
        else:
            loader.add_value("image_url", urljoin_rfc(get_base_url(response), img[0]))

        identifier = None
        if img:
            identifier = img[0].split('/t/')[1].rpartition('-')[0]

        try:
            loader.add_value("identifier", identifier)
        except:
            return

        try:
            price = hxs.select('//div/div[@class="price"]/text()').extract()[0].strip()
        except:
            return
        loader.add_value("price", price)

        sku = hxs.select('//script/text()').re('google_base_offer_id\", \"(.*)\"')
        if sku:
            loader.add_value('sku', sku)

        delivery = hxs.select('//div[@class="product_overview_sidebar"]/span[@rel=".ttip_home_delivery"]/text()').extract()
        if not delivery:
            self.log("ERROR delivery not found")
        else:
            d = delivery[0].strip()
            m = re.search('((?<=\- \$)(.*))', d)
            if not m:
                self.log("ERROR delivery not found2")
            else:
                shipping_cost = m.group(1)
                loader.add_value("shipping_cost", shipping_cost.strip())

        yield loader.load_item()

        return


