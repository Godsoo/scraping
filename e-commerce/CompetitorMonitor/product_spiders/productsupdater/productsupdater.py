# -*- encoding: utf-8
import sys
import os
import csv
from decimal import Decimal
from datetime import datetime, date
from collections import defaultdict

from sqlalchemy import and_
from sqlalchemy import desc, func

path = os.path.abspath(os.path.join(__file__, '../../..'))

path = os.path.join(path, 'productspidersweb')

sys.path.append(path)

from productspidersweb.models import Crawl, Spider, DailyErrors, SpiderError, AdditionalFieldsGroup

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


class ProductsUpdater(object):
    def __init__(self, db_session, metadata_updater=None):
        self.db_session = db_session
        self.metadata_updater = metadata_updater

    def _get_current_time(self):
        return self.db_session.execute(func.current_timestamp()).scalar()

    def start_crawl(self, spider_name):
        spider = self.db_session.query(Spider)\
                                .filter(Spider.name == spider_name).one()

        crawl = self.db_session.query(Crawl).join(Spider)\
                               .filter(and_(Spider.id == spider.id,
                                            Crawl.status == 'scheduled_on_worker')).order_by(desc(Crawl.id)).first()
        if not crawl:
            return None

        current_time = self._get_current_time()
        crawl.status = 'running'
        crawl.start_time = current_time
        self.db_session.add(crawl)
        self.db_session.commit()

        return crawl

    def set_finished(self, crawl_id):
        crawl = self.db_session.query(Crawl).get(crawl_id)
        crawl.status = 'processing_finished'
        crawl.end_time = self._get_current_time()
        self.db_session.add(crawl)

        spider = self.db_session.query(Spider).get(crawl.spider_id)
        spider.rerun = False
        self.db_session.add(spider)
        self.db_session.commit()

    def set_with_errors(self, crawl_id, errors):
        crawl = self.db_session.query(Crawl).get(crawl_id)
        crawl.status = 'errors_found'
        crawl.end_time = self._get_current_time()
        # crawl.error_message = '\n'.join(errors).decode('utf-8', 'ignore')
        self.db_session.add(crawl)
        # Daily errors
        spider = self.db_session.query(Spider).get(crawl.spider_id)
        if (not spider.error or (spider.error and spider.error.status == 'fixed')) and not spider.rerun:
            day_errors = self.db_session.query(DailyErrors).filter(DailyErrors.date == date.today()).first()
            if day_errors:
                day_errors.possible += 1
            else:
                day_errors = DailyErrors(date=date.today())
                day_errors.possible = 1
            self.db_session.add(day_errors)
        spider.rerun = True
        self.db_session.add(spider)
        self.db_session.commit()

    def merge_reviews(self, old_m, new_m):
        def get_review_id(rev):
            if 'review_id' in rev:
                ids = ['review_id']
            else:
                ids = ['sku', 'rating', 'full_text', 'date']

            rev_id = ''
            for x in ids:
                s_id = rev.get(x, '')
                if type(s_id) not in [str, unicode]:
                    s_id = str(s_id)

                s_id = s_id.encode('utf8')
                rev_id += ':' + s_id

            return rev_id

        seen = set()
        reviews = new_m.get('reviews', [])[:]
        for r in new_m.get('reviews', []):
            r_id = get_review_id(r)
            seen.add(r_id)

        for r in old_m.get('reviews', []):
            r_id = get_review_id(r)
            if r_id not in seen:
                reviews.append(r)
                seen.add(r_id)

        return reviews

    def merge_products(self, old_products, products, meta_db=None, crawl_id=None, old_crawl_id=None):
        old_products_idx = defaultdict(list)
        products_idx = defaultdict(list)

        i = 0
        for idx, prods in [[old_products_idx, old_products], [products_idx, products]]:
            for product in prods:
                ident, sku, name = product.get('identifier', ''), product.get('sku', ''), product['name'].lower()
                if meta_db:
                    if i == 0:
                        metadata = meta_db.get_metadata(product.get('identifier'), old_crawl_id)
                    else:
                        metadata = meta_db.get_metadata(product.get('identifier'), crawl_id)
                else:
                    metadata = product.get('metadata', {})

                universal_ident = metadata.get('universal_identifier')
                if universal_ident:
                    idx['universal_ident:%s' % universal_ident].append(product)
                if ident:
                    idx['ident:%s' % ident].append(product)
                if sku:
                    idx['sku:%s' % sku].append(product)

                idx['name:%s' % name].append(product)
            i += 1

        processed_ids = set(x['identifier'] for x in products)

        for i, product in enumerate(old_products):
            metadata = meta_db.get_metadata(product.get('identifier'), old_crawl_id)
            r = self._get_matching_product(product, products_idx, old_products_idx, use_u_ident=True, metadata=metadata)
            if not r:
                if product['identifier'] in processed_ids:
                    pass
                else:
                    products.append(product)
                    meta_db.set_metadata(product['identifier'], crawl_id, metadata)
                    processed_ids.add(product['identifier'])
            elif metadata.get('universal_identifier'):
                r['identifier'] = product['identifier']


            if r and 'reviews' in metadata:
                new_metadata = meta_db.get_metadata(product.get('identifier'), crawl_id)
                metadata['reviews'] = self.merge_reviews(metadata, new_metadata)
                meta_db.set_metadata(product['identifier'], crawl_id, metadata)

            if i % 1000 == 0:
                meta_db.db_session.flush()

        meta_db.db_session.flush()

        return products

    def get_changes(self, f):
        reader = csv.DictReader(f)

        change_types = {'new': 'addition',
                        'removed': 'deletion',
                        'old': 'deletion',
                        'updated': 'update',
                        'normal': 'silent_update'}

        for change in reader:
            if change['status'] in ['new', 'removed', 'old']:

                yield {'url': change['url'],
                       'name': change['name'],
                       'sku': change['sku'],
                       'price': Decimal(change['price'] or 0),
                       'change_type': change_types[change['status']],
                       'category': change.get('category', ''),
                       'brand': change.get('brand', ''),
                       'image_url': change.get('image_url', ''),
                       'shipping_cost': change.get('shipping_cost', ''),
                       'identifier': change.get('identifier', ''),
                       'dealer': change.get('dealer', ''),
                       'stock': int(change.get('stock')) if 'stock' in change and change['stock'] != '' else ''}

            elif change['status'] in ['updated', 'normal']:
                yield {'url': change['url'],
                       'name': change['name'],
                       'sku': change['sku'],
                       'price': Decimal(change['price'] or 0),
                       'old_price': Decimal(change['old_price'] or 0),
                       'change_type': change_types[change['status']],
                       'difference': Decimal(change.get('price') or 0) - Decimal(change.get('old_price') or 0),
                       'category': change.get('category', ''),
                       'brand': change.get('brand', ''),
                       'image_url': change.get('image_url', ''),
                       'shipping_cost': change.get('shipping_cost', ''),
                       'identifier': change.get('identifier', ''),
                       'dealer': change.get('dealer', ''),
                       'stock': int(change.get('stock')) if 'stock' in change and change['stock'] != '' else ''}

    def get_errors(self, f):
        reader = csv.DictReader(f)

        for error in reader:
            yield {'message': error['error'].decode('utf-8'), 'code': error.get('code', '')}

    def compute_changes(self, current_crawl_id, old_products, products, silent_updates=False, set_crawl_data=True):
        current_crawl = self.db_session.query(Crawl).get(current_crawl_id)

        previous_crawl = self.db_session.query(Crawl)\
                                        .filter(and_(Crawl.spider_id == current_crawl.spider_id,
                                                     Crawl.id < current_crawl_id))\
                                        .order_by(desc(Crawl.crawl_date)).first()


        changes = []

        additions = []
        deletions = []
        updates = []

        old_products_idx = defaultdict(list)
        products_idx = defaultdict(list)

        for idx, prods in [[old_products_idx, old_products], [products_idx, products]]:
            for product in prods:
                ident, sku, name = product['identifier'], product['sku'], product['name'].lower()
                if ident:
                    idx['ident:%s' % ident].append(product)
                if sku:
                    idx['sku:%s' % sku].append(product)

                idx['name:%s' % name].append(product)

        # check for old products and updated products
        if previous_crawl:
            for product in old_products:

                new_product = self._get_matching_product(product, products_idx, old_products_idx)

                if not new_product:
                    change = {'name': product['name'], 'price': product['price'],
                              'change_type': 'deletion',
                              'url': product['url'], 'sku': product['sku'],
                              'category': product.get('category', ''),
                              'brand': product.get('brand', ''),
                              'image_url': product.get('image_url', ''),
                              'shipping_cost': product.get('shipping_cost', ''),
                              'identifier': product.get('identifier', ''),
                              'stock': product.get('stock', ''),
                              'dealer': product.get('dealer', '')}

                    changes.append(change)
                    deletions.append(change)

                else:  # check for price changes
                    old_price = Decimal(product['price'] or 0)
                    new_price = Decimal(new_product['price'] or 0)
                    if old_price != new_price:
                        difference = new_price - old_price
                        change_type = 'update'
                        if silent_updates and (not new_price or not old_price):
                            change_type = 'silent_update'

                        change = {'name': new_product['name'], 'price': new_price, 'old_price': old_price,
                                  'change_type': change_type, 'difference': difference,
                                  'url': new_product['url'], 'sku': product['sku'],
                                  'category': new_product.get('category', ''),
                                  'brand': new_product.get('brand', ''),
                                  'image_url': new_product.get('image_url', ''),
                                  'shipping_cost': new_product.get('shipping_cost', ''),
                                  'identifier': new_product.get('identifier', ''),
                                  'stock': new_product.get('stock', ''),
                                  'dealer': new_product.get('dealer', '')}

                        changes.append(change)
                        updates.append(change)

        # check for new products
        for product in products:
            old_product = None
            if previous_crawl:
                old_product = self._get_matching_product(product, old_products_idx, products_idx)

            if not old_product:
                change = {'name': product['name'], 'price': product['price'],
                          'change_type': 'addition',
                          'url': product['url'], 'sku': product['sku'],
                          'category': product.get('category', ''),
                          'brand': product.get('brand', ''),
                          'image_url': product.get('image_url', ''),
                          'shipping_cost': product.get('shipping_cost', ''),
                          'identifier': product.get('identifier', ''),
                          'stock': product.get('stock', ''),
                          'dealer': product.get('dealer', '')}

                changes.append(change)
                additions.append(change)

        if set_crawl_data:
            current_crawl.products_count = len(products)
            current_crawl.changes_count = len(changes)
            current_crawl.additions_count = len(additions)
            current_crawl.deletions_count = len(deletions)
            current_crawl.updates_count = len(updates)

            self.db_session.add(current_crawl)
            self.db_session.commit()

        return changes, additions, deletions, updates

    def compute_metadata_changes(self, current_crawl_id, old_products, products, meta_db, crawl_id, old_crawl_id):
        current_crawl = self.db_session.query(Crawl).get(current_crawl_id)

        previous_crawl = self.db_session.query(Crawl)\
                                        .filter(and_(Crawl.spider_id == current_crawl.spider_id,
                                                     Crawl.id < current_crawl_id))\
                                        .order_by(desc(Crawl.crawl_date)).first()


        changes = []

        old_products_idx = defaultdict(list)
        products_idx = defaultdict(list)

        i = 0
        for idx, prods in [[old_products_idx, old_products], [products_idx, products]]:
            for product in prods:
                ident, sku, name = product.get('identifier', ''), product.get('sku', ''), product['name'].lower()
                if meta_db:
                    if i == 0:
                        metadata = meta_db.get_metadata(product.get('identifier'), old_crawl_id)
                    else:
                        metadata = meta_db.get_metadata(product.get('identifier'), crawl_id)
                else:
                    metadata = product.get('metadata', {})

                universal_ident = metadata.get('universal_identifier')
                if universal_ident:
                    idx['universal_ident:%s' % universal_ident].append(product)
                if ident:
                    idx['ident:%s' % ident].append(product)
                if sku:
                    idx['sku:%s' % sku].append(product)

                idx['name:%s' % name].append(product)

            i += 1

        if previous_crawl:
            for product in old_products:
                new_meta = meta_db.get_metadata(product.get('identifier'), crawl_id)
                new_product = self._get_matching_product(product, products_idx, old_products_idx, use_u_ident=True,
                                                         metadata=new_meta)

                if not new_product:
                    change = {
                        'name': product['name'],
                        'url': product.get('url', ''),
                        'sku': product['sku'],
                        'identifier': product.get('identifier', ''),
                        'insert': [],
                        'update': [],
                        'delete': [{'field': ''}]
                    }

                    changes.append(change)

                else:

                    old_meta = meta_db.get_metadata(product.get('identifier'), old_crawl_id)

                    if old_meta != new_meta:
                        identifier = product.get('identifier') \
                            if new_meta.get('universal_identifier') \
                            else new_product.get('identifier')

                        change = {
                            'name': new_product['name'],
                            'url': new_product.get('url', ''),
                            'sku': new_product['sku'],
                            'identifier': identifier,
                        }
                        change.update({'new_metadata': new_meta})

                        changes.append(change)

        for product in products:
            old_product = None
            new_meta = meta_db.get_metadata(product.get('identifier'), crawl_id)
            if previous_crawl:
                old_product = self._get_matching_product(product, old_products_idx, products_idx, use_u_ident=True,
                                                         metadata=new_meta)

            if not old_product:
                change = {
                    'name': product['name'],
                    'url': product.get('url', ''),
                    'sku': product['sku'],
                    'identifier': product.get('identifier', ''),
                }
                meta_changes = self.metadata_updater.get_changes({}, new_meta)
                change.update(meta_changes)
                changes.append(change)

        return changes

    def compute_additional_changes(self, current_crawl_id, old_products, products, set_crawl_data=True):
        current_crawl = self.db_session.query(Crawl).get(current_crawl_id)
        spider = self.db_session.query(Spider).get(current_crawl.spider_id)
        fields = ['identifier', 'name', 'url', 'shipping_cost', 'sku',
                  'brand', 'category', 'image_url', 'stock', 'dealer']
        if spider.additional_fields_group_id:
            additional_fields_group = self.db_session.query(AdditionalFieldsGroup)\
                                          .get(spider.additional_fields_group_id)

            # if weekly updates enabled, then choose sunday
            if not additional_fields_group.enable_weekly_updates or datetime.now().weekday() != 6:
                fields = ['identifier', 'shipping_cost', 'sku', 'stock', 'dealer']
                if additional_fields_group.enable_url:
                    fields.append('url')
                if additional_fields_group.enable_image_url:
                    fields.append('image_url')
                if additional_fields_group.enable_brand:
                    fields.append('brand')
                if additional_fields_group.enable_category:
                    fields.append('category')
                if additional_fields_group.enable_name:
                    fields.append('name')

        old_products_idx = defaultdict(list)
        products_idx = defaultdict(list)

        for idx, prods in [[old_products_idx, old_products], [products_idx, products]]:
           for product in prods:
               ident, sku, name = product.get('identifier', ''), product.get('sku', ''), product['name'].lower()
               if ident:
                   idx['ident:%s' % ident].append(product)
               if sku:
                   idx['sku:%s' % sku].append(product)

               idx['name:%s' % name].append(product)

        changes = []
        for product in old_products:
            new_product = self._get_matching_product(product, products_idx, old_products_idx)
            if not new_product:
                continue

            product_changes = {}
            for field in fields:
                if product.get(field) != new_product.get(field):
                    if field == 'sku':
                        old_sku = product.get('sku', '') or ''
                        new_sku = new_product.get('sku', '') or ''
                        if old_sku.lower() == new_sku.lower():
                            continue
                    product_changes[field] = (product.get(field, ''), new_product.get(field, ''))

            if product_changes:
                changes.append({'product_data': product, 'changes': product_changes})

        if set_crawl_data:
            current_crawl.additional_changes_count = len(changes)
            self.db_session.add(current_crawl)
            self.db_session.commit()

        return changes


    def _get_matching_product(self, product, products, same_crawl_products, use_u_ident=False, metadata=None):
        matching_products = []
        if use_u_ident and metadata.get('universal_identifier'):
            uid = metadata.get('universal_identifier')
            matching_products_uident = products.get('universal_ident:%s' % uid)
            if matching_products_uident:
                matching_products += matching_products_uident

        # search for the identifier
        if product.get('identifier'):
            matching_products_ident = products.get('ident:%s' % product['identifier'])
            if matching_products_ident:
                m = []
                for p in matching_products_ident:
                    if p['name'] != product['name']:
                        prods_ident = same_crawl_products.get('ident:%s' % p['identifier'])
                        found_same_prod = False
                        for prod_ident in prods_ident:
                            if prod_ident['name'] == p['name']:
                                found_same_prod = True
                        if not found_same_prod:
                            m.append(p)
                    else:
                        m.append(p)

                matching_products += m

        if not matching_products:
            matching_products += products['name:%s' % product['name'].lower()]
            if product.get('identifier'):
                matching_products = [pr for pr in matching_products
                                     if not pr.get('identifier') or pr['identifier'] == product['identifier']]

        if not matching_products:
            return None

        diffs = [{'diff': abs(Decimal(pr['price'] or 0) - Decimal(product['price'] or 0)),
                  'product': pr}
                 for pr in matching_products]

        matching_product = min(diffs, key=lambda x: x['diff'])

        return matching_product['product']
