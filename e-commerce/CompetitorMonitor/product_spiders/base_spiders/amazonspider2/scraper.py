# -*- coding: utf-8 -*-
import string
import json
import logging
import re
import urllib
from urlparse import urljoin, parse_qs, parse_qsl, urlparse, urlunparse, ParseResult

from scrapy import log
from scrapy.selector import HtmlXPathSelector
from scrapy.utils.response import get_base_url
from scrapy.utils.url import url_query_parameter, add_or_replace_parameter, url_query_cleaner
from scrapy.http.response.html import HtmlResponse

from product_spiders.utils import extract_price2uk, fix_json

from product_spiders.base_spiders.amazonspider2.utils import parse_review_date_locales


class AmazonScraperException(Exception):
    pass

class AmazonScraperProductDetailsException(Exception):
    pass

class AmazonScraper(object):
    def log(self, message, level=logging.INFO):
        log.msg(message, level)

    def antibot_protection_raised(self, text):
        """
        Checks if Amazon suspects our spider as a bot, consider using proxy/tor if so
        """

        if u'Sorry, we just need to make sure' in text:
            if u're not a robot' in text:
                return True
        if u"Désolés, il faut que nous nous assurions que vous n'êtes pas un robot" in text:
            return True
        if u"Geben Sie die Zeichen unten ein" in text:
            return True
        if u"Inserisci i caratteri visualizzati nello spazio sottostante" in text:
            return True

        # general solution
        hxs = HtmlXPathSelector(text=text)
        if hxs.select("//input[@id='captchacharacters']").extract():
            return True

        return False

    def _check_if_unavailable(self, stock_container):
        unavailable_texts = [
            u'Currently unavailable',
            u'Actuellement indisponible',
            u'Derzeit nicht verfügbar',
            u'No disponible temporalmente',
            u'out of stock',
        ]
        for t in unavailable_texts:
            if stock_container.select(u'.//*[contains(text(), "%s")]' % t):
                return True
        return False

    def _extract_price(self, source_url, price):
        if "-" in price:
            low, high = map(extract_price2uk, price.split("-"))
            return low, high
        else:
            return extract_price2uk(price)

    def _process_search_results(self, response, results, amazon_direct=False):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        products = []

        preloaded_images = hxs.select('//div[@id="results-atf-images-preload"]/img/@src').extract()
        preloaded_images.reverse()

        for result in results:
            # Skip "See all ... results"
            if result.select(".//a[contains(text(), 'See all')][contains(text(), 'results')]"):
                self.log('[AMAZON SCRAPER] "See all" found on page: %s' % (response.url, ))
                continue
            # french: "Voir les ... résultats"
            if result.select(u".//a[contains(text(), 'Voir les')][contains(text(), 'résultats')]"):
                self.log('[AMAZON SCRAPER] "See all" found on page: %s' % (response.url,))
                continue
            # german: "Alle ... Ergebnisse"
            if result.select(u".//a[contains(text(), 'Alle')][contains(text(), 'Ergebnisse')]"):
                self.log('[AMAZON SCRAPER] "See all" found on page: %s' % (response.url,))
                continue
            # spanish: "Ver los ... resultados"
            if result.select(u".//a[contains(text(), 'Ver los')][contains(text(), 'resultados')]"):
                self.log('[AMAZON SCRAPER] "See all" found on page: %s' % (response.url,))
                continue

            product_name = result.select(u'.//h3/a/span/text()').extract()
            if product_name and product_name[0].endswith('...'):
                new_product_name = result.select(u'.//h3/a/span/@title').extract()
                if new_product_name:
                    product_name = new_product_name

            if not product_name:
                product_name = result.select(u'.//h3/a/text()').extract()
                if product_name and product_name[0].endswith('...'):
                    new_product_name = result.select(u'.//h3/a/@title').extract()
                    if new_product_name:
                        product_name = new_product_name

            if not product_name:
                product_name = result.select(u'.//h2//text()').extract()
                if len(product_name) > 2:
                    product_name = [''.join(product_name[1:]).strip()]
                elif len(product_name) == 2:
                    product_name = result.select(u'.//h2/text()').extract()
            if not product_name:
                if result.select('.//h3'):
                    text = result.select(".//h3/text()").extract()[0].strip()
                    if not text:
                        continue
                else:
                    continue
                raise AmazonScraperException("Couldn't extract product name from product list: %s" % response.url)
            product_name = product_name[0].strip()
            product_name = product_name[0:1020] + '...' if len(product_name) > 1024 else product_name

            identifier = result.select('./@name').extract()
            if not identifier:
                identifier = result.select('@data-asin').extract()
            if not identifier:
                raise AmazonScraperException("Could not extract identifier for product \"%s\" from page: %s" %
                                             (product_name, response.url))
            identifier = identifier[0].strip()

            price = result.select('.//span[contains(@class, "lrg") and contains(@class, "red") and contains(@class, "bld")]//text()').extract()
            if not price:
                price = result.select('.//span[contains(@class, "price")]/text()').extract()
            if not price and not amazon_direct:
                # This price is not valid for amazon direct spiders
                price = result.select('.//span[contains(@class, "price")]//text()').extract()
            if not price:
                self.log('[AMAZON SCRAPER] No price found for %s on %s' % (product_name, response.url))
                continue

            price = price[0].strip()
            product = {}

            product['name'] = AmazonFilter.filter_name(product_name)

            brand = result.select(u'.//h3/span[contains(text(),"by")]/text()').extract()
            if not brand:
                brand = result.select(u'.//h3/span[contains(text(),"von")]/text()').extract()
            if not brand:
                brand = result.select(u'.//div[span[contains(text(),"by")]]/span[2]/text()').extract()
            if not brand:
                brand = result.select(u'.//h2/strong[1]/text()').extract()

            if brand:
                product['brand'] = AmazonFilter.filter_brand(brand[0])

            product['price'] = self._extract_price(response.url, price)

            product['identifier'] = identifier
            product['asin'] = identifier

            url = result.select(u'.//h3/a/@href').extract()
            if not url:
                url = result.select(u'.//a[contains(@class, "access-detail-page")]/@href').extract()
            if not url:
                raise AmazonScraperException("Could not extract url for product \"%s\" from page: %s" %
                                             (product_name, response.url))
            url = url[0]
            url = urljoin(base_url, url)
            if amazon_direct and AmazonUrlCreator.is_seller_url(url):
                url = AmazonUrlCreator.make_amazon_direct_url(url)
            product['url'] = url

            if preloaded_images:
                pre_image_url = preloaded_images.pop()
            else:
                pre_image_url = ''

            image_url = result.select(u'.//img[contains(@class, "productImage")]/@src').extract()
            if not image_url:
                image_url = result.select(u'.//img[contains(@class, "access-image")]/@src').extract()
            if image_url:
                product['image_url'] = urljoin(base_url, image_url[0])
                if len(product['image_url']) > 1024:
                    product['image_url'] = pre_image_url

            reviews_url = result.select(u'ul/li/span[@class="rvwCnt"]/a/@href').extract()
            if not reviews_url:
                reviews_url = result.select(u'.//div[span//i[contains(@class, "a-icon-star")]]/a/@href').extract()
            if not reviews_url:
                reviews_url = result.select(u'.//a[contains(@href, "reviews")]/@href').extract()
            if reviews_url:
                reviews_url = AmazonUrlCreator.build_reviews_list_url_from_asin(
                    AmazonUrlCreator.get_domain_from_url(response.url), product['asin']
                )
                product['reviews_url'] = urljoin('http://www.amazon.com', reviews_url)
            else:
                product['reviews_url'] = None

            more_buying_choices = \
                result.select('.//li[@class="sect mbc"]/../li[contains(@class,"mkp2")]/a/@href').extract()
            if not more_buying_choices:
                more_buying_choices = result.select('.//li[contains(@class,"mkp2")]/a/@href').extract()
            if not more_buying_choices:
                more_buying_choices = result.select('.//a[contains(@href, "offer-listing")]/@href').extract()
            if more_buying_choices:
                for mbc_url in more_buying_choices:
                    mbc_url = urljoin(base_url, mbc_url)
                    parsed_url = urlparse(mbc_url)
                    mbc_url_new = urlunparse(ParseResult(
                        scheme=parsed_url.scheme,
                        netloc=parsed_url.netloc,
                        path=parsed_url.path,
                        params='',
                        query='condition=new',
                        fragment=''
                    ))
                    mbc_url_used = urlunparse(ParseResult(
                        scheme=parsed_url.scheme,
                        netloc=parsed_url.netloc,
                        path=parsed_url.path,
                        params='',
                        query='condition=used',
                        fragment=''
                    ))
                    product['mbc_list_url_new'] = mbc_url_new
                    product['mbc_list_url_used'] = mbc_url_used

            product['result'] = result
            products.append(product)

        return products

    def scrape_search_results_page(self, response, amazon_direct=False):
        """
        Returns:
        - list of products
        - list of suggested products
        - page number
        - next page url
        - number of results
        - list of urls for suggested searches
        """
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        results = hxs.select(u'//div[@id="atfResults" or @id="btfResults"]//div[starts-with(@id, "result_")][not(contains(@id, "empty"))]')
        if not results:
            results = hxs.select(u'//div[@id="rightResultsATF" or @id="btfResults"]//div[starts-with(@id, "result_")]')
        if not results:
            if not hxs.select("//h1[@id='noResultsTitle']"):
                results = hxs.select('//div[@id="resultsCol"]//div[@id="atfResults" or @id="btfResults"]//li[@data-asin and contains(@id, "result_")]')
                if not results:
                    results = hxs.select('//div[@id="resultsCol"]/div[1]//li[@data-asin and contains(@id, "result_")]')
                if not results:
                    results = hxs.select(u'//div[@id="rightResultsATF" or @id="btfResults"]//li[starts-with(@id, "result_")]')
        a = len(results)

        results = self._process_search_results(response, results, amazon_direct)

        b = len(results)
        if b < a and b < (a - 1):
            self.log("[[TESTING]] Found results differ for: %s" % response.url)

        # Follow suggested links only on original search page
        suggested_search_urls = hxs.select(
            u'//div[contains(@class,"fkmrResults")]//h3[contains(@class, "fkmrHead")]//a/@href').extract()
        if not suggested_search_urls:
            suggested_search_urls = hxs.select(u"//div[@id='resultsCol']//h3/a/@href").extract()
        suggested_search_urls = [urljoin(base_url, url) for url in suggested_search_urls]

        suggested_results = hxs.select(
            u'//div[contains(@class,"fkmrResults")]//div[starts-with(@id, "result_")][not(contains(@id, "empty"))]')
        if not suggested_results:
            if hxs.select("//h1[@id='noResultsTitle']"):
                suggested_results = hxs.select(
                    '//div[@id="resultsCol"]/div//li[@data-asin and contains(@id, "result_")]')
            else:
                suggested_results = hxs.select(
                    '//div[@id="resultsCol"]/div[3]//li[@data-asin and contains(@id, "result_")]')
        suggested_results = self._process_search_results(response, suggested_results)

        next_url = hxs.select(u'//a[@id="pagnNextLink"]/@href').extract()
        if not next_url:
            next_url = hxs.select(u'//ul[@class="a-pagination"]/li[@class="a-last"]/a/@href').extract()
        if not next_url:
            next_url = hxs.select("//a[contains(text(), 'Next')]/@href").extract()
        next_url = urljoin(base_url, next_url[0]) if next_url else None

        current_page = hxs.select('//span[@class="pagnCur"]/text()').extract()
        if not current_page:
            current_page = hxs.select(u'//ul[@class="a-pagination"]/li[@class="a-selected"]/a/text()').extract()
        current_page = current_page[0] if current_page else None

        results_count = None
        results_count_el = hxs.select('//h2[@id="resultCount"]')
        if not results_count_el:
            results_count_el = hxs.select('//h2[@id="s-result-count"]')

        results_regex1 = r'([\d,.]+)\-([\d,.]+) \w+ ([\s\d,.]+) \w+'
        results_regex2 = r'([\d,.]+) \w+'
        if results_count_el:
            # check plain text
            text = results_count_el.select('text()').extract()
            if text and not text[0].strip():
                text = None
            if not text:
                text = results_count_el.select('span/text()').extract()
            if text:
                text = text[0].replace(u"\xa0", "")
                m1 = re.search(results_regex1, text, re.I + re.U)
                m2 = re.search(results_regex2, text, re.I + re.U)
                if m1:
                    results_count = int(m1.group(3).replace(",", "").replace(".", ""))
                elif m2:
                    results_count = int(m2.group(1).replace(",", "").replace(".", ""))

        max_pages = hxs.select('//div[@id="pagn"]/span[@class="pagnDisabled"]/text()').re(r'\d+')
        if not max_pages:
            max_pages = hxs.select('//div[@id="pagn"]//ul[@class="a-pagination"]/li[@class="a-disabled"]/text()').re(r'\d+')
        if max_pages:
            max_pages = int(max_pages[-1])
        else:
            max_pages = None

        try:
            price_filter_form = hxs.select('//div[@class="customPriceV2"]/form')
            action_url = urljoin(base_url, price_filter_form.select('@action').extract()[0])
            filter_params = dict(
                zip(price_filter_form.select('.//input/@name').extract(),
                    map(lambda v: v.encode('utf8'), price_filter_form.select('.//input/@value').extract())))
        except:
            action_url = None
            filter_params = None

        if action_url and filter_params:
            filter_form = {
                'url': action_url,
                'params': filter_params
            }
        else:
            filter_form = None

        current_cat = hxs.select("//select[@class='searchSelect']/option[@current='true']/text()").extract()
        if current_cat:
            current_cat = current_cat[0]
        else:
            current_cat = None
        current_cat_passed = False
        subcategory_urls = []
        sub_count = 0
        for el in hxs.select("//div[@class='categoryRefinementsSection']/ul/li"):
            if not current_cat or current_cat_passed:
                url = el.select('a[span[@class="refinementLink"]]/@href').extract()
                if url:
                    url = url[0]
                    subcategory_urls.append(urljoin(base_url, url))
                    pd_count = el.select('a/span[@class="narrowValue"]/text()').re('\((.*)\)')
                    if pd_count:
                        pd_count = pd_count.pop().replace(",", "").replace(".", "")
                    else:
                        pd_count = 0
                    sub_count += int(pd_count)
            else:
                if current_cat:
                    selected_cat = el.select('strong/text()')
                    if selected_cat:
                        current_cat_passed = True

        if subcategory_urls:
            if sub_count < results_count:
                self.log("[SCRAPER] Number of subcategory products %d is less than total number of results %d: %s" %
                         (sub_count, results_count, response.url))
                subcategory_urls = []

        # it's the sign of message:
        # `Your search "<search query>" did not match any products, so we searched in All Departments`
        # this usually appears when searching some term in specific category
        if response.xpath("//div[@id='apsRedirectLink']").extract():
            is_non_specific_cat_results = True
        else:
            is_non_specific_cat_results = False

        return {
            'products': results,
            'suggested_products': suggested_results,
            'suggested_search_urls': suggested_search_urls,
            'next_url': next_url,
            'current_page': current_page,
            'results_count': results_count,
            'max_pages': max_pages,
            'filter_form': filter_form,
            'subcategory_urls': subcategory_urls,
            'is_non_specific_cat_results': is_non_specific_cat_results
        }

    def scrape_product_details_page(self, response, only_color=False, collect_new_products=True,
                                    collect_used_products=False):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        name = hxs.select("//h1[@class='parseasinTitle']/span/span//text()").extract()
        if not name:
            name = hxs.select("//span[@id='productTitle']/text()").extract()
        if not name:
            name = hxs.select("//h1[contains(@class, 'parseasinTitle')]/span/text()").extract()
        if not name:
            return None

        name = AmazonFilter.filter_name(name[0])

        asin = re.findall(r'current_asin\":\"([^,]*)\",',
                          response.body_as_unicode().replace('\n', ''))

        if not asin:
            asin = hxs.select("//input[@id='ASIN']/@value").extract()
        if not asin:
            asin = hxs.select("//input[@name='ASIN']/@value").extract()
        if not asin:
            asin = hxs.select("//input[@name='ASIN.0']/@value").extract()
        if not asin:
            asin = hxs.select("//li[b[contains(text(), 'ASIN:')]]/text()").extract()
        if not asin:
            asin = hxs.select("//tr[td[contains(text(), 'ASIN')]]/td[@class='value']/text()").extract()
        asin = asin[0].strip()

        seller_id = hxs.select("//input[@id='merchantID']/@value").extract()
        if not seller_id:
            seller_id = hxs.select("//input[@name='merchantID']/@value").extract()
        if not seller_id:
            seller_id = hxs.select("//input[@id='sellingCustomerID']/@value").extract()
        if not seller_id:
            seller_id = hxs.select("//input[@name='sellingCustomerID']/@value").extract()
        if not seller_id:
            seller_id = None
        else:
            seller_id = seller_id[0]

        big_data = re.findall(r'P.register\(\'twister-js-init-mason-data\', function\(\) {'
                              r'\s*var dataToReturn = ({.*});\s*return dataToReturn',
                              response.body_as_unicode().replace('\n', ''))
        if big_data:
            big_data = json.loads(big_data[0])

            options = big_data['asin_variation_values']

            display_data = big_data['dimensionValuesDisplayData']

            dimensions = big_data['dimensions']

            dimension_labels = big_data['variationDisplayLabels']

        else:

            options = re.findall(r'var asin_variation_values = ({.*});  var stateData',
                                 response.body_as_unicode().replace('\n', ''))
            if not options:
                options = re.findall(r'asin_variation_values\":({.*}),\"vari',
                                     response.body_as_unicode().replace('\n', ''))

            display_data = re.findall(r'var dimensionValuesDisplayData = ({[^}]*})',
                                      response.body_as_unicode().replace('\n', ''))
            if not display_data:
                display_data = re.findall(r'dimensionValuesDisplayData\":({[^}]*})',
                                          response.body_as_unicode().replace('\n', ''))

            dimensions = re.findall(r'dimensions\":(\[.*\]),\"dimensionsDisplayType',
                                    response.body_as_unicode().replace('\n', ''))

            dimension_labels = re.findall(r'variationDisplayLabels\":({.*}),\"toggleSwatchesWeblab',
                                          response.body_as_unicode().replace('\n', ''))

            option_values = re.findall(r'var variation_values = ({[^}]*})',
                                       response.body_as_unicode().replace('\n', ''))
            if not option_values:
                option_values = re.findall(r'\"variation_values\":({.*}),\"num_total_variations',
                                           response.body_as_unicode().replace('\n', ''))

            hxs.select("//div[@id='variation_size_name']//select/option[@selected]/text()").extract()

            try:
                options = json.loads(options[0]) if options else {}
            except ValueError:
                try:
                    options = json.loads(fix_json(options[0])) if options else {}
                except ValueError:
                    msg = "Can't scrape options from %s" % response.url
                    self.log('[AMAZON SCRAPER] ' + msg, level=logging.ERROR)
                    raise AmazonScraperProductDetailsException(msg)
            try:
                display_data = json.loads(display_data[0]) if display_data else {}
            except ValueError:
                try:
                    display_data = json.loads(fix_json(display_data[0])) if display_data else {}
                except ValueError:
                    msg = "Can't scrape display options from %s" % response.url
                    self.log('[AMAZON SCRAPER] ' + msg, level=logging.ERROR)
                    raise AmazonScraperProductDetailsException(msg)

            try:
                dimensions = json.loads(dimensions[0]) if dimensions else {}
            except ValueError:
                try:
                    dimensions = json.loads(fix_json(dimensions[0])) if dimensions else {}
                except ValueError:
                    msg = "Can't scrape dimensions from %s" % response.url
                    self.log('[AMAZON SCRAPER] ' + msg, level=logging.ERROR)
                    raise AmazonScraperProductDetailsException(msg)

            try:
                dimension_labels = json.loads(dimension_labels[0]) if dimension_labels else {}
            except ValueError:
                try:
                    dimension_labels = json.loads(fix_json(dimension_labels[0])) if dimension_labels else {}
                except ValueError:
                    msg = "Can't scrape dimension_labels from %s" % response.url
                    self.log('[AMAZON SCRAPER] ' + msg, level=logging.ERROR)
                    raise AmazonScraperProductDetailsException(msg)

            try:
                option_values = json.loads(option_values[0]) if option_values else {}
            except ValueError:
                try:
                    option_values = json.loads(fix_json(option_values[0])) if option_values else {}
                except ValueError:
                    msg = "Can't scrape option_values from %s" % response.url
                    self.log('[AMAZON SCRAPER] ' + msg, level=logging.ERROR)
                    raise AmazonScraperProductDetailsException(msg)

        if only_color:
            if 'color_name' in dimensions:
                for option_id, option_data in options.items():
                    keys = option_data.keys()
                    for key in keys:
                        if key.lower() not in ('asin', 'color_name'):
                            del(option_data[key])

                color_dim_index = dimensions.index('color_name')

                for option_id, option_data in display_data.items():
                    display_data[option_id] = [option_data[color_dim_index]]

                uniq_colors = {x['color_name'] for x in options.values()}

                new_options = {}

                if asin in options:
                    new_options[asin] = options[asin]
                    uniq_colors.remove(options[asin]['color_name'])

                # as there could be several ASINs per color we should sort ASINs
                # so we will be picking the same ASIN for colour every crawl
                for option_id in sorted(options.keys()):
                    option_data = options[option_id]
                    if option_data['color_name'] in uniq_colors:
                        new_options[option_id] = option_data
                        uniq_colors.remove(option_data['color_name'])
                options = new_options

                new_display_data = {}
                for option_id in options:
                    if option_id in display_data:
                        new_display_data[option_id] = display_data[option_id]
                display_data = new_display_data

                dimensions = [dimensions[color_dim_index]]
                dimension_labels = {'color_name': dimension_labels['color_name']}
            else:
                options = {}

        option_dicts = []
        if options:
            for option_id, option_data in options.items():
                option_url = AmazonUrlCreator.build_url_from_asin(AmazonUrlCreator.get_domain_from_url(response.url),
                                                                  option_id)

                options_strs = None
                if display_data:
                    if option_id in display_data:
                        options_strs = display_data[option_id]

                texts = []

                if options_strs:
                    for i, dim_value in enumerate(options_strs):
                        if dimensions and dimension_labels:
                            dim_name = dimension_labels[dimensions[i]]
                            texts.append('%s: %s' % (dim_name, dim_value))
                        else:
                            texts.append(dim_value)
                else:
                    for dim_name, dim_value in option_data.items():
                        if dim_name.lower() == 'asin':
                            continue
                        dim_text_value = option_values[dim_name][int(dim_value)]
                        texts.append('%s: %s' % (dim_name, dim_text_value))

                option_dict = {
                    'texts': texts,
                    'url': option_url,
                    'identifier': option_id
                }
                option_dicts.append(option_dict)

        option_texts = []
        if asin in options:
            options_strs = None
            if display_data:
                if asin in display_data:
                    options_strs = display_data[asin]

            for i, dim_value in enumerate(options_strs):
                if dimensions and dimension_labels:
                    dim_name = dimension_labels[dimensions[i]]
                    option_texts.append('%s: %s' % (dim_name, dim_value))
                else:
                    option_texts.append(dim_value)

        if not option_texts:
            for el in hxs.select("//form[@id='twister']/div"):
                label = el.select(".//div[contains(@class, 'a-row')]/label/text()").extract()
                value = el.select(".//div[contains(@class, 'a-row')]/span[contains(@class, 'selection')]/text()").extract()

                res = ''
                if label:
                    res += label[0].strip()

                if value:
                    res += ' ' + value[0].strip()
                    option_texts.append(res)

        if not option_texts:
            option_texts = hxs.select('//select[contains(@id, "dropdown_selected")]/option[@selected]/text()')\
                .extract()

            if option_texts or not hxs.select('//select[contains(@id, "dropdown_selected")]'):
                option_texts += hxs.select("//div[@class='variationSelected']//b[@class='variationLabel']/text()").extract()

            option_texts = [AmazonFilter.filter_name(x) for x in option_texts]
            if not option_texts:
                selected_colour = re.findall(r'data\["landingAsinColor"\] = \'([^\']*)\';', response.body_as_unicode())
                if selected_colour and selected_colour[0].lower() != 'initial':
                    option_texts = [selected_colour[0]]

        name_with_options = ''
        if option_texts:
            name_with_options = name + ' [' + ', '.join(option_texts) + ']'

        # soup = BeautifulSoup(response.body)
        # try:
        #     soup_form = soup.find(id='handleBuy')
        #     price = soup_form.find('b', 'priceLarge')
        #     if not price:
        #         price = soup_form.find('span', 'priceLarge')
        #     if not price:
        #         price = soup_form.find('span', 'price')
        #     if not price:
        #         price = soup_form.find('span', 'pa_price')
        #     if price:
        #         price = price.text
        #     else:
        #         price = None
        # except:
        #     pass

        price = None

        if not price:
            price = hxs.select('//div[@id="price"]//td[text()="Price:"]'
                               '/following-sibling::td/span/text()').extract()
        if not price:
            price = hxs.select('//span[@id="priceblock_saleprice"]/text()').extract()
        if not price:
            price = hxs.select('//span[@id="actualPriceValue"]/*[@class="priceLarge"]/text()').extract()
        if not price:
            price = hxs.select('//*[@class="priceLarge"]/text()').extract()
        if not price:
            price = hxs.select('//span[@id="priceblock_ourprice"]/text()').extract()
        if not price:
            price = hxs.select('//span[@id="priceblock_dealprice"]/text()').extract()
        if not price:
            price = hxs.select('//div[@id="buyNewSection"]//span[contains(@class, "offer-price")]/text()').extract()

        if not price:
            for condition_container in hxs.select("//div[span/span[@class='a-color-price']]"):
                if price:
                    break
                for condition_subcontainer in condition_container.select("span"):
                    condition = condition_subcontainer.select("a/text()").re('\d+\s*(.+)')
                    condition_price = condition_subcontainer.select("span/text()").extract()
                    if condition:
                        if condition[0].lower() == 'new' and collect_new_products:
                            price = condition_price
                            break
                        elif condition[0].lower() == 'used' and collect_used_products:
                            price = condition_price
                            break

        if price:
            price = price[0]
        else:
            price = None

        ajax_price_url = None
        ajax_price_obj = hxs.select("//span[*[contains(text(), 'See price in cart')]]/@data-a-modal").extract()
        if ajax_price_obj:
            ajax_price_obj = json.loads(ajax_price_obj[0])
            ajax_price_url = urljoin(get_base_url(response), ajax_price_obj['url'])

        brand = hxs.select("//span[@class='brandLink']/a/text()").extract()
        if not brand:
            brand = hxs.select('//div[@class="buying"]/span[contains(text(), "by")]/a/text()').extract()
        if not brand:
            brand = hxs.select('//div[@class="buying"]/span[span[contains(@class, "by")]]/a/text()').extract()
        if not brand:
            brand = hxs.select("//a[@id='brand']/text()").extract()
        brand = brand[0].strip() if brand else None

        # scrape category
        categories = map(string.strip,
                         hxs.select('//div[@id="wayfinding-breadcrumbs_feature_div"]//li/span/a/text()').extract())

        vendor = hxs.select(u'//div[@class="buying"]//a[contains(@href,"seller/at-a-glance")]/text()').extract()
        if not vendor:
            vendor = hxs.select('//div[@id="soldByThirdParty"]/b/text()').extract()
        if not vendor:
            vendor = hxs.select("//div[contains(text(), 'old by')]/a/text()").extract()
        vendor = vendor[0] if vendor else None

        if not vendor:
            amazon_price = hxs.select('//span[@id="actualPriceValue"]/b/text()').extract()
            if not amazon_price:
                amazon_price = hxs.select('//span[@id="priceblock_ourprice"]/text()').extract()
            if not amazon_price:
                amazon_price = hxs.select('//div[@id="buybox"]/div[contains(., "Dispatched from and sold by Amazon")]//span[contains(@class, "price")]/text()').extract()
                # Checks if it is an amazon product
            if amazon_price:
                vendor = 'Amazon'

        if vendor:
            if vendor.lower().startswith('amazon'):
                vendor = 'Amazon'
            else:
                vendor = 'AM - ' + vendor
        else:
            vendor = None

        used_vendor = hxs.select(
            u'//div[@class="buying"]//a[contains(@href,"seller/at-a-glance")]/text()/../../../@id').extract()
        used_vendor = used_vendor[0] if used_vendor else None

        if used_vendor:
            if used_vendor.lower().startswith('amazon'):
                used_vendor = 'Amazon'
            else:
                used_vendor = 'AM - ' + used_vendor
        else:
            used_vendor = None

        image_url = hxs.select("//img[@id='main-image']/@src").extract()
        if not image_url:
            image_url = hxs.select("//img[@id='landingImage']/@src").extract()
        if not image_url:
            image_url = hxs.select("//img[@id='imgBlkFront']/@data-a-dynamic-image").re('(http.+?)"')
        image_url = image_url[0] if image_url else None

        if image_url is not None and len(image_url) > 1024:
            image_url = hxs.select('//img[@id="main-image-nonjs"]/@src').extract()
            if not image_url:
                image_data_json = hxs.select("//img[@id='landingImage']/@data-a-dynamic-image").extract()
                if image_data_json:
                    image_data = json.loads(image_data_json[0])
                    try:
                        image_url = image_data.keys()[0]
                    except (AttributeError, IndexError):
                        image_url = ''

        shipping = hxs.select(
            '//div[@id="buyboxDivId"]//span[@class="plusShippingText"]/text()').extract()
        if not shipping:
            shipping = hxs.select('//span[contains(@class, "shipping3P")]/text()').re(r'([\d,.]+)')
        shipping_cost = shipping[0] if shipping else None

        model = hxs.select('//span[@class="tsLabel" and contains(text(), "Part Number")]/../span[2]/text()').extract()
        if not model:
            model = hxs.select('//b[contains(text(), "model number")]/../text()').extract()
        if not model:
            model = hxs.select('//tr[@class="item-model-number"]/td[@class="value"]/text()').extract()
        if not model:
            model = hxs.select('//li[b[contains(text(), "Item model number:")]]/text()').extract()
        if not model:
            model = hxs.select('//span[@class="tsLabel" and contains(text(), "Part Number")]/../span[2]/text()').extract()
        if not model:
            model = hxs.select('//tr[td[contains(text(), "Model Number")]]/td[@class="value"]/text()').extract()
        if not model:
            model = hxs.select('//tr[th[contains(text(), "Model number")]]/td/text()').extract()

        model = model[0].strip() if model else ''

        reviews_url = hxs.select("//div[contains(@id, 'ReviewsSummary')]//a[contains(text(), 'reviews')]/@href").extract()
        if not reviews_url:
            reviews_url = hxs.select("//div[@id='summaryStars']/a/@href").extract()
        if not reviews_url:
            reviews_url = hxs.select("//div[@class='buying']//span[@class='crAvgStars']/a/@href").extract()
        if not reviews_url:
            reviews_url = hxs.select("//div[@id='revSum']/div[1]/div/a/@href").extract()
        if not reviews_url:
            reviews_url = hxs.select("//a[contains(@id, 'acrCustomerReviewLink')]/@href").extract()
        if not reviews_url:
            reviews_url = hxs.select("//div[contains(@id, 'CustomerReviews')]//a[span[contains(text(), 'reviews')]]/@href").extract()
        reviews_url = urljoin(get_base_url(response), reviews_url[0]) if reviews_url else ''

        stock_container = hxs.select('//div[@id="outOfStock"]')
        if not stock_container:
            stock_container = hxs.select('//div[@id="availability"]')

        if stock_container:
            unavailable = self._check_if_unavailable(stock_container)
        else:
            unavailable = False

        fulfilled_by = hxs.select("//a[@id='SSOFpopoverLink']/text()").re('Fulfilled by (.*)')
        fulfilled_by = fulfilled_by[0] if fulfilled_by else None

        product = {
            'name': name,
            'name_with_options': name_with_options,
            'brand': brand,
            'categories': categories,
            'price': self._extract_price(response.url, price) if price is not None else None,
            'identifier': asin,
            'asin': asin,
            'url': AmazonUrlCreator.build_url_from_asin(AmazonUrlCreator.get_domain_from_url(response.url), asin),
            'image_url': image_url,
            'shipping_cost': shipping_cost,
            'model': model,
            'vendor': vendor,
            'used_vendor': used_vendor,
            'option_texts': option_texts,
            'options': option_dicts,
            'reviews_url': reviews_url,
            'seller_identifier': seller_id,
            'ajax_price_url': ajax_price_url,
            'unavailable': unavailable,
            'fulfilled_by': fulfilled_by,
        }

        offer_listing = hxs.select('//div[@id="olpDivId"]/span[@class="olpCondLink"]/a/@href').extract()
        if not offer_listing:
            offer_listing = hxs.select('//div[@id="olp_feature_div"]//span/a/@href').extract()
        if not offer_listing:
            offer_listing = hxs.select('//li[@class="swatchElement selected"]//span/a/@href').extract()
        if not offer_listing:
            offer_listing = hxs.select('//span[@class="tmm-olp-links"]/span/a/@href').extract()
        if not offer_listing:
            offer_listing = hxs.select('//div[@id="mbc"]//h5//@href').extract()

        product['mbc_list_url_new'] = ''
        product['mbc_list_url_used'] = ''
        for mbc_url in offer_listing:
            params = parse_qs(urlparse(mbc_url).query)
            condition = params.get('condition', ['any'])[0].strip()
            if condition == 'new':
                product['mbc_list_url_new'] = urljoin(base_url, mbc_url)
            elif condition == 'used':
                product['mbc_list_url_used'] = urljoin(base_url, mbc_url)
        if not product['mbc_list_url_new']:
                product['mbc_list_url_new'] = AmazonUrlCreator.build_offer_listing_new_url_from_asin(
                    AmazonUrlCreator.get_domain_from_url(response.url), asin)
        if not product['mbc_list_url_used']:
                product['mbc_list_url_used'] = AmazonUrlCreator.build_offer_listing_used_url_from_asin(
                    AmazonUrlCreator.get_domain_from_url(response.url), asin)
        if self.is_kindle_book(response):
            product['mbc_list_url_new'] = None
            product['mbc_list_url_used'] = None

        return product

    def scrape_mbc_list_page(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        try:
            url = hxs.select('//a[@id="olpDetailPageLink"]/@href').extract()[0]
            url = urljoin(base_url, url)
            url_parts = url.split('/')
            try:
                asin = url_parts[url_parts.index('product') + 1]
            except ValueError:
                asin = url_parts[url_parts.index('dp') + 1]
        except IndexError:
            return None

        products = []
        for i, result in enumerate(hxs.select('//div[@id="olpOfferList"]//div[contains(@class, "olpOffer")]'), 1):
            product = {}

            name = ' '.join(hxs.select(u'//div[@id="olpProductDetails"]/h1//text()').extract()).strip()
            product['name'] = AmazonFilter.filter_name(name)

            brand = hxs.select(u'//div[@id="olpProductByline"]/text()').extract()
            if brand:
                product['brand'] = AmazonFilter.filter_brand(brand[0])

            price_el = result.select('.//span[contains(@class, "olpOfferPrice")]/text()')
            if not price_el:
                # check if there is text "Add to basket to check price"
                price_text = result.select('.//div[p[contains(@class, "olpShippingInfo")]]/text()').extract()[0].strip()
                if 'basket' in price_text.lower() or 'cart' in price_text.lower():
                    product['price'] = None
                else:
                    raise AmazonScraperException(
                        "Couldn't extract price from element %d from url %s" % (i, response.url))
            else:
                price = price_el.extract()[0].strip()
                product['price'] = self._extract_price(response.url, price)

            seller_id = None
            seller_urls = result.select(u'.//*[contains(@class, "olpSellerName")]//a/@href').extract()
            if seller_urls:
                seller_url_ = seller_urls[0]
                if 'seller=' in seller_url_:
                    seller_id = url_query_parameter(seller_url_, 'seller')
                else:
                    seller_parts = seller_url_.split('/')
                    try:
                        seller_id = seller_parts[seller_parts.index('shops') + 1]
                    except (IndexError, KeyError, ValueError):
                        # External website (link "Shop this website"?)
                        seller_id = url_query_parameter(seller_url_, 'merchantID')

            product['identifier'] = asin
            product['asin'] = asin
            if seller_id:
                product['seller_identifier'] = seller_id
                product['url'] = AmazonUrlCreator.build_url_from_asin_and_dealer_id(
                    AmazonUrlCreator.get_domain_from_url(response.url), asin, seller_id)
                product['seller_url'] = AmazonUrlCreator.build_vendor_url(
                    AmazonUrlCreator.get_domain_from_url(response.url), seller_id)
                # product['url'] = 'http://%s/gp/product/%s/?m=%s' % (self._get_domain_from_url(response.url), product_id, seller_id)
            else:
                product['seller_identifier'] = None
                product['url'] = AmazonUrlCreator.build_url_from_asin(
                    AmazonUrlCreator.get_domain_from_url(response.url), asin)
                product['seller_url'] = None
                # product['url'] = 'http://%s/gp/product/%s/' % (self._get_domain_from_url(response.url), product_id)

            shipping = result.select('.//span[@class="olpShippingPrice"]/text()').extract()
            if shipping:
                product['shipping_cost'] = shipping[0]

            image_url = hxs.select(u'//div[@id="olpProductImage"]//img/@src').extract()
            if image_url:
                product['image_url'] = urljoin(base_url, image_url[0])

            vendor = result.select(u'.//div[contains(@class, "olpSellerColumn")]//img/@title').extract()
            if not vendor:
                vendor = result.select(u'.//div[contains(@class, "olpSellerColumn")]//img/@alt').extract()
            if not vendor:
                vendor = result.select(u'.//*[contains(@class, "olpSellerName")]//a/b/text()').extract()
            if not vendor:
                vendor = result.select(u'.//*[contains(@class, "olpSellerName")]//span/a/text()').extract()
            if vendor:
                vendor = vendor[0]
                if vendor.lower().startswith('amazon'):
                    vendor = 'Amazon'
                else:
                    vendor = 'AM - ' + vendor
                product['vendor'] = vendor
            elif not seller_id:
                product['vendor'] = 'Amazon'
            else:
                product['vendor'] = None

            fulfilled_by_amazon = bool(result.xpath(".//div[contains(@class, 'olpDeliveryColumn')]/"
                                                     "div[contains(@class, 'olpBadgeContainer')]"))

            product['fulfilled_by_amazon'] = fulfilled_by_amazon

            products.append(product)

        next_url = hxs.select('//ul[@class="a-pagination"]/li[@class="a-last"]/a/@href').extract()
        next_url = urljoin(base_url, next_url[0]) if next_url else None

        current_page = hxs.select('//ul[@class="a-pagination"]/li[@class="a-selected"]/a/text()').extract()
        current_page = current_page[0] if current_page else None

        return {
            'next_url': next_url,
            'current_page': current_page,
            'products': products
        }

    def scrape_reviews_list_page(self, response, inc_selector=False, collect_author=False, collect_author_url=False):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        # check encoding is OK
        reviews = hxs.select(u'//div[@id="cm_cr-review_list"]/div[contains(@class, "review")]')
        if not reviews:
            reviews = hxs.select(u'//table[@id="productReviews"]//div[@style="margin-left:0.5em;"]')
        if reviews:
            review = reviews[0]
            date = review.select(u'.//span[contains(@class, "review-date")]/text()').extract()
            if not date:
                date = review.select(u'.//nobr/text()').extract()
            date = date[0]
            date = date.lstrip('on ').lstrip('le ').lstrip('am ')
            date = parse_review_date_locales(date)
            # date couldn't be parsed because:
            # - encoding is wrong and paged decoded incorrectly
            # - date couldn't be parsed for other reason (which will raise an error later for manual detection)
            if not date:
                response = HtmlResponse(url=response.url, body=response.body, encoding='utf-8')

        hxs = HtmlXPathSelector(response)
        reviews = hxs.select(u'//div[@id="cm_cr-review_list"]/div[contains(@class, "review")]')
        if not reviews:
            reviews = hxs.select(u'//table[@id="productReviews"]//div[@style="margin-left:0.5em;"]')

        review_dicts = []

        for review in reviews:
            date = review.select(u'.//span[contains(@class, "review-date")]/text()').extract()
            if not date:
                date = review.select(u'.//nobr/text()').extract()
            date = date[0]
            date = date.lstrip('on ').lstrip('le ').lstrip('am ')
            date = parse_review_date_locales(date)

            rating = review.select(u'.//i[contains(@class, "review-rating")]/span/text()').extract()
            if rating and not rating[0].replace('.', '').isdigit():
                rating = None
            if not rating:
                rating = review.select(u'.//text()').re(u'([\d\.]+) out of 5 stars')
            if not rating:
                rating = review.select(u'.//text()').re(u'([\d\.]+) étoiles sur 5')
            if not rating:
                rating = review.select(u'.//text()').re(u'([\d\.]+) von 5 Sternen')
            if not rating:
                rating = review.select(u'.//text()').re(u'([\d\.]+) su 5 stelle')
            if rating:
                rating = int(float(rating[0]))
            else:
                rating = 1
            title = review.select(u'.//a[contains(@class, "review-title")]/text()').extract()
            if not title:
                title = review.select(u'.//b/text()').extract()
            title = title[0]

            if collect_author:
                author = review.select(u'.//a[contains(@class, "author")]/text()').extract()[0]
            if collect_author_url:
                author_url = review.select(u'.//a[contains(@class, "author")]/@href').extract()[0]
                if author_url and not author_url.startswith('http'):
                    author_url = urljoin(base_url, author_url)

            text = review.select(u'.//span[contains(@class, "review-text")]/text()').extract()
            if not text:
                text = ''.join([s.strip() for s in review.select(u'div[@class="reviewText"]/text()').extract()])
            else:
                text = '\n'.join(text)

            url = review.select(u'.//a[contains(@class, "review-title")]/@href').extract()
            if not url:
                url = review.select(".//a[contains(text(), 'Permalink')]/@href").extract()
            if not url:
                url = review.select(".//a[contains(text(), 'Permalien')]/@href").extract()
            if not url:
                url = review.select(".//a[contains(text(), 'Link permanente')]/@href").extract()
            if not url:
                url = review.select(".//a[contains(text(), 'Kommentar als Link')]/@href").extract()

            url = url[0]
            if url and not url.startswith('http'):
                url = urljoin(base_url, url)

            # if comment from verified purchase
            if review.xpath(".//div[contains(@class, 'review-data')]"
                            "      [span[not(contains(@class, 'review-text'))]]/*").extract():
                verified = True
            else:
                verified = False

            identifier = AmazonUrlCreator.get_review_identifier_from_url(url)

            review_dict = {
                'date': date,
                'rating': rating,
                'url': url,
                'identifier': identifier,
                'full_text': u'%s\n%s' % (title, text),
                'verified': verified,
            }
            if collect_author:
                review_dict['author'] = author
            if collect_author_url:
                review_dict['author_url'] = author_url

            if inc_selector:
                review_dict['review_selector'] = review

            review_dicts.append(review_dict)

        next_url = hxs.select("//a[contains(text(), 'Next')][contains(@href, 'product-reviews')]/@href").extract()
        if next_url:
            next_url = next_url[0]
            if next_url == '#':
                current_page = int(url_query_parameter(response.url, 'pageNumber', '1'))
                next_page = current_page + 1
                next_url = add_or_replace_parameter(response.url, 'pageNumber', str(next_page))
        else:
            next_url = None

        if next_url and not next_url.startswith('http'):
            next_url = urljoin(base_url, next_url)

        current_page = hxs.select("//span[@class='paging']/span[@class='on']/text()").extract()
        current_page = current_page[0] if current_page else None

        return {
            'next_url': next_url,
            'current_page': current_page,
            'reviews': review_dicts
        }

    def scrape_review_author_page(self, response):
        if not response.xpath("//span[contains(@class, 'public-name-text')]/text()").extract():
            return None
        author = response.xpath("//span[contains(@class, 'public-name-text')]/text()").extract()[0]
        location = ''.join(response.xpath("//div[contains(@class, 'location-and-occupation-holder')]//text()")
                           .extract()).strip()
        return {
            'author': author,
            'location': location
        }

    def scrape_vendor_page(self, response):
        hxs = HtmlXPathSelector(response)

        name = hxs.select("//div[@id='aag_header']/h1/text()").extract()
        if not name:
            name = hxs.select('//*[@id="sellerName"]/text()').extract()
        if name:
            name = name[0]
        else:
            name = None

        return {
            'name': name
        }

    def scrape_price_from_ajax_price_page(self, response):
        hxs = HtmlXPathSelector(response)

        price = hxs.select("//span[contains(@id, 'priceblock')]/text()").extract()[0].strip()

        return price

    def is_kindle_book(self, response):
        hxs = HtmlXPathSelector(response)

        cat = hxs.select("//div[@id='nav-subnav']/a[1]//text()").extract()

        if not cat:
            return False

        cat = cat[0]

        if 'kindle' in cat.lower():
            return True

        return False


class AmazonUrlCreatorException(Exception):
    pass


class AmazonUrlCreator(object):
    REVIEW_IDENTIFIER_FROM_URL_REGEXS = [
        re.compile(r"/review/([^/]*)/"),
        re.compile(r"/customer-reviews/([^\?^/]*)"),
    ]
    ASIN_FROM_URL_REGEX = re.compile(r"/(?:gp/product|dp)/([^/]*)(?:/|$)")

    @staticmethod
    def _fix_domain(domain):
        if not domain.startswith('www.'):
            domain = 'www.' + domain
        return domain

    @staticmethod
    def get_domain_from_url(url):
        parsed_url = urlparse(url)
        return parsed_url.hostname

    @staticmethod
    def get_product_asin_from_url(url):
        """
        >>> AmazonUrlCreator.get_product_asin_from_url('http://www.amazon.co.uk/gp/product/B0078Y4ME6/?ref=twister_dp_update&ie=UTF8&psc=1')
        'B0078Y4ME6'
        >>> AmazonUrlCreator.get_product_asin_from_url('http://www.amazon.co.uk/LEGO-Star-Wars-10188-Death/dp/B002EEP3NO/ref=sr_1_1/279-2607573-2864855?ie=UTF8&qid=1395239715&sr=8-1&keywords=LEGO+10188')
        'B002EEP3NO'
        >>> AmazonUrlCreator.get_product_asin_from_url('http://www.amazon.co.uk/LEGO-Star-Wars-10188-Death/asd/B002EEP3NO/ref=sr_1_1/279-2607573-2864855?ie=UTF8&qid=1395239715&sr=8-1&keywords=LEGO+10188')
        ''
        >>> AmazonUrlCreator.get_product_asin_from_url('http://www.amazon.co.uk/Beldray-Multi-Functional-Orange-White-Cleaner/dp/B00ULMS360')
        'B00ULMS360'
        """
        m = AmazonUrlCreator.ASIN_FROM_URL_REGEX.search(url)
        if m:
            return m.group(1)
        else:
            return ''

    @staticmethod
    def get_review_identifier_from_url(url):
        """
        >>> AmazonUrlCreator.get_review_identifier_from_url('http://www.amazon.co.uk/review/R2W6KMDRC2DSD2/ref=cm_cr_pr_perm/?ie=UTF8&ASIN=B002EEP3NO&linkCode=&nodeID=&tag=')
        'R2W6KMDRC2DSD2'
        >>> AmazonUrlCreator.get_review_identifier_from_url('http://www.amazon.co.uk/dp/R2W6KMDRC2DSD2/ref=cm_cr_pr_perm/?ie=UTF8&ASIN=B002EEP3NO&linkCode=&nodeID=&tag=')
        ''
        >>> AmazonUrlCreator.get_review_identifier_from_url('http://www.amazon.com/gp/customer-reviews/RXOGJCSOC8MHP?ASIN=B00CTUXKWY')
        'RXOGJCSOC8MHP'
        >>> AmazonUrlCreator.get_review_identifier_from_url('http://www.amazon.com/gp/customer-reviews/R3752I2SE6B55G/ref=cm_cr_pr_rvw_ttl?ie=UTF8&ASIN=B00AU6GHGA')
        'R3752I2SE6B55G'
        """
        for regex in AmazonUrlCreator.REVIEW_IDENTIFIER_FROM_URL_REGEXS:
            m = regex.search(url)
            if m:
                return m.group(1)
        return ''

    @staticmethod
    def build_url_from_asin(domain, asin):
        domain = AmazonUrlCreator._fix_domain(domain)
        url = 'http://%s/gp/product/%s/?ref=twister_dp_update&ie=UTF8&psc=1' % (domain, asin)
        return url

    @staticmethod
    def build_offer_listing_new_url_from_asin(domain, asin):
        domain = AmazonUrlCreator._fix_domain(domain)
        url = 'http://%s/gp/offer-listing/%s/?condition=new' % (domain, asin)
        return url

    @staticmethod
    def build_offer_listing_used_url_from_asin(domain, asin):
        domain = AmazonUrlCreator._fix_domain(domain)
        url = 'http://%s/gp/offer-listing/%s/?condition=used' % (domain, asin)
        return url

    @staticmethod
    def build_url_from_asin_and_dealer_id(domain, asin, dealer_id):
        domain = AmazonUrlCreator._fix_domain(domain)
        url = 'http://%s/gp/product/%s/?m=%s&ref=twister_dp_update&ie=UTF8&psc=1' % (domain, asin, dealer_id)
        return url

    @staticmethod
    def build_search_url(domain, search_string, amazon_direct=False, search_alias=None, search_node=None):
        domain = AmazonUrlCreator._fix_domain(domain)
        if isinstance(search_string, unicode):
            search_string = search_string.encode("utf-8")
        if search_alias is None:
            search_alias = 'aps'
        url = 'http://%s/s/ref=nb_sb_noss' % domain
        url_param = 'search-alias=%s' % search_alias
        params = {
            'url': url_param,
            'field-keywords': search_string
        }

        if search_node:
            params['node'] = search_node

        url = url + '?' + urllib.urlencode(params)
        if amazon_direct:
            url = AmazonUrlCreator.filter_by_amazon_direct(domain, url)
        return url

    @staticmethod
    def filter_by_amazon_direct(domain, url):
        if '.com' in domain:
            code = 'ATVPDKIKX0DER'
        elif '.co.uk' in domain:
            code = 'A3P5ROKL5A1OLE'
        elif '.fr' in domain:
            code = 'A1X6FK5RDHNB96'
        elif '.it' in domain:
            code = 'A11IL2PNWYJU7H'
        elif '.de' in domain:
            code = 'A3JWKAKR8XB7XF'
        elif '.ca' in domain:
            code = 'A3DWYIK6Y9EEQB'
        elif '.es' in domain:
            code = 'A1AT7YVPFBWXBL'
        else:
            raise AmazonUrlCreatorException('Domain %s not found!!' % domain)
        new_url = add_or_replace_parameter(url, 'emi', code)
        return new_url

    @staticmethod
    def build_vendor_url(domain, dealer_id):
        domain = AmazonUrlCreator._fix_domain(domain)
        url = 'http://%s/gp/aag/main?ie=UTF8&seller=%s' % (domain, dealer_id)
        return url

    @staticmethod
    def build_from_existing_with_price_margins(url, low_price, high_price):
        if low_price is None and high_price is None:
            return url
        params = {
            'low-price': low_price,
            'high-price': high_price,
            'x': 0,
            'y': 0,
            'page': 1,
        }
        return AmazonUrlCreator.build_from_existing_with_params(url, params)

    @staticmethod
    def build_from_existing_with_params(url, params):
        """
        None as value means that value should be unset
        """
        parsed_url = urlparse(url)
        parsed_query = dict(parse_qsl(parsed_url.query))

        for param, value in params.items():
            if param in parsed_query and value is None:
                del(parsed_query[param])
            else:
                parsed_query[param] = value

        query = urllib.urlencode(parsed_query)

        res = urlunparse(ParseResult(
            scheme=parsed_url.scheme,
            netloc=parsed_url.netloc,
            path=parsed_url.path,
            params='',
            query=query,
            fragment=''
        ))
        return res

    @staticmethod
    def build_reviews_list_url_from_asin(domain, asin):
        url = "http://%s/product-reviews/%s/" \
              "?sortBy=recent&reviewerType=all_reviews&filterByStar=all_stars" % \
              (domain, asin)

        return url

    @staticmethod
    def check_review_url_is_sorted_by_date(url):
        sorting = url_query_parameter(url, 'sortBy')
        if sorting != 'bySubmissionDateDescending':
            return False
        else:
            return True

    @staticmethod
    def get_reviews_url_sorted_by_date(url):
        return add_or_replace_parameter(url, 'sortBy', 'bySubmissionDateDescending')

    @staticmethod
    def make_amazon_direct_url(url):
        """
        >>> AmazonUrlCreator.make_amazon_direct_url('http://www.amazon.ca/Brother-Wireless-Monochrome-DCPL2540DW-Networking/dp/B00MFG57ZK/ref=sr_1_fkmr0_1?m=A3DWYIK6Y9EEQB&ie=UTF8&qid=1455271993&sr=8-1-fkmr0&keywords=BROTHER+QL570')
        'http://www.amazon.ca/Brother-Wireless-Monochrome-DCPL2540DW-Networking/dp/B00MFG57ZK/ref=sr_1_fkmr0_1?ie=UTF8&qid=1455271993&sr=8-1-fkmr0&keywords=BROTHER+QL570'
        """
        url = url_query_cleaner(url, parameterlist=['m'], remove=True)
        return url

    @staticmethod
    def is_seller_url(url):
        """
        >>> AmazonUrlCreator.is_seller_url('http://www.amazon.ca/Brother-Wireless-Monochrome-DCPL2540DW-Networking/dp/B00MFG57ZK/ref=sr_1_fkmr0_1?m=A3DWYIK6Y9EEQB&ie=UTF8&qid=1455271993&sr=8-1-fkmr0&keywords=BROTHER+QL570')
        True
        >>> AmazonUrlCreator.is_seller_url('http://www.amazon.ca/Brother-Wireless-Monochrome-DCPL2540DW-Networking/dp/B00MFG57ZK/ref=sr_1_fkmr0_1?ie=UTF8&qid=1455271993&sr=8-1-fkmr0&keywords=BROTHER+QL570')
        False
        """
        return url_query_parameter(url, 'm') is not None


class AmazonFilter(object):
    BRAND_CLEAR_DATE_REGEX = re.compile("\(\d+ \w+ \d+\)")

    @staticmethod
    def filter_name(name):
        m = re.search(r"^new offers for", name, re.I)
        if m:
            found = m.group(0)
            res = name.replace(found, "")
        else:
            res = name
        res = res.strip()
        return res

    @staticmethod
    def filter_brand(brand):
        """
        >>> AmazonFilter.filter_brand('LEGO  (8 Jul 2010)')
        'LEGO'
        """
        brand = brand.replace('by ', '').replace('de ', '')
        if AmazonFilter.BRAND_CLEAR_DATE_REGEX.search(brand):
            brand = AmazonFilter.BRAND_CLEAR_DATE_REGEX.sub("", brand)
        brand = brand.strip()

        return brand
