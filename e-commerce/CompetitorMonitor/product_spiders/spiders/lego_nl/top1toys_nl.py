import re
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

from product_spiders.utils import extract_price
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

from product_spiders.spiders.BeautifulSoup import BeautifulSoup


class Top1ToysSpider(BaseSpider):
    name = 'top1toys.nl'
    allowed_domains = ['top1toys.nl']
    start_urls = ['http://www.top1toys.nl/?page=merk_5647']

    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        for product in hxs.select('//div[@id="main"]//a[not(contains(@href, "/speelgoed/lego/?nr="))]/img/../@href').extract():
            '''
            if 'window.location' in product:
                product = re.search('\'(.+)\'', product).groups()[0]
            '''
            yield Request(urljoin_rfc(get_base_url(response), product), callback=self.parse_product)

        for page in hxs.select('//a[contains(@href, "/speelgoed/lego/?nr=")]/@href').extract():
            yield Request(urljoin_rfc(get_base_url(response), page), callback=self.parse)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        loader = ProductLoader(item=Product(), response=response)

        # XPath does not work for some reason
        soup = BeautifulSoup(response.body)

        try:
            name = soup.find(attrs={'itemprop': 'name'}).text
        except:
            return

        loader.add_value('identifier', soup.find('div', {'class': 'clearfix'}).find('a')['title'])
        loader.add_value('url', response.url)
        loader.add_value('name', name)
        loader.add_value('price', extract_price(soup.find(attrs={'itemprop': 'price'}).text.replace('.', '').replace(',', '.')))

        try:
            loader.add_value('sku', re.search('(\d{4}\d*)', name).groups()[0])
        except:
            self.log('Product without SKU: %s' % (response.url))
        loader.add_value('category', 'Lego')

        img = soup.find(attrs={'itemprop': 'image'}).find('img')
        if img:
            loader.add_value('image_url', urljoin_rfc(get_base_url(response), img['src']))

        loader.add_value('brand', 'lego')
        loader.add_value('shipping_cost', '1.99')
#        loader.add_xpath('stock', '1')

        yield loader.load_item()
