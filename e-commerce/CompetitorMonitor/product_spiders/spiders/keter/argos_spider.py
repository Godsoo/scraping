import re
from datetime import datetime
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc
from product_spiders.items import Product, ProductLoader
from keteritems import KeterMeta, Review, ReviewLoader

from scrapy import log


class ArgosCoUKKeterSpider(BaseSpider):
    name = 'argos.co.uk_keter'
    allowed_domains = ['argos.co.uk', 'argos.ugc.bazaarvoice.com']
    start_urls = ('http://www.argos.co.uk',)

    search_url = 'http://www.argos.co.uk/static/Search/searchTerms/'

    products = ['Keter',
                'Suncast',
                'Rubbermaid',
                'Lifetime',
                'Step+2',
                'Sterilite']

    cats = ['kitchen',
            'garden',
            'furniture',
            'diy']

    def start_requests(self):
        for keyword in self.products:
            url = self.search_url + keyword + '.htm'
            request = Request(url, callback=self.parse_search)
            request.meta['brand'] = keyword.replace('+', ' ')
            yield request

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)

        url = response.url
        brand = response.meta.get('brand', '')
        l = ProductLoader(item=Product(), response=response)

        name = hxs.select("//div[@id='pdpProduct']/h1/text()").extract()
        if not name:
            self.log("ERROR! NO NAME! %s" % url)
            log.msg('ERROR! NO NAME!')
            return
        name = name[0].strip()

        if brand.lower() == 'lifetime' and name.lower().find('lifetime') == -1:
            return

        price = hxs.select("//div[@id='pdpPricing']/span[@class='actualprice']/span/text()").extract()
        if not price:
            self.log("ERROR! NO PRICE! %s %s" % (url, name))
            return
        price = "".join(price)

        sku = hxs.select("//span[@class='identifier']/span[contains(@class, 'partnumber')]/text()").extract()
        if not sku:
            self.log("ERROR! SKU! %s %s" % (url, name))
            # return
        else:
            l.add_value('sku', sku[0])

        category = ''
        s = hxs.select("//script[contains(text(),'EFFECTIVE_URL')]/text()").extract()
        if s:
            s = s[0].strip()
            pos = s.find('category_root')
            if pos != -1:
                s = s[pos:].split('|')
                if len(s) > 1:
                    category = s[1].replace('+', ' ')
                    l.add_value('category', category)
        if category == '':
            self.log("ERROR! NO Category found! %s %s" % (url, name))

        product_image = hxs.select('//*[@id="mainimage"]/@src').extract()
        if not product_image:
            self.log('ERROR: no product Image found!')
        else:
            image = urljoin_rfc(get_base_url(response), product_image[0].strip())
            l.add_value('image_url', image)

        l.add_value('name', name)
        l.add_value('url', url)
        l.add_value('price', price)
        l.add_value('brand', brand.strip().lower())
        l.add_xpath('identifier', u'//form/input[@name="productId"]/@value')
        product = l.load_item()
        metadata = KeterMeta()
        metadata['brand'] = brand.strip().lower()

        metadata['reviews'] = []
        product['metadata'] = metadata

        reviews_url = 'http://argos.ugc.bazaarvoice.com/1493-en_gb/%s/reviews.djs?format=embeddedhtml'
        # part_number = hxs.select(u'//form/input[@name="partNumber"]/@value').extract()[0]
        part_number = re.search(r'/partNumber/(\d+)', response.url).group(1)
        yield Request(reviews_url % part_number, callback=self.parse_review_page, meta={'product': product})

    def parse_review_page(self, response):
        item_ = response.meta.get('product', '')
        hxs = HtmlXPathSelector(text=self._extract_html(response))
        reviews = hxs.select('//div[@class="BVRRReviewDisplayStyle5"]')
        for review in reviews:
            l = ReviewLoader(item=Review(), response=response, date_format='%m/%d/%Y')
            rating = review.select(".//span[contains(@class,'BVRRRatingNumber')]/text()").extract()[0]
            date = review.select(".//span[contains(@class,'BVRRValue BVRRReviewDate')]/text()").extract()[0]
            review = review.select(".//span[contains(@class,'BVRRReviewText')]/text()")[1].extract()

            l.add_value('rating', rating)
            l.add_value('url', response.url)
            l.add_value('date', datetime.strptime(date, '%d %B %Y').strftime('%m/%d/%Y'))
            l.add_value('full_text', review)
            item_['metadata']['reviews'].append(l.load_item())

        next = hxs.select('//span[@class="BVRRPageLink BVRRNextPage"]/a/@data-bvjsref').extract()
        if next:
            yield Request(next[0], callback=self.parse_review_page, meta={'product': item_})
        else:
            yield item_

    def parse_search(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        brand = response.meta.get('brand', '')

        # parse pages
        pages = hxs.select("//div[contains(@class, 'pagination')]//a[@class='button']/@href").extract()
        for page in pages:
            request = Request(page, callback=self.parse_search)
            request.meta['brand'] = brand
            yield request

        # parse products
        items = hxs.select("//div[@id='products']/ul/li[contains(@class, 'item')]/dl")
        for item in items:
            url = item.select('dt[@class="title"]/a/@href').extract()
            if not url:
                self.log("ERROR! NO URL! URL: %s." % (response.url,))
                continue
            url = urljoin_rfc(base_url, url[0])

            request = Request(url, callback=self.parse_product)
            request.meta['brand'] = brand
            yield request

    def _extract_html(self, response):
        review_html = ''
        for line in response.body.split('\n'):
            if 'var materials=' in line:
                review_html = line.split('"BVRRSecondaryRatingSummarySourceID":" ')[-1].split('\n}')[0].replace('\\', '')
        return review_html
