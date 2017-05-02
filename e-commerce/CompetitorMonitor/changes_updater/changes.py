import csv
import json
from decimal import Decimal


class Change(object):
    """
    Abstract class for changes.
    Price changes, metadata changes and additional changes will use it as a base.
    """

    NO_CHANGE = 0
    NEW = 1
    OLD = 2
    UPDATE = 3

    def __init__(self, el_old=None, el_new=None, settings=None):
        self.el_old = el_old
        self.el_new = el_new
        self.change = {}
        self.change_type = None
        self.settings = settings or {}

    def change_data(self):
        """
        Returns a tuple with two elements.
        The first element will be the change type.
        The second element will be a dictionary that contains the change's data.
        If there's no change between the elements NO_CHANGE is returned as the code.
        """
        raise NotImplementedError()

    def format_json(self):
        """
        Json representation of the change.
        """
        raise NotImplementedError()

    def format_csv(self, hash_function=None):
        """
        CSV representation of the change

        Optional arguments:
        :param hash_function: function to use to generate a hash over the change's dict
                              and export it on the first column
        """
        raise NotImplementedError()

    @property
    def old_element(self):
        return self.el_old

    @property
    def new_element(self):
        return self.el_new


class PriceChange(Change):
    """Class to represent price changes, additions and deletions."""
    def change_data(self):
        if self.change_type is None:
            self.change = {}
            self.change_type = self.NO_CHANGE
            if self.el_old and not self.el_new:
                self.change.update(self.el_old)
                self.change['status'] = self.OLD
                self.change['old_price'] = ''
                self.change_type = self.OLD
            elif self.el_new and not self.el_old:
                self.change.update(self.el_new)
                self.change['status'] = self.NEW
                self.change['old_price'] = ''
                self.change_type = self.NEW
            elif self.el_old and self.el_new \
                    and Decimal(self.el_old.get('price') or 0) != Decimal(self.el_new.get('price') or 0):
                self.change.update(self.el_new)
                self.change['status'] = self.UPDATE
                self.change['old_price'] = self.el_old['price']
                self.change_type = self.UPDATE

        return self.change_type, self.change

    def format_csv(self, hash_function=None, export_always=False):
        status = {self.OLD: 'old', self.UPDATE: 'updated', self.NEW: 'new', self.NO_CHANGE: 'normal'}
        change_type, change = self.change_data()
        if not change and not export_always:
            return ''


        head = []
        if hash_function:
            head.append('hash')

        head += ['identifier', 'name', 'url', 'price',
                 'old_price', 'status', 'sku', 'category',
                 'brand', 'image_url', 'shipping_cost', 'stock', 'dealer']
        row = []
        if hash_function:
            row.append(hash_function(change))

        change_status = status[change.get('status', Change.NO_CHANGE)]
        if change.get('status') == self.UPDATE and self.settings.get('silent_updates') \
            and (not Decimal(self.el_old.get('price') or 0) or not Decimal(self.el_new.get('price') or 0)):
            change_status = 'normal'

        if change:
            row += [self.change.get(h, '') if h != 'status' else change_status for h in head]
        else:
            row += [self.el_new.get(h, '') if h != 'status' else change_status for h in head]

        row = [r.encode('utf8') for r in row]

        class f(object):
            res = ''

            def write(self, s):
                self.res = s.strip()

        file_ = f()
        writer = csv.writer(file_)
        writer.writerow(row)

        return file_.res


class AdditionalChange(Change):
    """Class that represents additional changes. I.E: changes to attributes different than the price."""
    def change_data(self):
        if self.change_type is None:
            self.change = {}
            self.change_type = self.NO_CHANGE
            if self.el_new and self.el_old:
                fields = self.settings.get('additional_fields') or \
                         ['identifier', 'name', 'url', 'shipping_cost', 'sku',
                          'brand', 'category', 'image_url', 'stock', 'dealer']
                product_changes = {}
                for field in fields:
                    if self.el_old.get(field) != self.el_new.get(field):
                        if field == 'sku':
                            old_sku = self.el_old.get('sku', '') or ''
                            new_sku = self.el_new.get('sku', '') or ''
                            if old_sku.lower() == new_sku.lower():
                                continue

                        if not self.el_new.get(field, '').strip():
                            if field == 'brand':
                                continue

                        product_changes[field] = (self.el_old.get(field, ''), self.el_new.get(field, ''))
                if product_changes:
                    self.change_type = self.UPDATE
                    product_data = self.el_old.copy()
                    product_data['price'] = self.el_new.get('price', '')
                    
                    self.change = {'product_data': product_data, 'changes': product_changes}

        return self.change_type, self.change

    def format_json(self):
        change_type, change = self.change_data()
        if change_type == self.NO_CHANGE:
            return ''

        return json.dumps(change)


class MetadataChange(Change):
    """Class that represents changes in the metadata."""
    def change_data(self):
        if self.change_type is None:
            self.change = {}
            self.change_type = self.NO_CHANGE
            if self.el_new and not self.el_old or \
                    (self.el_old and self.el_new and (self.el_old.get('metadata') != self.el_new.get('metadata') or
                                                          (self.el_old.get('_status', '') == 'old' and
                                                           self.el_new.get('_status', '') != 'old'))):
                self.change = {
                    'name': self.el_new.get('name'),
                    'url': self.el_new.get('url', ''),
                    'sku': self.el_new.get('sku', ''),
                    'identifier': self.el_new.get('identifier', ''),
                }
                self.change.update({'new_metadata': self.el_new.get('metadata')})
                self.change_type = self.UPDATE

        return self.change_type, self.change

    def format_json(self):
        change_type, change = self.change_data()
        if change_type == self.NO_CHANGE:
            return ''

        return json.dumps(change)

    def merge_reviews(self):
        """Merge reviews found on the old metadata into the new metadata"""
        seen = set()

        if not self.el_old or not self.el_new:
            return

        new_m = self.el_new['metadata']
        old_m = self.el_old['metadata']

        if new_m == old_m:
            return

        reviews = new_m.get('reviews', [])[:]
        for r in new_m.get('reviews', []):
            r_id = self._get_review_id(r)
            seen.add(r_id)

        for r in old_m.get('reviews', []):
            r_id = self._get_review_id(r)
            if r_id not in seen:
                reviews.append(r)
                seen.add(r_id)

        if reviews:
            self.el_new['metadata']['reviews'] = reviews

    def _get_review_id(self, rev):
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


class IdentifierChange(Change):
    """Class to represent identifier changes, this is mainly used for error detection."""
    def change_data(self):
        if self.change_type is None:
            self.change = {}
            self.change_type = self.NO_CHANGE
            if self.el_old['identifier'] != self.el_new['identifier']:
                self.change = {'old_identifier': self.el_old['identifier'],
                               'new_identifier': self.el_new['identifier']}
                self.change_type = self.UPDATE

        return self.change_type, self.change
