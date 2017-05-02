# -*- coding: utf-8 -*-

import urlparse
import os
import csv
import re
import shutil
from product_spiders.spiders.siehunting.generic import GenericReviewSpider
import logging
from scrapy import log
from urllib import quote
from scrapy.http import Request, HtmlResponse
from scrapy.selector import HtmlXPathSelector
from hamiltonitems import Review, ReviewLoader
from product_spiders.items import ProductLoader, Product
from product_spiders.utils import extract_price

from product_spiders.config import DATA_DIR

HERE = os.path.abspath(os.path.dirname(__file__))


def get_reviews_url(product):
    url = product['url']
    productid = url.split('/')[-1].split('.')
    if productid:
        return 'http://walmart.ugc.bazaarvoice.com/1336a/%s/reviews.djs?format=embeddedhtml' % productid[0]
        # return 'http://reviews.walmart.com/1336/%s/reviews.htm' % productId[0]
    return None


def review_rating_extractor(review_box):
    url = review_box.select('.//div[@id="BVRRRatingOverall_Review_Display"]/div[@class="BVRRRatingNormalImage"]//div[@class="BVImgOrSprite"]//img/@alt').extract()
    if url:
        return url[0].split(" ")[0]
    return None


def sku_extractor(product_box):
    sku = ''.join(product_box.select('//tr[td[contains(text(),"Model No.:")]]//text()').extract())
    sku = re.findall('Model No.:(.*)', sku)
    if sku:
        sku = sku[0].strip()
    else:
        sku = ''

    return sku

def ident_extractor(hxs):
    return re.search(r'/(\d+)$', hxs.response.url).group(1)

def xpath_select(hxs, selector):
    if not hxs:
        return []
    parts = selector.replace('//tbody', '/tbody').split('/tbody')
    if len(parts) == 1:
        return hxs.select(selector)
    current = hxs.select(parts[0])
    for s in parts[1:]:
        temp = current.select("./tbody")
        if temp:
            current = temp
        current = current.select("." + s)
    return current


