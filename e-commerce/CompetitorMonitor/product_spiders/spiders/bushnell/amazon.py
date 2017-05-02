import os
import csv
from decimal import Decimal

from scrapy.http import Request, HtmlResponse

from product_spiders.base_spiders.amazonspider2.items import AmazonProductLoader, AmazonProduct
from product_spiders.base_spiders.amazonspider2 import BaseAmazonSpider
from product_spiders.base_spiders.amazonspider2.scraper import AmazonScraper, AmazonUrlCreator, \
    AmazonScraperProductDetailsException
from product_spiders.utils import extract_price2uk


HERE = os.path.abspath(os.path.dirname(__file__))


MAX_SKU_LEN = 255


class AmazonSpider(BaseAmazonSpider):
    name = 'bushnell-amazon.com'
    allowed_domains = ['amazon.com']

    user_agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.9; rv:24.0) Gecko/20100101 Firefox/24.0'

    domain = 'amazon.com'
    type = 'category'
    only_buybox = True
    do_retry = True
    collect_products_with_no_dealer = True
    parse_options = True
    collect_reviews = True
    semicolon_in_identifier = False
    _max_pages = 10
    model_as_sku = True

    bushnell_products = {}

    def get_category_url_generator(self):
        with open(os.path.join(HERE, 'bushnell_products.csv')) as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.bushnell_products[row['SKU'].upper().strip()] = row

        yield ('http://www.amazon.com/s/ref=nb_sb_noss?url=srs%3D2529087011%26search-alias%3Dspecialty-aps&field-keywords', 'Bushnell')
        yield ('http://www.amazon.com/s/ref=sr_in_v_p_89_30?fst=as%3Aoff&rh=n%3A172282%2Cn%3A!493964%2Cn%3A502394%2Cn%3A499320%2Cn%3A297842%2Cp_89%3AVortex+Optics|Vortex&bbn=297842&ie=UTF8&qid=1464013939&rnid=2528832011', 'Vortex')
        yield ('http://www.amazon.com/s/ref=sr_in_v_p_89_16?fst=as%3Aoff&rh=n%3A3375251%2Cn%3A!3375301%2Cn%3A10971181011%2Cn%3A706813011%2Cn%3A13364359011%2Cn%3A162017011%2Cn%3A162020011%2Cn%3A3226124011%2Cp_89%3AVortex+Optics|Vortex&bbn=3226124011&ie=UTF8&qid=1464014088&rnid=2528832011', 'Vortex')
        yield ('http://www.amazon.com/s/ref=sr_in_v_p_89_13?fst=as%3Aoff&rh=n%3A3375251%2Cn%3A!3375301%2Cn%3A10971181011%2Cn%3A706813011%2Cn%3A13364359011%2Cn%3A162017011%2Cn%3A3168061%2Cp_89%3AVortex+Optics|Vortex&bbn=3168061&ie=UTF8&qid=1464014353&rnid=2528832011', 'Vortex')
        yield ('http://www.amazon.com/s/ref=sr_in_l_p_89_14?fst=as%3Aoff&rh=n%3A172282%2Cn%3A!493964%2Cn%3A502394%2Cn%3A499320%2Cn%3A297842%2Cp_89%3ALeupold&bbn=297842&ie=UTF8&qid=1464014176&rnid=2528832011', 'Leupold')
        yield ('http://www.amazon.com/s/ref=sr_in_l_p_89_16?fst=as%3Aoff&rh=n%3A3375251%2Cn%3A!3375301%2Cn%3A10971181011%2Cn%3A706813011%2Cn%3A13364359011%2Cn%3A162017011%2Cn%3A162020011%2Cn%3A3226124011%2Cp_89%3ALeupold&bbn=3226124011&ie=UTF8&qid=1464014456&rnid=2528832011', 'Leupold')
        yield ('http://www.amazon.com/s/ref=sr_in_l_p_89_6?fst=as%3Aoff&rh=n%3A3375251%2Cn%3A!3375301%2Cn%3A10971181011%2Cn%3A706813011%2Cn%3A13364359011%2Cn%3A162017011%2Cn%3A3168061%2Cp_89%3ALeupold&bbn=3168061&ie=UTF8&qid=1464014544&rnid=2528832011', 'Leupold')
        yield ('http://www.amazon.com/s/ref=sr_in_n_p_89_28?fst=as%3Aoff&rh=n%3A172282%2Cn%3A!493964%2Cn%3A502394%2Cn%3A499320%2Cn%3A297842%2Cp_89%3ANikon&bbn=297842&ie=UTF8&qid=1464014755&rnid=2528832011', 'Nikon')
        yield ('http://www.amazon.com/s/ref=sr_in_-2_p_89_32?fst=as%3Aoff&rh=n%3A3375251%2Cn%3A!3375301%2Cn%3A10971181011%2Cn%3A706813011%2Cn%3A13364359011%2Cn%3A162017011%2Cn%3A162020011%2Cn%3A3226124011%2Cp_89%3ANikon&bbn=3226124011&ie=UTF8&qid=1464014794&rnid=2528832011', 'Nikon')
        yield ('http://www.amazon.com/s/ref=sr_in_n_p_89_8?fst=as%3Aoff&rh=n%3A3375251%2Cn%3A!3375301%2Cn%3A10971181011%2Cn%3A706813011%2Cn%3A13364359011%2Cn%3A162017011%2Cn%3A3168061%2Cp_89%3ANikon&bbn=3168061&ie=UTF8&qid=1464014883&rnid=2528832011', 'Nikon')

    def construct_product(self, *args, **kwargs):
        product = super(AmazonSpider, self).construct_product(*args, **kwargs)
        if product.get('sku'):
            bushnell_product = self.bushnell_products.get(product['sku'].upper().strip(), None)
            if bushnell_product:
                product['category'] = bushnell_product['Class']
                self.log('Extracts category "%s" from bushnell file, URL: %s' % (product['category'], product['url']))
        return product

            
    def __construct_product(self, item, meta=None, use_seller_id_in_identifier=None):
        """
        Constructs `Product` instance from dict
        """
        if use_seller_id_in_identifier is None:
            if self.all_sellers:
                use_seller_id_in_identifier = True
            else:
                use_seller_id_in_identifier = False

        if meta and 'item' in meta:
            search_item = meta['item']
        elif meta and 'search_item' in meta:
            search_item = meta['search_item']
        else:
            search_item = self.current_search_item

        loader = AmazonProductLoader(item=AmazonProduct(), response=HtmlResponse(''))
        necessary_fields = ['name']
        optional_fields = ['sku', 'image_url', 'brand', 'stock']
        fields_from_search_item = ['sku', 'category', 'brand', 'identifier']

        synonym_fields = {
            'vendor': 'dealer',
        }

        identifier = item['identifier'] if self.use_amazon_identifier else search_item.get('identifier')
        if self.semicolon_in_identifier and \
                identifier and \
                self.use_amazon_identifier and \
                not identifier.startswith(':'):
            identifier = ':' + identifier

        if identifier and use_seller_id_in_identifier and item.get('seller_identifier'):
            identifier += ':' + item['seller_identifier']

        loader.add_value('identifier', identifier)

        for field in necessary_fields:
            loader.add_value(field, item[field])

        if item['price'] is not None:
            try:
                if type(item['price']) == tuple or type(item['price']) == list:
                    item['price'] = item['price'][0]
                price = extract_price2uk(item['price']) if not isinstance(item['price'], Decimal) else item['price']
            except Exception, e:
                self.log('ERROR: extracting price => PRICE: %s' % repr(item['price']))
                raise e
        else:
            price = Decimal('0')
        price = self.transform_price(price)
        loader.add_value('price', price)

        if item.get('asin') and item.get('seller_identifier'):
            loader.add_value(
                'url',
                AmazonUrlCreator.build_url_from_asin_and_dealer_id(
                    self.domain,
                    item['asin'],
                    item['seller_identifier']
                )
            )
        elif item.get('asin'):
            loader.add_value(
                'url',
                AmazonUrlCreator.build_url_from_asin(
                    self.domain,
                    item['asin']
                )
            )
        elif self.use_amazon_identifier:
            loader.add_value(
                'url',
                AmazonUrlCreator.build_url_from_asin(
                    self.domain,
                    item['identifier']
                )
            )
        elif item.get('url'):
            loader.add_value('url', item['url'])

        # take sku from model if configured to do so
        if item.get('model') and self.model_as_sku:
            model = item['model']
            if len(model) > MAX_SKU_LEN:
                model = model[:252] + '...'

            loader.add_value('sku', model)

        # pick search item
        # BSM simple run
        for field in optional_fields:
            if field in item and item[field]:
                loader.add_value(field, item[field])
            elif field in fields_from_search_item and search_item and field in search_item:
                if not loader.get_output_value(field):
                    loader.add_value(field, search_item[field])

        # category
        category = None
        if 'category' in item and item['category']:
            category = item['category']
        elif 'category' in fields_from_search_item and search_item and 'category' in search_item:
            category = search_item['category']
        elif self.type == 'category':
            if meta and meta.get('category'):
                category = meta['category']
            elif self.current_category:
                category = self.current_category

        if loader.get_output_value('sku'):
            bushnell_product = self.bushnell_products.get(loader.get_output_value('sku').upper().strip(), None)
            if bushnell_product:
                category = bushnell_product['Class']
                self.log('Extracts category "%s" from bushnell file, URL: %s' % (category, loader.get_output_value('url')))

        if category:
            if isinstance(category, list):
                for cat in category:
                    loader.add_value('category', cat)
            else:
                loader.add_value('category', category)
        else:
            loader.add_value('category', '')

        if item.get('shipping_cost', None):
            loader.add_value(
                'shipping_cost',
                extract_price2uk(item['shipping_cost'])
                if not isinstance(item['shipping_cost'], Decimal) else item['shipping_cost']
            )

        for synonym_field, field in synonym_fields.items():
            if synonym_field in item:
                value = item[synonym_field]
                loader.add_value(field, value)

        product = loader.load_item()
        return product
