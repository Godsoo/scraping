import csv
import os
import re
import time

from scrapy import log
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc, canonicalize_url

from product_spiders.items import (
    Product,
    ProductLoaderWithNameStrip as ProductLoader
)
from product_spiders.spiders.BeautifulSoup import BeautifulSoup
from keteritems import KeterMeta, Review, ReviewLoader

HERE = os.path.abspath(os.path.dirname(__file__))

brands = [
    'step2',
    'rubbermaid',
    'lifetime',
    'keter',
    'suncast',
    'sterilite'
]

class AmazonSpider(BaseSpider):
    name = 'keter-amazon.co.uk'
    allowed_domains = ['amazon.co.uk']
    # user_agent = 'spd'
    user_agent = 'Mozilla/5.0 (Windows NT 5.1; rv:7.0.1) Gecko/20100101 Firefox/7.0.1'

    def start_requests(self):

        with open(os.path.join(HERE, 'amazonuk_urls.csv')) as f:
            reader = csv.reader(f)
            search_urls = [row[0] for row in reader]
        for url in search_urls:
            for brand in brands:
                yield Request(url=canonicalize_url(url % brand), meta={'brand': brand})

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        soup = BeautifulSoup(response.body)

        next_page = soup.find('a', 'pagnNext')
        if next_page:
            # log.msg(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> TURN TO NEXT PAGE")
            yield Request(
                url=canonicalize_url(urljoin_rfc(base_url, next_page['href'])),
                meta=response.meta
            )

        products = hxs.select("//div/h3/a/@href").extract()
        log.msg(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> GOT %s PRODUCTS " %
                len(products))
        for product in products:
            # log.msg(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> URL %s" % product)
            yield Request(
                url=canonicalize_url(urljoin_rfc(base_url, product)),
                meta=response.meta,
                callback=self.parse_product
            )

        products = soup.findAll('div', id=re.compile(u'^result_.*'))
        log.msg(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> GOT %s PRODUCTS " %
                len(products))
        for product in products:
            parent_expressions = (lambda tag: tag.name == 'h3' and tag.get('class') == 'title',
                                  lambda tag: tag.name == 'div' and tag.get('class') == 'productTitle')
            url = product.find(lambda tag: tag.name == 'a' and any([tag.findParent(parent_expression) for parent_expression in parent_expressions]))
            if url:
                yield Request(
                    url=canonicalize_url(urljoin_rfc(get_base_url(response), url['href'])),
                    meta=response.meta,
                    callback=self.parse_product
                )

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        loader = ProductLoader(item=Product(), selector=hxs)
        soup = BeautifulSoup(response.body)

        log.msg("-"*79)

        loader.add_xpath('name', '//span[@id="btAsinTitle"]/span/text()')
        loader.add_value('url', response.url)
        loader.add_value('brand', response.meta['brand'].strip().lower())
        identifier = hxs.select('//form/input[@name="ASIN"]/@value').extract()[0]
        loader.add_value('identifier', identifier)

        price = soup.find('b', 'priceLarge')
        if not price:
            price = soup.find('span', 'price')
        if not price:
            price = soup.find('span', 'priceLarge')
        try:
            loader.add_value('price', price.text)
        except:
            loader.add_value('price', "")

        sku = hxs.select('//span[@class="tsLabel" and contains(text(), "Part Number")]/../span[2]/text()').extract()
        if not sku:
            sku = hxs.select('//b[contains(text(), "model number")]/../text()').extract()
        if sku:
            loader.add_value('sku', sku[0].strip().lower())

        product_image = hxs.select('//*[@id="main-image" or @id="prodImage"]/@src').extract()
        if not product_image:
            self.log('ERROR: no product Image found!')
        else:
            image = urljoin_rfc(get_base_url(response), product_image[0].strip())
            loader.add_value('image_url', image)

        category = hxs.select('//*[@id="nav-subnav"]/li[1]/a/text()').extract()
        if not category:
            self.log("ERROR: category not found")
        else:
            loader.add_value('category', category[0].strip())

        metadata = KeterMeta()
        metadata['brand'] = response.meta['brand'].strip().lower()
        metadata['reviews'] = []

        product = loader.load_item()
        product['metadata'] = metadata

        is_match = False
        brand = soup.find('h1', 'parseasinTitle').findNextSibling('a')
        if brand:
            brand = brand.text.strip()
            if response.meta['brand'].lower() in brand.lower():
                is_match = True
            log.msg('>>>>>>> %s==%s' %
                        (brand.lower(), response.meta['brand']))

        brand = soup.find('h1', 'parseasinTitle').find('span').text.strip()
        if brand:
            if response.meta['brand'].lower() in brand.lower():
                is_match = True
            log.msg('>>>>>>> %s==%s' %
                        (brand.lower(), response.meta['brand']))

        reviews_url = hxs.select(u'//a[contains(text(),"customer review")]/@href').extract()

        if is_match:
            yield product
            # if reviews_url:
            #     yield Request(
            #         url=canonicalize_url(reviews_url[0]),
            #         meta={'product': product},
            #         callback=self.parse_review
            #     )
            # else:
            #     yield product

    def parse_review(self, response):
        hxs = HtmlXPathSelector(response)
        soup = BeautifulSoup(response.body)
        product = response.meta['product']
        reviews = hxs.select(u'//table[@id="productReviews"]//div[@style="margin-left:0.5em;"]')

        if not reviews:
            yield product
            return

        for review in reviews:
            loader = ReviewLoader(item=Review(), selector=hxs, date_format=u'%d/%m/%Y')
            date = review.select(u'.//nobr/text()')[0].extract()
            res = None
            date_formats = (u'%B %d, %Y', u'%d %b %Y', u'%d %B %Y')
            for format in date_formats:
                try:
                    res = time.strptime(date, format)
                except ValueError:
                    pass
                if res:
                    break
            date = time.strftime(u'%d/%m/%Y', res)
            loader.add_value('date', date)

            rating = review.select(u'.//text()').re(u'([\d\.]+) out of 5 stars')[0]
            rating = int(float(rating))
            loader.add_value('rating', rating)
            loader.add_value('url', response.url)

            title = review.select(u'.//b/text()')[0].extract()
            text = ''.join([s.strip() for s in review.select(u'div[@class="reviewText"]/text()').extract()])
            loader.add_value('full_text', u'%s\n%s' % (title, text))

            product['metadata']['reviews'].append(loader.load_item())

        next_page = soup.find('a', text=re.compile('Next'))
        if next_page and next_page.parent.get('href'):
            yield Request(
                url=next_page.parent['href'],
                meta=response.meta,
                callback=self.parse_review
            )
        else:
            yield product
