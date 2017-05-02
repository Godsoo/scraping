import urlparse
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.spider import BaseSpider
from scrapy.utils.response import get_base_url
from product_spiders.items import Product, ProductLoader
from product_spiders.utils import extract_price


class WexCurrysSpider(BaseSpider):
    name = 'wexphotographic_new-currys.co.uk'
    allowed_domains = ['currys.co.uk']
    start_urls = [
        'http://www.currys.co.uk/gbuk/cameras-and-camcorders/digital-cameras/dslr-and-compact-system-cameras/344_3757_31522_xx_xx/xx-criteria.html',
        'http://www.currys.co.uk/gbuk/cameras-and-camcorders/digital-cameras/compact-and-bridge-cameras/344_3199_30301_xx_xx/xx-criteria.html',
        'http://www.currys.co.uk/gbuk/cameras-and-camcorders/camcorders-347-c.html',
        'http://www.currys.co.uk/gbuk/cctv/smart-tech/smart-home/smart-home-cameras-and-cctv/551_4281_32081_xx_ba00010914-bv00308842/xx-criteria.html',
        'http://www.currys.co.uk/gbuk/cameras-and-camcorders/photography-accessories-346-c.html',
        'http://www.currys.co.uk/gbuk/cameras-and-camcorders/photography-accessories/binoculars/346_3797_31507_xx_xx/xx-criteria.html',
        'http://www.currys.co.uk/gbuk/cameras-and-camcorders/photography-accessories/telescopes/346_4407_32086_xx_xx/xx-criteria.html',
        'http://www.currys.co.uk/gbuk/audio-and-headphones-32-u.html',
        'http://www.currys.co.uk/gbuk/audio-and-headphones/audio/hifi-systems-and-speakers/550_4278_31971_xx_xx/xx-criteria.html',
        'http://www.currys.co.uk/gbuk/audio-and-headphones/headphones-291-c.html',
        'http://www.currys.co.uk/gbuk/audio-and-headphones/audio/radios/550_4276_31970_xx_xx/xx-criteria.html',
        'http://www.currys.co.uk/gbuk/audio-and-headphones/audio/ipods-and-mp3-players/550_4275_31953_xx_xx/xx-criteria.html',
        'http://www.currys.co.uk/gbuk/apple-audio-and-headphones/audio/ipods-and-mp3-players/550_4275_31953_267_xx/xx-criteria.html',
        'http://www.currys.co.uk/gbuk/computing-accessories/office-supplies/dictaphones/510_4424_32068_xx_xx/xx-criteria.html',
        'http://www.currys.co.uk/gbuk/phones-broadband-and-sat-nav/sat-nav-403-c.html',
        'http://www.currys.co.uk/gbuk/computing/laptops-315-c.html',
        'http://www.currys.co.uk/gbuk/computing/tablets-and-ereaders-149-c.html',
        'http://www.currys.co.uk/gbuk/computing/projectors-570-c.html',
        'http://www.currys.co.uk/gbuk/computing/desktop-pcs-317-c.html',
        'http://www.currys.co.uk/gbuk/computing/pc-monitors/pc-monitors/354_3057_30059_xx_xx/xx-criteria.html',
        'http://www.currys.co.uk/gbuk/computing-accessories/printers-scanners-and-ink-319-c.html',
        'http://www.currys.co.uk/gbuk/computing-accessories/computer-accessories-318-c.html',
        'http://www.currys.co.uk/gbuk/computing-accessories/computer-accessories/laptop-bags-and-cases/318_3059_30067_xx_xx/xx-criteria.html',
        'http://www.currys.co.uk/gbuk/pc-gaming-1150-commercial.html',
        'http://www.currys.co.uk/gbuk/computing-accessories/data-storage-355-c.html',
        'http://www.currys.co.uk/gbuk/computing-accessories/components-upgrades-324-c.html',
        'http://www.currys.co.uk/gbuk/computing-accessories/software-323-c.html',
        'http://www.currys.co.uk/gbuk/computing-accessories/networking-321-c.html',
        'http://www.currys.co.uk/gbuk/computing-accessories/office-supplies-510-c.html',
        'http://www.currys.co.uk/gbuk/audio-and-headphones/headphones/headphones/291_3919_31664_xx_xx/xx-criteria.html'
    ]

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
        for cat_href in sub_categories:
            yield Request(
                urlparse.urljoin(get_base_url(response), cat_href.strip())
            )

        # products
        for product in hxs.select('//article//a[@class="in"]/@href').extract():
            yield Request(
                product.strip(),
                callback=self.parse_product
            )

        # products next page
        for next_page in set(hxs.select("//a[@class='next']/@href").extract()):
            yield Request(
                next_page.strip()
            )

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)

        url = response.url
        l = ProductLoader(item=Product(), response=response)

        # name
        name_l = hxs.select("//div[@class='product-page']//h1[@class='page-title nosp']//text()").extract()
        name = ' '.join([x.strip() for x in name_l if x.strip()])
        l.add_value('name', name)

        # price
        price = hxs.select("//meta[@property='og:price:amount']/@content").extract()
        price = extract_price("".join(price))
        l.add_value('price', price)

        # sku
        sku = hxs.select("//div[@class='product-page']//meta[@itemprop='identifier']/@content").extract()
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

        product = l.load_item()
        yield product
