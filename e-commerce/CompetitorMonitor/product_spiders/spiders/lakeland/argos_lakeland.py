import urlparse
import re
import os
import xlrd

from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.spider import BaseSpider
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc
from scrapy import log

from product_spiders.base_spiders import PrimarySpider
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.utils import extract_price

HERE = os.path.abspath(os.path.dirname(__file__))


class ArgosLakelandSpider(PrimarySpider):
    name = 'argos-lakeland'
    allowed_domains = ['argos.co.uk', 'argos.scene7.com']
    csv_file = 'lakeland_argos_as_prim.csv'
    start_urls = [
        # Storage, desks and filling
        'http://www.argos.co.uk/static/Browse/ID72/33008937/c_1/1|category_root|Home+and+garden|33005908/c_2/2|cat_33005908|Storage%2C+desks+and+filing|33008937.htm',

        # Homeware and accessories
        'http://www.argos.co.uk/static/ArgosPromo3/includeName/bathroom-shop.htm',
        'http://www.argos.co.uk/static/Browse/ID72/37924427/c_1/1|category_root|Home+and+garden|33005908/c_2/2|cat_33005908|Bedding|37924427.htm',
        'http://www.argos.co.uk/static/Browse/ID72/33007755/c_1/1|category_root|Home+and+garden|33005908/c_2/2|cat_33005908|Cooking%2C+dining+and+kitchen+equipment|33007755.htm',
        'http://www.argos.co.uk/static/Browse/ID72/33015482/c_1/1|category_root|Home+and+garden|33005908/c_2/2|33005908|Home+furnishings|33007198/c_3/3|cat_33007198|Blinds%2C+curtains+and+accessories|33015482.htm',
        'http://www.argos.co.uk/static/Browse/ID72/33007198/c_1/1|category_root|Home+and+garden|33005908/c_2/2|cat_33005908|Home+furnishings|33007198.htm',
        'http://www.argos.co.uk/static/Browse/ID72/33013696/c_1/1|category_root|Home+and+garden|33005908/c_2/2|33005908|Cooking%2C+dining+and+kitchen+equipment|33007755/c_3/3|cat_33007755|Kitchen+storage|33013696.htm',
        'http://www.argos.co.uk/static/Browse/ID72/33013670/c_1/1|category_root|Home+and+garden|33005908/c_2/2|33005908|Cooking%2C+dining+and+kitchen+equipment|33007755/c_3/3|cat_33007755|Kitchenware|33013670.htm',
        'http://www.argos.co.uk/static/Browse/ID72/33007566/c_1/1|category_root|Home+and+garden|33005908/c_2/2|cat_33005908|Laundry+and+cleaning|33007566.htm',
        'http://www.argos.co.uk/static/Browse/ID72/37907969/c_1/1|category_root|Home+and+Garden|33005908/c_2/2|cat_33005908|Lighting|37907969.htm',
        'http://www.argos.co.uk/static/Browse/ID72/33007638/c_1/1|category_root|Home+and+garden|33005908/c_2/2|cat_33005908|Pet+supplies|33007638.htm',
        'http://www.argos.co.uk/static/Browse/ID72/33015510/c_1/1|category_root|Home+and+garden|33005908/c_2/2|33005908|Home+furnishings|33007198/c_3/3|cat_33007198|Rugs+and+mats|33015510.htm',
        'http://www.argos.co.uk/static/Browse/ID72/33016995/c_1/1|category_root|Home+and+garden|33005908/c_2/2|33005908|Cooking%2C+dining+and+kitchen+equipment|33007755/c_3/3|cat_33007755|Tableware|33016995.htm',
        'http://www.argos.co.uk/static/Browse/ID72/33013307/c_1/1|category_root|Home+and+garden|33005908/c_2/2|33005908|Laundry+and+cleaning|33007566/c_3/3|cat_33007566|Washing+lines+and+airers|33013307.htm',

        # Home electricals
        'http://www.argos.co.uk/static/Browse/ID72/40384661/c_1/1|category_root|Home+and+garden|33005908/c_2/2|33005908|Large+kitchen+appliances|33008255/c_3/3|cat_33008255|Built-in+integrated+appliances|40384661.htm',
        'http://www.argos.co.uk/static/Browse/ID72/40835839/c_1/1|category_root|Home+and+garden|33005908/c_2/2|33005908|Floorcare|40835641/c_3/3|cat_40835641|Carpet+cleaners+and+accessories|40835839.htm',
        'http://www.argos.co.uk/static/Browse/ID72/33014862/c_1/1|category_root|Home+and+garden|33005908/c_2/2|33005908|Large+kitchen+appliances|33008255/c_3/3|cat_33008255|Cooking|33014862.htm',
        'http://www.argos.co.uk/static/Browse/ID72/33016098/c_1/1|category_root|Home+and+garden|33005908/c_2/2|33005908|Large+kitchen+appliances|33008255/c_3/3|cat_33008255|Fridge+freezers|33016098.htm',
        'http://www.argos.co.uk/static/Browse/ID72/33017080/c_1/1|category_root|Home+and+garden|33005908/c_2/2|33005908|Kitchen+electricals|33007917/c_3/3|cat_33007917|Kettles|33017080.htm',
        'http://www.argos.co.uk/static/Browse/ID72/33007917/c_1/1|category_root|Home+and+garden|33005908/c_2/2|cat_33005908|Kitchen+electricals|33007917.htm',
        'http://www.argos.co.uk/static/Browse/ID72/33008255/c_1/1|category_root|Home+and+garden|33005908/c_2/2|cat_33005908|Large+kitchen+appliances|33008255.htm',
        'http://www.argos.co.uk/static/Browse/ID72/40835833/c_1/1|category_root|Home+and+garden|33005908/c_2/2|33005908|Floorcare|40835641/c_3/3|cat_40835641|Handheld+and+cordless+cleaners|40835833.htm',
        'http://www.argos.co.uk/static/Browse/ID72/33017029/c_1/1|category_root|Home+and+garden|33005908/c_2/2|33005908|Laundry+and+cleaning|33007566/c_3/3|cat_33007566|Irons|33017029.htm',
        'http://www.argos.co.uk/static/Browse/ID72/40835793/c_1/1|category_root|Home+and+garden|33005908/c_2/2|33005908|Floorcare|40835641/c_3/3|cat_40835641|Steam+cleaners+and+accessories|40835793.htm',
        'http://www.argos.co.uk/static/Browse/ID72/33014029/c_1/1|category_root|Home+and+garden|33005908/c_2/2|33005908|Kitchen+electricals|33007917/c_3/3|cat_33007917|Toasters|33014029.htm',
        'http://www.argos.co.uk/static/Browse/ID72/33012718/c_1/1|category_root|Home+and+garden|33005908/c_2/2|33005908|Large+kitchen+appliances|33008255/c_3/3|cat_33008255|Tumble+dryers|33012718.htm',
        'http://www.argos.co.uk/static/Browse/ID72/40835641/c_1/1|category_root|Home+and+garden|33005908/c_2/2|cat_33005908|Floorcare|40835641.htm',
        'http://www.argos.co.uk/static/Browse/ID72/33012832/c_1/1|category_root|Home+and+garden|33005908/c_2/2|33005908|Large+kitchen+appliances|33008255/c_3/3|cat_33008255|Washing+machines|33012832.htm',
        'http://www.argos.co.uk/static/Browse/ID72/33012700/c_1/1|category_root|Home+and+garden|33005908/c_2/2|33005908|Large+kitchen+appliances|33008255/c_3/3|cat_33008255|Washer+dryers|33012700.htm',

        # Walpapers, paintings and decorations
        'http://www.argos.co.uk/static/Browse/ID72/33010334/c_1/1|category_root|Home+and+garden|33005908/c_2/2|33005908|Home+improvements|33007046/c_3/3|cat_33007046|Wallpaper+and+decorating|33010334.htm',

        'http://www.argos.co.uk/static/ArgosPromo3/includeName/kitchen-dining-shop.htm?tag=ar:gnav:ShopKitchenDining',
        'http://www.argos.co.uk/static/ArgosPromo3/includeName/storage-shop.htm?tag=ar:gnav:ShopStorage',

        'http://www.argos.co.uk/static/Browse/ID72/38082954/c_1/1|category_root|Gifts|33005782/c_2/2|cat_33005782|Home+and+garden+gifts|38082954.htm',
        'http://www.argos.co.uk/static/Browse/ID72/38082936/c_1/1|category_root|Gifts|33005782/c_2/2|cat_33005782|Food+and+drink|38082936.htm',
        'http://www.argos.co.uk/static/Browse/ID72/38082942/c_1/1|category_root|Gifts|33005782/c_2/2|cat_33005782|Mini+fridges|38082942.htm',

    ]

    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        # categories and subcategories
        for cat_href in hxs.select("//div[@id='categories']//li/a/@href").extract():
            yield Request(
                urlparse.urljoin(get_base_url(response), cat_href)
            )

        # promotional
        for promo_href in hxs.select("//div[@class='ss-row']//a[h2 and img]/@href").extract():
            yield Request(
                urlparse.urljoin(get_base_url(response), promo_href)
            )

        # products
        for product in hxs.select("//dl[@name]"):
            product_link = product.select(".//dd[contains(concat('',@class,''), 'image')]/a/@href").extract()[0]
            self.log(product_link)
            yield Request(
                product_link,
                callback=self.parse_product
            )

        # products next page
        for next_page in set(hxs.select("//a[@rel='next']/@href").extract()):
            yield Request(
                next_page
            )

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)

        url = response.url
        l = ProductLoader(item=Product(), response=response)

        # name
        name = response.xpath('//h1[@class="product-name-main"]/*[@itemprop="name"]/text()').extract()
        if not name:
            name = hxs.select('//h2[@class="product-title"]/text()').extract()

        if not name:
            self.log("ERROR! NO NAME! %s" % url)
            log.msg('ERROR! NO NAME!')
            if response.url.endswith('.htm'):
                yield Request(response.url.replace('.htm', '.html'), callback=self.parse_product)
            return
        name = name[0].strip()
        l.add_value('name', name)

        # price
        price = response.xpath(
            '//div[contains(@class, "product-price-wrap")]/div[@itemprop="price"]/@content').extract()
        price = extract_price("".join(price).strip())
        l.add_value('price', price)

        # sku
        sku = response.xpath("//li//text()[contains(., 'EAN')]").re('EAN: (.*)\.')
        if sku:
            sku = sku[0].split(":")[-1].split('.')[0].strip()
            l.add_value('sku', sku)

        # identifier
        identifier = response.url.split('/')[-1].split('.')[0]
        l.add_value('identifier', identifier)

        # category
        categories = response.xpath('//ol[contains(@class, "breadcrumb")]//a/span/text()').extract()[-3:]

        l.add_value('category', categories)

        # product image
        image_url = response.xpath('//meta[@property="og:image"]/@content').extract()
        l.add_value('image_url', image_url)
        # url
        l.add_value('url', url)
        # brand
        l.add_xpath('brand', "//span[@class='product-name-brand']/a[@itemprop='brand']/text()")

        product = l.load_item()

        meta_data = ' '.join([x.strip() for x in response.xpath('//div/span[@class="price-was"]/text()').extract()])
        product['metadata'] = {}
        product['metadata']['promotional_data'] = meta_data

        if not product.get('image_url', None):
            image_url_req = 'http://argos.scene7.com/is/image/Argos?req=set,json&imageSet='+product['identifier']+'_R_SET'
            yield Request(image_url_req, callback=self.parse_image, meta={'product': product})
        else:
            yield product

    def parse_image(self, response):
        product = response.meta['product']
        image_url = re.findall('"img_set","n":"(.*)","item', response.body)
        if image_url:
            image_url = 'http://argos.scene7.com/is/image/' + image_url[0]
            product['image_url'] = image_url

        yield product
