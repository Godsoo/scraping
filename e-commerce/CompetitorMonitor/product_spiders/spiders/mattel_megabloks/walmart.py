import os
import datetime

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.url import add_or_replace_parameter

from product_spiders.items import (
    Product,
    ProductLoaderWithNameStrip as ProductLoader
)
from hamiltonitems import HamiltonMeta, ReviewLoader, Review
from urlparse import urljoin
from product_spiders.utils import extract_price
from urllib import quote

HERE = os.path.abspath(os.path.dirname(__file__))


class WalmartSpider(BaseSpider):
    name = 'mattelmegabloks-walmart.com'
    allowed_domains = ['walmart.com', 'bazaarvoice.com']
    start_urls = ('http://www.walmart.com',)
    user_agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.11; rv:49.0) Gecko/20100101 Firefox/49.0'
    keys = [
        ('Mattel', 'Mattel'),
        ('Barbie', 'Mattel'),
        ('Hot Wheels', 'Mattel'),
        ('Monster High', 'Mattel'),
        ('WWE', 'Mattel'),
        ('Disney princess', 'Mattel'),
        ('Max Steel', 'Mattel'),
        ('Ever After High', 'Mattel'),
        ('Matchbox', 'Mattel'),
        ('Little Mommy', 'Mattel'),
        ('Cars', 'Mattel'),
        ('Polly Pocket', 'Mattel'),
        ('DC Universe', 'Mattel'),
        ('Sofia the First', 'Mattel'),
        ('Planes', 'Mattel'),
        ('Frozen', 'Mattel'),
        ('Toy Story', 'Mattel'),
        ('Fijit Friends', 'Mattel'),
        ('Mega Bloks', 'Mega Bloks'),
        ("Assassin's Creed", 'Mega Bloks'),
        ('Call of Duty', 'Mega Bloks'),
        ('Cat', 'Mega Bloks'),
        (u'Create \u2018n Play', 'Mega Bloks'),
        ("Create 'n Play Junior", 'Mega Bloks'),
        ('Dora the Explorer', 'Mega Bloks'),
        ('First Builders', 'Mega Bloks'),
        ('Halo', 'Mega Bloks'),
        ('Hello Kitty', 'Mega Bloks'),
        ('Jeep', 'Mega Bloks'),
        ('John Deere', 'Mega Bloks'),
        ('Junior Builders', 'Mega Bloks'),
        ('Kapow', 'Mega Bloks'),
        ('Mega Play', 'Mega Bloks'),
        ('power rangers', 'Mega Bloks'),
        ('Ride-ons', 'Mega Bloks'),
        ('Ride ons', 'Mega Bloks'),
        ('Skylanders', 'Mega Bloks'),
        ('spongebob squarepants', 'Mega Bloks'),
        ('thomas and friends', 'Mega Bloks'),
        ('world builders', 'Mega Bloks'),
    ]

    def parse(self, response):
        for key, brand in self.keys:
            self.log('Searching ' + key)

            try:
                yield Request('http://www.walmart.com/search/?query=' + quote(key), meta={'brand':brand}, callback=self.parse_list)
            except:
                pass

    def parse_list(self, response):
        hxs = HtmlXPathSelector(response)

        category = ''
        tmp = response.xpath('//div[@id="sidebar-container"]/div[contains(@class,"departments")]/div[1]//h4[1]/a/text()').extract()
        if not tmp:
            tmp = response.xpath('//p[@class="heading-d"]/a/text()').extract()
        if tmp:
            category = tmp[0]
        for link in response.xpath('//div[@id="tile-container"]//a/@href').extract():  # ##
            url = urljoin(response.url, link)
            meta = response.meta
            meta['category'] = category
            yield Request(url, meta=meta, callback=self.parse_product)

        tmp = response.xpath('//div[@class="paginator"]/a[contains(@class,"paginator-btn-next")]/@href').extract()
        if tmp:
            url = urljoin(response.url, tmp[0])
            yield Request(url, meta=response.meta, callback=self.parse_list)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)

        loader = ProductLoader(item=Product(), response=response)

        product_id = response.xpath('//form[@name="SelectProductForm"]/input[@name="product_id"]/@value').extract()
        if product_id:
            identifier = product_id[0]
        else:
            identifier = response.url.split('/')[-1]

        loader.add_value('identifier', identifier.split('?')[0])

        name = filter(lambda n: n, map(unicode.strip, response.xpath('//h1[@itemprop="name"]//text()').extract()))
        if not name:
            name = filter(lambda n: n, map(unicode.strip, response.xpath('//h1[contains(@class,"product-name")]//text()').extract()))
        if name:
            loader.add_value('name', name[0].strip())

        loader.add_value('brand', response.meta['brand'])

        categories = response.xpath('//div[@itemprop="breadcrumb"]//span[@itemprop="title"]/text()').extract()
        if not categories:
            categories = response.xpath('//div[@itemprop="breadcrumb"]//span[@itemprop="name"]/text()').extract()
        if categories:
            loader.add_value('category', categories[0])
        elif 'category' in response.meta:
            loader.add_value('category', response.meta['category'])

        sku = response.xpath('//table[@class="SpecTable"]//td[text()="Model No.:"]/following-sibling::td/text()').extract()
        if not sku:
            sku = response.xpath('//div[@class="specs-table"]//td[text()="Model No.:"]/following-sibling::td/text()').extract()
        if not sku:
            sku = response.xpath('//div[contains(@class, "specs-table")]//td[text()="Model No.:"]/following-sibling::td/text()').extract()
        if sku:
            loader.add_value('sku', sku[0].strip())
        loader.add_value('url', response.url)

        price = response.xpath('//div[@id="WM_PRICE"]//*[contains(@class,"camelPrice")]/span/text()').extract()
        if not price:
            price = response.xpath('//div[@class="onlinePriceMP"]//*[contains(@class,"camelPrice")]/span/text()').extract()
        if not price:
            price = response.xpath('//div[@itemprop="offers"]/div[contains(@class, "product-price")]//*[@itemprop="price"][1]//text()').extract()
        if not price:
            price = response.xpath('//div[@class="col5"]//div[contains(@class,"product-buying-table-row")][1]//div[contains(@class,"price-display")][1]//text()').extract()
        if not price:
            price = response.xpath('//*[@itemprop="price"]//text()').extract()
        if not price:
            price = response.xpath('//@data-product-price').extract_first()
            price = [price] if price else []

        price = ''.join(price).strip() if price else '0'

        price = extract_price(price)
        loader.add_value('price', price)

        out_stock = response.xpath('//div[@id="OnlineStat" and @class="OutOfStock"]')
        if not out_stock:
            out_stock = response.xpath('//p[@class="price-oos" and text()="Out of stock"]')
        if not out_stock:
            out_stock = response.xpath('//div[@id="OnlineStat" and @class="OnlineNotSold"]')
        if out_stock:
            loader.add_value('stock', 0)
        else:
            loader.add_value('stock', 1)

        image = response.xpath('//div[@class="LargeItemPhoto215"]//img/@src').extract()
        if not image:
            image = response.xpath('//div[contains(@class,"product-images")][1]//img/@src').extract()
        if image:
            loader.add_value('image_url', image[0])

        product = loader.load_item()
        metadata = HamiltonMeta()
        metadata['brand'] = product['brand'].strip().lower()
        metadata['reviews'] = []
        product['metadata'] = metadata

        if True:
            productid = response.url.split('/')[-1].split('.')
            url = 'https://www.walmart.com/reviews/product/%s?page=1' % productid[0]
            yield Request(url, meta={'product': product, 'page': 1, 'productid':productid[0]}, callback=self.parse_reviews)
        else:
            yield product

    def parse_reviews(self, response):
        hxs = HtmlXPathSelector(response)

        product = response.meta['product']
        productid = response.meta['productid']

        reviews = response.xpath(u'//div[@class="js-review-list"]/div[contains(@class, "customer-review")]')

        for review in reviews:
            review_loader = ReviewLoader(item=Review(), response=response, date_format="%B %d, %Y")
            tmp = review.select('.//span[contains(@class, "customer-review-date")]/text()').extract()
            if tmp:
                review_date = datetime.datetime.strptime(tmp[0], '%m/%d/%Y')
                review_loader.add_value('date', review_date.strftime("%B %d, %Y"))

            review_text = ''

            title = review.select('.//div[contains(@class, "customer-review-title")]/text()').extract()
            if title:
                review_text += title[0].strip() + ' #&#&#&# '

            review_text += ''.join(review.select('.//div[@class="customer-review-text"]//text()').extract()).strip(" \r\n")
            review_text += ' #&#&#&# ' + ' '.join(filter(lambda s: s, map(unicode.strip, review.select('.//div[contains(@class, "customer-info")]//text()').extract()))).strip()
            review_loader.add_value('full_text', review_text)
            review_loader.add_value('url', response.url)

            rating_text = review.select('.//div[contains(@class, "customer-stars")]/span[contains(@class, "visuallyhidden")]/text()').re(r'(\d+)')
            review_loader.add_value('rating', rating_text[0] if rating_text else None)

            product['metadata']['reviews'].append(review_loader.load_item())

        page = response.meta['page'] + 1
        review_pages = response.xpath('//a[contains(@class, "js-pagination")]/@data-page').extract()

        if not reviews or str(page) not in review_pages:
            yield product
        else:
            url = add_or_replace_parameter(response.url, 'page', str(page))
            request = Request(url, meta={'product': product, 'page': page, 'productid': productid}, callback=self.parse_reviews)
            yield request
