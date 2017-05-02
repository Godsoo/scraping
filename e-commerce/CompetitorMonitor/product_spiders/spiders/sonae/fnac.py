# -*- coding: utf-8 -*-
import datetime
import re, os, csv
import json

from scrapy.spider import BaseSpider
from scrapy.selector import Selector
from scrapy import Request
from scrapy import signals
from scrapy.xlib.pydispatch import dispatcher
from scrapy.utils.url import add_or_replace_parameter

from product_spiders.utils import extract_price_eu
from product_spiders.items import Product, ProductLoaderWithNameStripEU as ProductLoader
from sonaeitems import SonaeMeta
from product_spiders.config import DATA_DIR
HERE = os.path.abspath(os.path.dirname(__file__))


def get_seller_id_from_url(seller_url):
    seller_identifier = re.search("/([^/]*)$", seller_url).group(1)
    return seller_identifier


class FnacSpider(BaseSpider):
    name = "sonae-fnac.pt"
    allowed_domains = ["fnac.pt"]
    search_url = 'http://pesquisa.fnac.pt/SearchResult/ResultList.aspx?ItemPerPage=20&SDM=list&Search=%26&SFilt=1!206&sft=1&sl=0.77000964&ssi=1&sso=1&PageIndex={page}'   
    products = {}
    metadata_ = {}
    deduplicate_identifiers = True
    seen = set()
    seller_ids = {}
    identifiers = {}
    static_offers_url = 'http://www.fnac.pt/Se-Me-Amas-Acustico-ao-Vivo-CD-DVD-Xutos-et-Pontapes-nueve-ocasion?PRID={identifier}&REF={market_type}'

    def __init__(self, *args, **kwargs):
        super(FnacSpider, self).__init__(*args, **kwargs)
        dispatcher.connect(self.spider_idle, signals.spider_idle)

    def get_identifier(self, page_ident):
        ident = page_ident.replace('fcom', '').replace('mp', '')
        return self.identifiers.get(ident, page_ident)

    def get_static_offers_url(self, product_url):
        market_type = 'Marketplace'
        identifier = re.search('/mp(\d+)/', product_url)
        if not identifier:
            identifier = re.search('/a(\d+)$', product_url)
            market_type = 'FnacDirect'
        if identifier:
            identifier = identifier.groups()[0]
        return self.static_offers_url.format(market_type=market_type, identifier=identifier)

    def spider_idle(self):
        self.log('Spider idle.')
        for identifier in self.products:
            base_identifier = identifier.split('-')[0].replace('fcom', '').replace('mp', '')
            if base_identifier in self.seen:
                continue
            self.products[identifier]['base_identifier'] = base_identifier
            url = self.products[identifier]['url']
            exclusive_online = self.metadata_.get(identifier, {}).get('exclusive_online', '')
            if exclusive_online.lower() == 'yes':
                exclusive_online = True
            offers_url = self.get_static_offers_url(url)

            request = Request(offers_url, callback=self.parse_offers_static_page, 
                meta={'exclusive_online': exclusive_online, 'product_info': self.products[identifier]})

            self._crawler.engine.crawl(request, self)

    def start_requests(self):
        if hasattr(self, 'prev_crawl_id'):
            filename = os.path.join(DATA_DIR, '%s_products.csv' % self.prev_crawl_id)
        else:
            filename = os.path.join(HERE, 'fnac_products.csv')

        with open(filename) as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.products[row['identifier']] = {'brand':row['brand'].decode('utf8'),
                                                    'sku':row['sku'].decode('utf8'),
                                                    'url': row['url'].decode('utf8'),
                                                    'category': row['category'].decode('utf8'),
                                                    'image_url':row['image_url'].decode('utf8'),
                                                    'name': row['name'].decode('utf8')}

        fnac_full = os.path.join(HERE, 'fnac_full.csv')
        if os.path.exists(fnac_full):
            with open(fnac_full) as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row['identifier'] not in self.products:
                        self.products[row['identifier']] = {'brand': row['brand'].decode('utf8'),
                                                            'sku': row['sku'].decode('utf8'),
                                                            'url': row['url'].decode('utf8'),
                                                            'category': row['category'].decode('utf8'),
                                                            'image_url': row['image_url'].decode('utf8'),
                                                            'name': row['name'].decode('utf8')}

        if hasattr(self, 'prev_crawl_id'):
            meta_filename = os.path.join(DATA_DIR, 'meta/%s_meta.json-lines' % self.prev_crawl_id)
            if os.path.exists(meta_filename):
                with open(meta_filename) as f:
                    for line in f:
                        p = json.loads(line)
                        self.metadata_[p['identifier']] = {'promo_start': p['metadata'].get('promo_start'),
                                                           'promo_end': p['metadata'].get('promo_end')}

        if os.path.exists(os.path.join(HERE, 'fnac_idents.csv')):
            with open(os.path.join(HERE, 'fnac_idents.csv')) as f:
                reader = csv.reader(f)
                for row in reader:
                    self.identifiers[row[0].replace('fcom', '').replace('mp', '')] = row[0]

        yield Request(self.search_url.format(page=1), callback=self.parse_number_pages)

    def parse_number_pages(self, response):
        pages = response.xpath('//*[@class="sliderTotal"]/text()').extract()[0]
        pages = int(re.search('(\d+)', pages, re.MULTILINE).groups()[0])
        pages = (pages / 20) + 10
        self.log('{} pages found'.format(pages))

        for i in range(1, pages + 1):
            yield Request(self.search_url.format(page=i), callback=self.parse_search_results,
                          dont_filter=True)

    def extract_product_info(self, product):
        prod_url = product.xpath('.//a/@href').extract()[0]
        price_section = product.xpath('./../../following-sibling::div')
        marketplace = len(price_section.xpath('.//*[@class="seller"]')) > 0

        is_used = False
        if marketplace:
            state = product.xpath('../..//*[@class="shipping"]/ul/li[span[contains(text(), "Estado")]]/strong/text()').extract_first()
            if state and 'novo' not in state.lower():
                is_used = True

        price = price_section.xpath('.//*[@class="floatl"]//*[@class="userPrice"]/text()').extract()
        if price:
            price = price[0].replace(u'\xa0', '')
            price = extract_price_eu(price)

        promotion_price = price_section.xpath('.//*[@class="floatl"]//*[@class="oldPrice"]/text()').extract()
        if promotion_price:
            promotion_price = promotion_price[0].replace(u'\xa0', '')
            promotion_price = extract_price_eu(promotion_price)

        offers_url = None
        offers_count = 0
        offers_links = price_section.css('.OffersSumary').xpath(".//a")
        for a in offers_links:
            link_title = a.xpath("text()").extract_first().strip()
            if u'segunda' in link_title:
                continue
            if u'novo' not in link_title:
                continue
            offers_url = a.xpath("@href").extract_first()
            offers_count = a.xpath("text()").re_first(u"(?u)(\d*)\s*novo")
            offers_count = int(offers_count)

        seller = None
        seller_identifier = None
        if marketplace:
            seller = price_section.xpath('.//a[@class="seller"]/text()').extract_first().strip()
            seller_url = price_section.xpath('.//a[@class="seller"]/@href').extract_first()
            seller_identifier = get_seller_id_from_url(seller_url)

            self.seller_ids[seller.lower()] = seller_identifier

        out_stock = len(product.xpath('./..//*[@class="Nodispo"]').extract()) > 0
        dispo = product.xpath('./../..').css('.sellerInfos > li')
        if dispo:
            dispo = ' '.join(dispo.css('.Dispo-txt').xpath("text()").extract())
        else:
            dispo = ''

        exclusive_online = u'exclusivo internet' in dispo.lower()

        if marketplace:
            shipping = product.xpath('../..//*[@class="shipping"]/ul/li[span[contains(text(), "Portes")]]/strong/text()')
        else:
            shipping = product.xpath('./..//*[@class="Delivery-price"]//text()')
        if shipping:
            shipping = ''.join(shipping.extract())
            shipping = extract_price_eu(shipping)
        else:
            shipping = ''

        identifier = re.search('/mp(\d+)/', prod_url)
        if not identifier:
            identifier = re.search('/a(\d+)$', prod_url)
        if identifier:
            identifier = 'fcom' + identifier.groups()[0]
        else:
            self.log('Identifier not found {}'.format(prod_url))

        if marketplace:
            combined_identifier = identifier + '-' + seller_identifier
        else:
            combined_identifier = identifier
            combined_identifier = self.get_identifier(combined_identifier)

        result = {'url': prod_url, 'marketplace': marketplace, 'price': price,
                  'promotion_price': promotion_price, 'out_stock': out_stock,
                  'exclusive_online': exclusive_online, 'shipping': shipping,
                  'identifier': identifier,
                  'offers_url': offers_url, 'offers_count': offers_count,
                  'seller': seller, 'seller_identifier': seller_identifier,
                  'combined_identifier': combined_identifier,
                  'is_used': is_used}

        return result

    def get_product_from_cache(self, response, product_data):
        identifier = product_data['combined_identifier']
        values = self.products[identifier]
        loader = ProductLoader(item=Product(), response=response)
        loader.add_value('identifier', identifier)
        loader.add_value('brand', values['brand'].decode('utf-8'))
        loader.add_value('sku', values['sku'].decode('utf-8'))
        loader.add_value('image_url', values['image_url'])
        loader.add_value('name', values['name'])
        category = self.products[identifier]['category'].split(' > ')

        loader.add_value('category', category)
        # difference to direct
        loader.add_value('dealer', product_data['seller'])
        if product_data['shipping']:
            loader.add_value('shipping_cost', product_data['shipping'])

        loader.add_value('url', product_data['url'])
        loader.add_value('price', str(product_data['price']).replace('.', ','))

        product = Product(loader.load_item())

        product['metadata'] = SonaeMeta()
        product['metadata']['delivery_24_48'] = 'Yes'

        if product_data['exclusive_online']:
            product['metadata']['exclusive_online'] = 'Yes'

        promotion_price = product_data['promotion_price']
        if promotion_price:
            product['metadata']['promotion_price'] = str(promotion_price).replace(',', '.')

        if identifier in self.metadata_:
            prev_meta = self.metadata_[identifier]
        else:
            prev_meta = {}

        promo = promotion_price
        promo_start = prev_meta.get('promo_start')
        promo_end = prev_meta.get('promo_end')
        today = datetime.datetime.now().strftime('%Y-%m-%d')

        product['metadata']['extraction_timestamp'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
        if promo:
            product['metadata']['promo_start'] = promo_start if promo_start and not promo_end else today
            product['metadata']['promo_end'] = ''
        else:
            if promo_start:
                product['metadata']['promo_start'] = promo_start
                product['metadata']['promo_end'] = today if not promo_end else promo_end

        return product

    def parse_search_results(self, response):
        products = response.xpath('//*[@class="Article-desc"]')
        products = [p for p in products if p.xpath('.//a')]
        self.log('products found {}'.format(len(products)))

        for prod in products:
            result = self.extract_product_info(prod)
            identifier = result['combined_identifier']
            # if no "novo" offers: skip as it's a Fnac product
            if not result['marketplace'] and result['offers_count'] == 0:
                # Fnac direct product
                self.log('Fnac direct product: {}'.format(result['url']))
                continue
            # if price is seller's price and it's not second hand product
            # and there is no more than one seller and product is in cache:
            # process product from cache
            if result['marketplace'] and result['offers_count'] < 2 and identifier in self.products and not result['is_used']:
                self.log('Loading product from cache')
                self.seen.add(result['identifier'].replace('fcom', ''))
                yield self.get_product_from_cache(response, result)
            elif result['offers_count'] > 0:
                meta = response.meta.copy()
                if result['exclusive_online']:
                    meta['exclusive_online'] = True
                if identifier in self.products:
                    product_info = self.products[identifier]
                    product_info['base_identifier'] = result['identifier']
                    meta['product_info'] = product_info
                    yield Request(self.get_static_offers_url(result['url']), meta=meta,
                                  callback=self.parse_offers_static_page)
                else:
                    result['base_identifier'] = result['identifier']
                    meta['product_info'] = result
                    yield Request(result['offers_url'], meta=meta, callback=self.parse_product_with_dealers)
            else:
                # can go here if:
                # - offers_count == 0
                # and:
                # - not marketplace
                # - identifier not in products
                # which means that it's Fnac direct product
                pass

    def parse_product(self, response, stop_on_missing_price=True):
        self.log("[[TEST]] parse_product")
        
        description_field = response.xpath("//script[contains(text(), 'tc_vars')]/text()").extract_first()
        if not description_field:
            if error_msg:
                return
            raise ValueError("Could not find description field: {}".format(response.url))
        
        m = re.findall(r'tc_vars\["product_EAN"\]\s*=\s*"(\d*)"', description_field)
        sku = m[0] if m else ''

        category_01 = response.css('.Breadcrumb-list').css('.Breadcrumb-item').css('[itemprop=title]')[1].xpath('text()').extract_first()
        try:
            category_02 = response.css('.Breadcrumb-list').css('.Breadcrumb-item').css('[itemprop=title]')[2].xpath('text()').extract_first()
        except IndexError:
            category_02 = ''

        name = response.css('.ProductSummary-title').xpath("//*[@itemprop='name']/text()").extract_first().strip()
        if not name:
            raise ValueError("Name not found: {}".format(response.url))
        subtitle_1st_el = response.css('.ProductSummary-subTitle').xpath("*[1]")
        if subtitle_1st_el.xpath("name()").extract_first() == 'span':
            subname = subtitle_1st_el.xpath("text()").extract_first()
            if subname:
                name = ' '.join([name, subname])

        m = re.findall(r'tc_vars\["product_trademark"\]\s*=\s*"([^"]*)"', description_field)
        brand = m[0] if m else ''

        m = re.findall(r'tc_vars\["product_picture_url"\]\s*=\s*"([^"]*)"', description_field)
        image_url = m[0] if m else ''

        return {'category': [x for x in [category_01, category_02]], 'sku': sku,
                'name': name, 'brand': brand, 'image_url': image_url}

    def parse_product_with_dealers(self, response):
        self.log("[[TEST]] parse_product_with_dealers")

        product_info = response.meta['product_info']
        other = self.parse_product(response)
        for k in other:
            product_info[k] = other[k]

        yield Request(self.get_static_offers_url(product_info['url']),
                      callback=self.parse_offers_static_page, 
                      meta={'product_info': product_info, 
                      'exlusive_online': response.meta.get('exclusive_online')})

    def parse_offers_static_page(self, response):
        rows = response.css('#colsMP tr')
        if rows:
            rows = rows[1:]

        exclusive_online = False
        if response.meta.get('exclusive_online'):
            exclusive_online = True
        product_info = response.meta['product_info']
        base_identifier = product_info['base_identifier'].replace('mp', '')
        if not 'fcom' in base_identifier:
            base_identifier = 'fcom' + base_identifier

        self.seen.add(base_identifier.replace('fcom', ''))
        product_info = response.meta.get('product_info')
        for row in rows:
            if row.css('.fnacView'):
                self.log('Skipping Fnac direct product')
                continue
            status = row.css('td.gras').xpath('./text()').extract()
            if status and 'novo' not in status[0].lower():
                self.log('Skipping used product')
                continue

            price = row.css('.userPrice').xpath('./text()').extract()
            if not price:
                self.log('Price not found')
                continue
            else:
                price = price[0].replace(u'\xa0', '').strip()

            promotion_price = row.css('.oldPrice').xpath('./text()').extract()
            if promotion_price:
                promotion_price = extract_price_eu(promotion_price[0].replace(u'\xa0', '').strip())

            shipping_cost = row.css('.noir').xpath('./text()').extract()
            if shipping_cost:
                shipping_cost = extract_price_eu(shipping_cost[0].strip())

            dealer = row.css('.bleu_MP')
            if not dealer:
                self.log('Dealer not found')
                continue
            dealer_id = dealer.xpath('./a/@href').extract()[0].split('/')[-1]
            dealer_name = dealer.xpath('./a/strong/text()').extract()[0].strip()
        
            loader = ProductLoader(item=Product(), selector=row)
            identifier = base_identifier + '-' + dealer_id
            identifier = self.get_identifier(identifier)
            loader.add_value('identifier', identifier)
            loader.add_value('dealer', dealer_name)
            for c in ['name', 'category', 'brand', 'url', 'image_url', 'sku']:
                loader.add_value(c, product_info[c])
            loader.add_value('price', price)
            if shipping_cost:
                loader.add_value('shipping_cost', shipping_cost)

            product = loader.load_item()
            metadata = SonaeMeta()
            if exclusive_online:
                metadata['exclusive_online'] = 'Yes'

            metadata['delivery_24_48'] = 'Yes'

            if promotion_price:
                metadata['promotion_price'] = str(promotion_price)

            product['metadata'] = metadata
            if identifier in self.metadata_:
                prev_meta = self.metadata_[identifier]
            else:
                prev_meta = {}
            promo = promotion_price
            promo_start = prev_meta.get('promo_start')
            promo_end = prev_meta.get('promo_end')
            today = datetime.datetime.now().strftime('%Y-%m-%d')

            product['metadata']['extraction_timestamp'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
            if promo:
                product['metadata']['promo_start'] = promo_start if promo_start and not promo_end else today
                product['metadata']['promo_end'] = ''
            else:
                if promo_start:
                    product['metadata']['promo_start'] = promo_start
                    product['metadata']['promo_end'] = today if not promo_end else promo_end

            yield product
