# -*- coding: utf-8 -*-
from decimal import Decimal

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.utils.response import get_base_url
from scrapy.http import Request

from scrapy import log

from product_spiders.items import ProductLoader, Product

import urlparse
import re
from product_spiders.spiders.keter.keteritems import KeterMeta, ReviewLoader, Review

__author__ = 'Theophile R. <rotoudjimaye.theo@gmail.com>'

def xpath_select(hxs, selector):
    if not hxs: return []
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


class GenericSpider(BaseSpider):
    NAVIGATION = []
    PRODUCT_BOX = []

    PRICE_RE = re.compile("\d+\.?\d*")

    THOUSAND_SEP = ","
    DECIMAL_SEP = "."
    PRODUCT_URL_EXCLUDE = ()
    NAV_URL_EXCLUDE = ()


    PRODUCT_BOX_XOR = False
    CHECK_PRODUCT_NAME = True
    CHECK_PRICE_IN_PRODUCT_PAGE = False

    SKIP_PAGE_IF = ()

    SPECIFIC_PRODUCTS = []

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        self.visited_urls = set()
        self.product_links = set()
        self.product_names = set()

        for item in self.parse_products(response):
            yield item

    def get_base_url(self, response):
        try:
            return get_base_url(response)
        except: return

    def preprocess_link(self, base_url, href):
        return href

    def skip_navigation(self, url):
        for item in self.NAV_URL_EXCLUDE:
            if item in url:
                return True
        return False

    def _strip_fragment(self, url):
        return url.split("#")[0] if url else url

    def navigation_links(self, response, hxs, base_url):
        links = set()
        for xpath in self.NAVIGATION:
            for href in xpath_select(hxs, xpath).extract():
                url = self._strip_fragment(urlparse.urljoin(base_url, self.preprocess_link(base_url, href)))
                if url not in self.visited_urls and not self.skip_navigation(url):
                    links.add(url)
        else:
            # log.msg("No navigation xpath specification for this spider", level=log.WARNING)
            pass
        return links

    def parse_products(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = self.get_base_url(response)

        for url in self.navigation_links(response, hxs, base_url):
            if url in self.product_links: continue
            if url not in self.visited_urls:
                self.visited_urls.add(url)
                yield Request(url, callback=self.parse_products, meta=dict(**response.meta))

        for item in self.do_parse_products(response, hxs, base_url): yield item

    def do_parse_products(self, response, hxs, base_url):
        hxs = HtmlXPathSelector(response)
        base_url = self.get_base_url(response)
        if not base_url: return

        for item in self.SKIP_PAGE_IF:
            try:
                if callable(item) and item(hxs): return
                if hxs.select(item): return
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
                price_specs = box_spec.get('price', []) if hasattr(box_spec.get('price', []), 'append') else [box_spec['price']]
                price = None
                for price_xpath in price_specs:
                    product_price = xpath_select(product_box, price_xpath).extract() if not callable(price_xpath) else [price_xpath(hxs, name)]
                    if any(product_price):
                        price_text = "".join([e.strip() for e in product_price if e])
                        match = self.PRICE_RE.findall(price_text.strip().replace(self.THOUSAND_SEP, "").replace(self.DECIMAL_SEP, "."))
                        if match:
                            price = match[0]
                            break

                product['price'] = Decimal(price) if price is not None else ''

                # shipping cost
                shipping_cost_specs = box_spec.get('shipping_cost', []) if hasattr(box_spec.get('shipping_cost', []), 'append') else [box_spec['shipping_cost']]
                shipping_cost = None
                for sc_xpath in shipping_cost_specs:
                    product_sc = xpath_select(product_box, sc_xpath).extract() if not callable(sc_xpath) else [sc_xpath(hxs, name)]
                    if any(product_sc):
                        sc_text = "".join([e.strip() for e in product_sc if e])
                        match = self.PRICE_RE.findall(sc_text.strip().replace(self.THOUSAND_SEP, "").replace(self.DECIMAL_SEP, "."))
                        if match:
                            shipping_cost = match[0]
                            break

                product['shipping_cost'] = Decimal(shipping_cost) if shipping_cost is not None else ''

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
                    log.msg("Crawled %s -> %s" % (name, str(product)))
                    product_page = product['url'] == response.url
                    if not product_page and self.visit_product_page(response, product):
                        response.meta.update({'product': product})
                        yield Request(url=product['url'], callback=self.parse_products, meta=dict(**response.meta))
                    else:
                        self.product_links.add(product['url'])
                        self.product_names.add(product['name'])
                        items = self.after_product_parse(response, product_box, product, box_spec) or []
                        for item in items: yield item
                        #
            if found and self.PRODUCT_BOX_XOR: break

    def parse_product_ext(self, response, hxs, product):
        product_page = product['url'] == response.url
        return product

    def keep_product(self, response, product_box, product):
        for item in self.PRODUCT_URL_EXCLUDE:
            if item in product['url']:
                return False
        if self.CHECK_PRODUCT_NAME:
            if product['name'] in self.product_names:
                return False
        return True

    def visit_product_page(self, response, product):
        return not product['price'] and self.CHECK_PRICE_IN_PRODUCT_PAGE

    def after_product_parse(self, response, product_box, product, product_box_spec):
        yield self.clean_product(product)

    def clean_product(self, product):
        if not 'price' in product or \
            not product['price'] or product['price'] == u'None':
            product['price'] = ''
        return product


class GenericReviewSpider(GenericSpider):
    """"""
    BRAND_GET_PARAM = None
    PRODUCT_REVIEW_BOX = None
    PRODUCT_REVIEW_DATE_FORMAT = '%d/%m/%Y'

    CHECK_PRODUCT_BRAND_IN_NAME = False
    PRODUCT_BOX_XOR = True

    def start_requests(self):
        reqs = []
        if self.BRAND_GET_PARAM:
            for url in self.start_urls:
                parsed = urlparse.urlparse(url)
                params = urlparse.parse_qs(parsed.query)
                brand = params.get(self.BRAND_GET_PARAM) if not callable(self.BRAND_GET_PARAM) else [self.BRAND_GET_PARAM()]
                reqs.append(Request(url, meta={'product_brand': brand[0] if brand else None}))

        if self.SPECIFIC_PRODUCTS:
            for products in self.SPECIFIC_PRODUCTS:
                brand = products.get('brand', '')
                for url in products.get('urls', ''):
                    reqs.append(Request(url, meta={'product_brand': brand}))

        if reqs:
            return reqs
        
        else:
            return BaseSpider.start_requests(self)

    def parse_product_ext(self, response, hxs, product):
        product_page = product['url'] == response.url

        if 'metadata' not in product:
            product['metadata'] = KeterMeta()
            product['metadata']['brand'] = None

        if self.BRAND_GET_PARAM and product['metadata']['brand'] is None:
            brand = response.meta.get('product_brand')
            if brand:
                product['metadata']['brand'] = brand
                if not product.get('brand'):
                    product['brand'] = brand

        return product

    def keep_product(self, response, product_box, product):
        if not GenericSpider.keep_product(self, response, product_box, product):
            return False
        brand = response.meta.get('product_brand')
        if not self.CHECK_PRODUCT_BRAND_IN_NAME or not brand: return True
        return  brand.lower() in product['name'].lower() if not callable(self.CHECK_PRODUCT_BRAND_IN_NAME) else self.CHECK_PRODUCT_BRAND_IN_NAME(response, product_box, product, brand)

    def after_product_parse(self, response, product_box, product, product_box_spec):
        base_url = self.get_base_url(response)
        response.meta.update({'product': product})

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
            yield self.clean_product(product)

        #
    REVIEW_TEXT_STRIP = '" \r\n"'
    REVIEW_TEXT_JOIN = " "
    REVIEW_PARAGRAPH_JOIN = ". "
    def parse_product_reviews(self, response):
        hxs = HtmlXPathSelector(response) if response.body else None
        base_url = self.get_base_url(response)
        product = response.meta['product']
        product['metadata'].setdefault('reviews', [])

        box_spec = self.PRODUCT_REVIEW_BOX or {}

        review_hxs = xpath_select(hxs, box_spec.get('xpath')) if 'xpath' in box_spec and box_spec.get('xpath') != "." else hxs

        for review_box in review_hxs:
            loader = ReviewLoader(item=Review(), selector=hxs, date_format=self.PRODUCT_REVIEW_DATE_FORMAT)
            loader.add_value('url', urlparse.urljoin(base_url, response.url))
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
                product['metadata']['reviews'].append(review)

        next_page = xpath_select(hxs, box_spec.get('next_url')).extract() if (box_spec.get('next_url') and not callable(box_spec['next_url'])) else [box_spec['next_url'](response, hxs)] if callable(box_spec.get('next_url')) else None
        next_page_url = urlparse.urljoin(base_url, next_page[0]) if any(next_page) else None

        if not next_page_url or next_page_url in self.visited_urls or not review_hxs:
            yield self.clean_product(product)
        else:
            self.visited_urls.add(next_page_url)
            yield Request(url=next_page_url, meta=dict(**response.meta), callback=self.parse_product_reviews)