class WalmartSpider(GenericReviewSpider):
    name = "hamiltonbeach-walmart.com"
    allowed_domains = ["walmart.com", "walmart.ugc.bazaarvoice.com"]
    skus = []
    retry_urls = {}
    handle_httpstatus_list = [302, 301]

    rotate_agent = True

    BRAND_GET_PARAM = 'search_query'
    NAVIGATION = ['//h4[@class="tile-heading"]/a/@href', '//a[contains(@class,"paginator-btn")]/@href']

    PRODUCT_BOX = [
        ('.', {'name': '//h1[contains(@class, "product-name")]//text()',
               # 'price': ['//div[@id="WM_PRICE"]//span/text()',
               #           '//div[@class="onlinePriceMP"]//span/text()',
               #           '//div[contains(@class, "camelPrice")]//span/text()',
               #           ],
               'sku': sku_extractor,
               'identifier': ident_extractor,
               'image_url': '//img[contains(@class, "js-product-primary-image")]/@src',
               'category': '//ol[contains(@class, "breadcrumb-list")]//li[last()]//a/span/text()',
               'review_url': get_reviews_url}),
    ]

    PRODUCT_REVIEW_DATE_FORMAT = '%m/%d/%Y'
    PRODUCT_REVIEW_BOX = {'xpath': u'//div[starts-with(@id, "BVRRDisplayContentReviewID_")]', 'full_text': './/div[@class="BVRRReviewTextContainer"]//span[@class="BVRRReviewText"]/text()', 'date': u'.//span[contains(@class,"BVRRReviewDate")]/text()', 'rating': review_rating_extractor, 'next_url': '//a[@name="BV_TrackingTag_Review_Display_NextPage"]/@data-bvjsref'}

    def start_requests(self):
        '''
        For test purposes:
        search_url = 'http://www.walmart.com/search/search-ng.do?tab_value=all&ss=false&search_query=Oster&facet=brand:Oster&search_constraint=0&ic=32_0'
        yield Request(search_url, meta={'brand': 'Oster', 'cookiejar': 1, 'dont_merge_cookies': True})
        '''

        with open(os.path.join(HERE, 'brands.csv')) as f:
            for i, brand in enumerate(f):
                brand_cleaned = quote(brand.strip())
                search_url = 'https://www.walmart.com/search/search-ng.do?tab_value=all&ss=false&search_query=%(brand)s&search_constraint=0&ic=32_0' % {'brand': brand_cleaned}
                yield Request(search_url, meta={'brand': brand.strip(), 'cookiejar': i, 'dont_merge_cookies': True, 'dont_redirect': True})

        if hasattr(self, 'prev_crawl_id'):
            with open(os.path.join(DATA_DIR, '%s_products.csv' % self.prev_crawl_id)) as f:
                reader = csv.DictReader(f)
                i = 0
                for row in reader:
                    i += 1
                    yield Request(row['url'], meta={'brand': row['brand'], 'cookiejar': i, 'dont_merge_cookies': True, 'dont_redirect': True})

    def parse(self, response):
        if response.status == 302:
            url = response.url
            rc = self.retry_urls.get(url, 0)
            rc += 1
            if rc > 100:
                self.log('Redirect retry max count reached, giving up: {}'.format(url))
            else:
                self.log('Redirected, trying again: #{}'.format(rc))
                self.retry_urls[url] = rc
                yield Request(url, dont_filter=True, meta=response.meta)
            return
        if response.status == 301:
            url = response.url.replace('http:', 'https:')
            rc = self.retry_urls.get(url, 0)
            rc += 1
            if rc > 3:
                self.log('Redirect retry max count reached, giving up: {}'.format(url))
            else:
                self.log('Redirected, trying again: #{}'.format(rc))
                self.retry_urls[url] = rc
                yield Request(url, dont_filter=True, meta=response.meta)
            return

        self.visited_urls = set()
        self.product_links = set()
        self.product_names = set()

        for item in self.parse_products(response):
            yield item

    def parse_products(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = self.get_base_url(response)

        for url in self.navigation_links(response, hxs, base_url):
            if url in self.product_links: continue
            if url not in self.visited_urls:
                self.visited_urls.add(url)
                yield Request(url, callback=self.parse_products, meta=dict(**response.meta))

        for item in self.do_parse_products(response, hxs, base_url): 
            yield item

    def do_parse_products(self, response, hxs, base_url):
        hxs = HtmlXPathSelector(response)
        base_url = self.get_base_url(response)
        if not base_url: return

        for item in self.SKIP_PAGE_IF:
            try:
                if callable(item) and item(hxs): 
                    return
                if hxs.select(item): 
                    return
            except: pass

        for xpath, box_spec in self.PRODUCT_BOX:
            product_hxs = xpath_select(hxs, xpath) if xpath and xpath != "." else [hxs]
            found = False
            for product_box in product_hxs:
                found = True
                product_name = xpath_select(product_box, box_spec['name']).extract() if not callable(box_spec['name']) else [box_spec['name'](product_box)]

                if not any(product_name): continue

                product_link = xpath_select(product_box, box_spec['url']) if box_spec.get('url') else None
                name = " ".join([n.strip(' \r\n\t') for n in product_name if n.strip(' \r\n\t')])
                url = urlparse.urljoin(base_url, product_link.extract()[0]) if product_link else response.url

                if url in self.product_links: continue

                product = Product()

                product['name'] = name
                product['url'] = url

                # price
                #price_specs = box_spec.get('price', []) if hasattr(box_spec.get('price', []), 'append') else [box_spec['price']]
                #price = None
                #for price_xpath in price_specs:
                    #product_price = xpath_select(product_box, price_xpath).extract() if not callable(price_xpath) else [price_xpath(hxs, name)]
                    #if any(product_price):
                        #price_text = "".join([e.strip() for e in product_price if e])
                        #match = self.PRICE_RE.findall(price_text.strip().replace(self.THOUSAND_SEP, "").replace(self.DECIMAL_SEP, "."))
                        #if match:
                            #price = match[0]
                            #break

                #price = extract_price(''.join(hxs.select('//div[@itemprop="price"]//text()').extract()))

                product['price'] = None

                # shipping cost
                #shipping_cost_specs = box_spec.get('shipping_cost', []) if hasattr(box_spec.get('shipping_cost', []), 'append') else [box_spec['shipping_cost']]
                #shipping_cost = None
                #for sc_xpath in shipping_cost_specs:
                    #product_sc = xpath_select(product_box, sc_xpath).extract() if not callable(sc_xpath) else [sc_xpath(hxs, name)]
                    #if any(product_sc):
                        #sc_text = "".join([e.strip() for e in product_sc if e])
                        #match = self.PRICE_RE.findall(sc_text.strip().replace(self.THOUSAND_SEP, "").replace(self.DECIMAL_SEP, "."))
                        #if match:
                            #shipping_cost = match[0]
                            #break

                #product['shipping_cost'] = Decimal(shipping_cost) if shipping_cost is not None else ''

                # identifier
                product_identifier = [] if not box_spec.get('identifier') else xpath_select(product_box, box_spec['identifier']).extract() if not callable(box_spec['identifier']) else [box_spec['identifier'](product_box)]
                if any(product_identifier):
                    product['identifier'] = "".join([e.strip() for e in product_identifier])

                # sku
                product_sku = [] if not box_spec.get('sku') else xpath_select(product_box, box_spec['sku']).extract() if not callable(box_spec['sku']) else [box_spec['sku'](product_box)]
                if any(product_sku):
                    product['sku'] = "".join([e.strip() for e in product_sku])

                # category
                product_category = [] if not box_spec.get('category') else xpath_select(product_box, box_spec['category']).extract() if not callable(box_spec['category']) else [box_spec['category'](product_box)]
                if any(product_category):
                    product['category'] = "".join([e.strip() for e in product_category])

                # brand
                product_category = [] if not box_spec.get('brand') else xpath_select(product_box, box_spec['brand']).extract() if not callable(box_spec['brand']) else [box_spec['brand'](product_box)]
                if any(product_category):
                    product['brand'] = "".join([e.strip() for e in product_category])

                # image url
                image_url = [] if not 'image_url' in box_spec else xpath_select(product_box, box_spec['image_url']).extract() if not callable(box_spec['image_url']) else [box_spec['image_url'](product_box)]
                if any(image_url):
                    for item in image_url:
                        if item:
                            product['image_url'] = urlparse.urljoin(base_url, item.strip())
                            break

                #
                if response.meta.get('product') and response.meta['product']['name'] == product_name:
                    product, data = response.meta.get('product'), product
                    if not product.get('price'): product['price'] = data.get('price')
                    if not product.get('sku'): product['sku'] = data.get('sku')
                #
                product = self.parse_product_ext(response, hxs, product)
                if self.keep_product(response, product_box, product):
                    #log.msg("Crawled %s -> %s" % (name, str(product)))
                    product_page = product['url'] == response.url
                    if not product_page and self.visit_product_page(response, product):
                        response.meta.update({'product': product})
                        yield Request(url=product['url'], callback=self.parse_products, meta=dict(**response.meta))
                    else:
                        self.product_links.add(product['url'])
                        self.product_names.add(product['name'])
                        items = self.after_product_parse(response, product_box, product, box_spec) or []
                        for item in items: 
                            yield item
                        #
            if found and self.PRODUCT_BOX_XOR: 
                break

        
    def parse_product_reviews(self, response):
        log.msg('Extract reviews')
        for line in response.body.split('\n'):
            if line.startswith('var materials='):
                body = line.lstrip('var materials=').rstrip(',')
                break

        try:
            body = eval(body)
        except:
            logging.error('Failed to parse: ' + repr(response.body))
            body = ''
        # Emulate "normal" HTML response
        if body:
            body = ('<html><body>' +
                    '%s' +
                    '</body></html>') % (body['BVRRSourceID'].replace('\\/', '/'))

        response2 = HtmlResponse(url=response.url, body=body)
        response2.request = response.request

        hxs = HtmlXPathSelector(response2) if body else None
        base_url = self.get_base_url(response)
        product = response.meta['product']
        product['metadata'].setdefault('reviews', [])

        box_spec = self.PRODUCT_REVIEW_BOX or {}

        review_hxs = xpath_select(hxs, box_spec.get('xpath')) if 'xpath' in box_spec and box_spec.get('xpath') != "." else hxs
        for review_box in review_hxs:
            loader = ReviewLoader(item=Review(), selector=hxs, date_format=self.PRODUCT_REVIEW_DATE_FORMAT)
            # loader.add_value('url', urlparse.urljoin(base_url, response.url))
            loader.add_value('url', product['url'])
            # review full text
            full_text_specs = box_spec.get('full_text', []) if hasattr(box_spec.get('full_text', []), 'append') else [box_spec['full_text']]
            full_text_parts = []
            for xpath in full_text_specs:
                items = xpath_select(review_box, xpath).extract() if not callable(xpath) else [xpath(hxs)]
                if any(items):
                    item_text = self.REVIEW_TEXT_JOIN.join([e.replace(u'\xa0', u' ').strip(self.REVIEW_TEXT_STRIP) for e in items])
                    full_text_parts.append(item_text)

            review_text = self.REVIEW_PARAGRAPH_JOIN.join(full_text_parts)
            loader.add_value('full_text', review_text)

            if box_spec.get('date'):
                date = review_box.select(box_spec.get('date')).extract() if not callable(box_spec.get('date')) else [box_spec['date'](review_box)]
                loader.add_value('date', date[0] if date else None)

            if box_spec.get('rating'):
                rating_text = review_box.select(box_spec.get('rating')).extract() if not callable(box_spec.get('rating')) else [box_spec['rating'](review_box)]
                loader.add_value('rating', rating_text[0] if rating_text else None)

            review = loader.load_item()
            if review.get('full_text') or review.get('date'):
                for k in review:
                    if type(review[k]) in [str, unicode]:
                        review[k] = review[k].strip().replace('\r\n', '').replace('\n', '')
                    
                product['metadata']['reviews'].append(review)

        next_page = xpath_select(hxs, box_spec.get('next_url')).extract() if (box_spec.get('next_url') and not callable(box_spec['next_url'])) else [box_spec['next_url'](response, hxs)] if callable(box_spec.get('next_url')) else None
        next_page_url = urlparse.urljoin(base_url, next_page[0]) if any(next_page) else None

        if not next_page_url or next_page_url in self.visited_urls or not review_hxs:
            yield product
        else:
            self.visited_urls.add(next_page_url)
            if 'javascript://' in next_page_url:
                yield product
            else:
                yield Request(url=next_page_url, meta=dict(**response.meta), callback=self.parse_product_reviews)

    def visit_product_page(self, response, product):
        return True  # visit product page to have access to sku

    def after_product_parse(self, response, product_box, product, product_box_spec):
        base_url = self.get_base_url(response)
        response.meta.update({'product': product})

        product['brand'] = response.meta.get('brand')

        review_urls = product_box_spec.get('review_url', []) if hasattr(product_box_spec.get('review_url', []), 'append') else [product_box_spec['review_url']] if callable(product_box_spec.get('review_url')) else [product_box_spec['review_url']]

        if not any(review_urls):
            yield self.clean_product(product)

        reviews_available = []
        for xpath in review_urls:
            if xpath == '.' or not xpath:
                # reviews are available in the product page

                for item in self.parse_product_reviews(response):
                    yield item
                reviews_available.append(True)
            else:
                review_url = xpath_select(product_box, xpath).extract() if not callable(xpath) else [xpath(product)]
                if review_url:
                    url = urlparse.urljoin(base_url, review_url[0])
                    if not url in self.visited_urls:
                        self.visited_urls.add(url)
                        yield Request(url=url, callback=self.parse_product_reviews, meta=dict(**response.meta))
                    reviews_available.append(True)
                else:
                    reviews_available.append(False)

        if not any(reviews_available):
            yield product
