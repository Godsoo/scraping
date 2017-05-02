class MetadataUpdater(object):
    """Class in charge of computing changes for metadata instances of products. """

    def __init__(self, metadata_rules=None):
        if not metadata_rules:
            metadata_rules = {}
        self.metadata_rules = metadata_rules

    def get_changes(self, old_meta, new_meta):
        """ Given the old and new instances of metadata returns the changes between them
            using the metadata rules passed in the constructor """

        inserts, updates, deletes = [], [], []
        total_fields = set(old_meta).union(new_meta)
        if 'universal_identifier' in total_fields:
            total_fields.remove('universal_identifier')

        for field in total_fields:
            meta_rules = self.metadata_rules.get(field)
            ids = None
            if meta_rules:
                ids = meta_rules.get('id')
                if type(ids) == str:
                    if not ids:
                        ids = None
                    else:
                        ids = [ids]

            if ids is None:
                # ids not provided, use default
                if type(old_meta.get(field)) != list and type(new_meta.get(field)) != list:
                    ids = None
                else:
                    old_meta_field_ids = self._get_field_list_common_keys(field, old_meta)
                    new_meta_field_ids = self._get_field_list_common_keys(field, new_meta)

                    ids = old_meta_field_ids.intersection(new_meta_field_ids)

            # TODO: generalize
            if field == 'reviews':
                if old_meta.get('reviews') and old_meta['reviews'][0].get('review_id') and \
                    new_meta.get('reviews') and new_meta['reviews'][0].get('review_id'):
                    new_ids = ['review_id']
                else:
                    new_ids = ['sku', 'rating', 'full_text', 'date']
            else:
                new_ids = (list(ids or []) or [])[:]

            inserts += self._get_inserts(field, new_ids, old_meta, new_meta)
            deletes += self._get_deletes(field, new_ids, old_meta, new_meta)
            updates += self._get_updates(field, new_ids, old_meta, new_meta)

        return {'insert': inserts, 'update': updates, 'delete': deletes, 'new_metadata': new_meta}

    def _get_field_list_common_keys(self, field, meta):
        meta_field_ids = set()
        rows = meta.get(field, [])
        if rows:
            meta_field_ids = set(rows[0])
        for row in meta.get(field, []):
            meta_field_ids = meta_field_ids.intersection(set(row))

        return meta_field_ids

    def _get_inserts(self, field, ids, old_meta, new_meta):
        """
        >>> updater = MetadataUpdater()
        >>> updater._get_inserts('mts_stock_code', set([]), {}, {'mts_stock_code': '1956515HTOCF2'})
        [{'field': 'mts_stock_code', 'value': '1956515HTOCF2'}]
        """
        inserts = []
        if not ids:
            if field not in old_meta and field in new_meta:
                inserts.append({'field': field, 'value': new_meta[field]})

        elif type(old_meta.get(field, [])) == list and type(new_meta.get(field, [])) == list:
            old_data = old_meta.get(field, [])
            new_data = new_meta.get(field, [])

            for data in new_data:
                matching_field = self._get_matching_field(old_data, ids, data)
                if matching_field is None:
                    inserts.append({'field': field, 'value': data})

        return inserts

    def _get_deletes(self, field, ids, old_meta, new_meta):
        deletes = []
        if not ids:
            if field not in new_meta and field in old_meta:
                deletes.append({'field': field, 'value': old_meta[field]})

        else:
            old_data = old_meta.get(field, [])
            new_data = new_meta.get(field, [])

            for data in old_data:
                matching_field = self._get_matching_field(new_data, ids, data)
                if matching_field is None:
                    deletes.append({'field': field, 'value': data})

        return deletes

    def _get_updates(self, field, ids, old_meta, new_meta):
        updates = []
        if field in old_meta and field in new_meta:
            if not isinstance(old_meta[field], list) and not isinstance(new_meta[field], list):
                if old_meta[field] != new_meta[field]:
                    updates.append({'field': field, 'old_value': old_meta[field], 'value': new_meta[field]})
            # updates for reviews only. Use if on "field == 'reviews'" and "'review_id' in ids"
            # also add tests
            elif field == 'reviews' and 'review_id' in ids:
                old_data = old_meta.get(field, [])
                new_data = new_meta.get(field, [])

                for data in old_data:
                    matching_field = self._get_matching_field(new_data, ids, data)
                    if matching_field is not None and data != matching_field:
                        updates.append({'field': field, 'value': matching_field})

        return updates

    def _get_matching_field(self, search_rows, ids, field_row):
        for row in search_rows:
            if all([field_row.get(i) == row.get(i) for i in ids]):
                return row

        return None
