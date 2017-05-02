import csv
import copy
import os
import json
import shutil
import tempfile
import locale

from join import SortedJoin, JoinFunction, CompositeJoinFunction
from export import Exporter
from stats import ChangesStats, AdditionalChangesStats, MetadataChangesStats
from datafiles import sort_products_file, sort_metadata_file, remove_non_unique_hashes, \
    SortedFile, CSVReader, JsonLinesReader
from changes import PriceChange, AdditionalChange, MetadataChange, IdentifierChange
from validation.additional_changes import MaxLengthValidator, SKUChangeValidator
from validation.changes import PriceChangeValidator
from validation.identifier_changes import IdentifierChangeValidator
from validation.metadata_changes import ImmutableMetadataValidator
from validation.stats_validator import AdditionalChangesValidator, ChangesValidator, MetadataChangesValidator
from validation.duplicate_identifiers import DuplicateIdentifierValidator
from reviews import MergeReviews
from changes import Change
from hashing import ProductHash
from duplicate_product_picker import remove_duplicates, remove_duplicates_meta


class Counter(object):
    def __init__(self, result_filter):
        self._count = 0
        self.result_filter = result_filter

    def process_result(self, result):
        if self.result_filter(result):
            self._count += 1

    @property
    def count(self):
        return self._count


def export_status(status, result):
    if result.change_data()[1].get('status', Change.NO_CHANGE) == status:
        return result.format_csv(export_always=True)
    else:
        return ''


def to_csv(r):
    row = [x.encode('utf8') for x in r]
    class f(object):
        res = ''

        def write(self, s):
            self.res = s.strip()

    file_ = f()
    writer = csv.writer(file_)
    writer.writerow(row)

    return file_.res


class ChangesUpdater(object):
    changes_validators = [PriceChangeValidator]
    additional_changes_validators = [MaxLengthValidator]
    metadata_changes_validators = [ImmutableMetadataValidator]

    def __init__(self, settings=None):
        self.settings = settings or {}
        max_length = {'sku': 255, 'category': 1024,
                      'name': 1024, 'url': 1024,
                      'brand': 100, 'image_url': 1024,
                      'identifier': 255, 'dealer': 255}
        defaults = [('max_price_percentage_change', ''),
                    ('max_additions', '10.0'),
                    ('max_deletions', '10.0'),
                    ('max_updates', '10.0'),
                    ('max_additional_to_empty', '10.0'),
                    ('max_image_url_changes', '10.0'),
                    ('max_category_changes', ''),
                    ('max_out_stock', ''),
                    ('immutable_metadata', ''),
                    ('fields_max_length', max_length),
                    ('collect_reviews', ''),
                    ('silent_updates', False),
                    ('additional_fields', []),
                    ('ignore_additional_changes', []),
                    ('max_matched_deletions', '5.0'),
                    ('max_sku_changes', '50.0'),
                    ('ignore_identifier_changes', False)]

        for k, v in defaults:
            if k not in self.settings:
                self.settings[k] = v

    def _detect_identifier_changes(self, folder_path, all_products_path, new_products_path,
                                   additions_path, errors_exporter, identifier_changes_path):
        if os.path.exists(all_products_path):
            all_f = SortedFile(all_products_path, sort_products_file, reader=CSVReader)
            new_products_f = SortedFile(new_products_path, sort_products_file, reader=CSVReader)
            deletions_path = os.path.join(folder_path, 'deletions.csv')
            deletions = open(deletions_path, 'w')
            total_additions_path = os.path.join(folder_path, 'total_additions.csv')
            total_additions = open(total_additions_path, 'w')

            sorted_join = SortedJoin(all_f, new_products_f)
            header = 'identifier,name,url,price,old_price,status,sku,category' \
                     ',brand,image_url,shipping_cost,stock,dealer'

            deletions_exporter = Exporter(output_file=deletions, header=header,
                                          format_func=lambda result: export_status(Change.OLD, result))
            additions_exporter = Exporter(output_file=total_additions, header=header,
                                          format_func=lambda result: export_status(Change.NEW, result))

            join_function1 = JoinFunction(PriceChange, [deletions_exporter, additions_exporter],
                                          settings=self.settings)
            sorted_join.full_join(join_function1, lambda x, y: locale.strcoll(x['identifier'], y['identifier']))
            deletions.close()
            total_additions.close()
            add_temp = tempfile.mktemp()
            add_temp_f = open(add_temp, 'w')
            total_additions = SortedFile(total_additions_path, sort_products_file, reader=CSVReader)
            additions = SortedFile(additions_path, sort_products_file, reader=CSVReader)
            real_additions_exporter = Exporter(output_file=add_temp_f, header=header,
                                               format_func=lambda result: export_status(Change.NO_CHANGE, result))
            join_func = JoinFunction(PriceChange, [real_additions_exporter], settings=self.settings)

            sorted_join = SortedJoin(total_additions, additions)
            sorted_join.inner_join(join_func, lambda x, y: locale.strcoll(x['identifier'], y['identifier']))

            add_temp_f.close()
            shutil.copy(add_temp, additions_path)

            temp_ = tempfile.mktemp()
            sort_products_file(deletions_path, temp_, hash_func=ProductHash.hash)
            remove_non_unique_hashes(temp_)
            shutil.move(temp_, deletions_path)

            deletions = SortedFile(deletions_path,
                                   lambda x, y: shutil.copy(x, y),
                                   reader=CSVReader)
            additions = SortedFile(additions_path,
                                   lambda x, y: sort_products_file(x, y, hash_func=ProductHash.hash),
                                   reader=CSVReader)
            sorted_join = SortedJoin(deletions, additions)
            ident_changes = open(identifier_changes_path, 'w')

            def fmt(r):
                return to_csv([r.new_element['name'], r.new_element['identifier'],
                               r.new_element['url'], r.old_element['identifier'], r.old_element['url']])

            identifier_exporter = Exporter(output_file=ident_changes,
                                           header='name,new_identifier,new_url,old_identifier,old_url',
                                           format_func=fmt)
            join_function = JoinFunction(IdentifierChange,
                                         [IdentifierChangeValidator(errors_exporter, settings=self.settings),
                                          IdentifierChangeValidator(identifier_exporter, settings=self.settings)],
                                         settings=self.settings)

            sorted_join.inner_join(join_function, lambda x, y: locale.strcoll(x['product_hash'], y['product_hash']))
            ident_changes.close()
            if identifier_exporter.exported_lines == 0:
                os.unlink(identifier_changes_path)

    def _compute_matched_deletions(self, folder_path, all_products_path, changes_path):
        if os.path.exists(all_products_path):
            matched = 0
            with open(all_products_path) as o:
                reader = csv.DictReader(o)
                for row in reader:
                    if row['matched'] == 't':
                        matched += 1

            all_f = SortedFile(all_products_path, sort_products_file, reader=CSVReader)
            changes_f = SortedFile(changes_path, sort_products_file, reader=CSVReader)
            sorted_join = SortedJoin(all_f, changes_f)
            counter = Counter(lambda result: result[1]['status'] == 'old' and result[0]['matched'] == 't')
            join_function1 = JoinFunction(lambda x, y, sett: (x, y), [counter], settings=self.settings)
            sorted_join.inner_join(join_function1, lambda x, y: locale.strcoll(x['identifier'], y['identifier']))
            return counter.count, matched
        else:
            return 0, 0

    def _detect_duplicate_identifiers(self, path, errors_exporter):
        validator = DuplicateIdentifierValidator()
        reader = CSVReader(path)
        for row in reader:
            r = validator.validate(row)
            if r:
                errors_exporter.export(r)

    def update(self, folder_path):
        # Update locale to avoid messing up the rules for sorting strings in python
        # with the rules from the sort command in linux
        locale.setlocale(locale.LC_ALL, '')

        old_products_path = os.path.join(folder_path, 'old_products.csv')
        new_products_path = os.path.join(folder_path, 'new_products.csv')
        all_products_path = os.path.join(folder_path, 'all_products.csv')
        old_meta_path = os.path.join(folder_path, 'old_meta.json-lines')
        new_meta_path = os.path.join(folder_path, 'new_meta.json-lines')
        new_meta_merged_path = os.path.join(folder_path, 'new_meta_merged.json-lines')
        product_changes_path = os.path.join(folder_path, 'changes.csv')
        meta_changes_path = os.path.join(folder_path, 'meta_changes.json-lines')
        additional_changes_path = os.path.join(folder_path, 'additional_changes.json-lines')
        errors_path = os.path.join(folder_path, 'errors.csv')
        identifier_changes_path = os.path.join(folder_path, 'identifier_changes.csv')
        errors_file = open(errors_path, 'w')
        errors_exporter = Exporter(output_file=errors_file, header='code,error',
                                   format_func=lambda result: result.format_csv())

        if not os.path.exists(old_products_path):
            with open(old_products_path, 'w') as f:
                with open(new_products_path) as f1:
                    line = f1.readline()
                    f.write(line)

        if not os.path.exists(old_meta_path) and os.path.exists(new_meta_path):
            with open(old_meta_path, 'w'):
                pass

        if os.path.exists(old_products_path):
            old_dups_count = remove_duplicates(old_products_path)
        if os.path.exists(new_products_path):
            new_dups_count = remove_duplicates(new_products_path)

        self._detect_duplicate_identifiers(new_products_path, errors_exporter)

        old_products_file = SortedFile(old_products_path, sort_products_file, reader=CSVReader)
        new_products_file = SortedFile(new_products_path, sort_products_file, reader=CSVReader)
        sorted_join = SortedJoin(old_products_file, new_products_file)

        product_changes_file = open(product_changes_path, 'w')
        header = 'identifier,name,url,price,old_price,status,sku,category,' \
                 'brand,image_url,shipping_cost,stock,dealer'
        changes_exporter = Exporter(output_file=product_changes_file, header=header,
                                    format_func=lambda result: result.format_csv())
        additions_path = os.path.join(folder_path, 'additions.csv')
        additions = open(additions_path, 'w')
        additions_exporter = Exporter(output_file=additions, header=header,
                                      format_func=lambda result: export_status(Change.NEW, result))
        changes_stats = ChangesStats()
        changes_validators = [cls(errors_exporter, settings=self.settings) for cls in self.changes_validators]
        join_function1 = JoinFunction(PriceChange,
                                      [changes_exporter, additions_exporter, changes_stats] + changes_validators,
                                      settings=self.settings)

        additional_change_file = open(additional_changes_path, 'w')
        additional_exporter = Exporter(output_file=additional_change_file,
                                       format_func=lambda result: result.format_json())
        additional_stats = AdditionalChangesStats()
        additional_validators = [cls(errors_exporter, settings=self.settings)
                                 for cls in self.additional_changes_validators]
        join_function2 = JoinFunction(AdditionalChange,
                                      [additional_exporter, additional_stats] + additional_validators,
                                      settings=self.settings)

        join_function = CompositeJoinFunction([join_function1, join_function2])

        sorted_join.full_join(join_function, lambda x, y: locale.strcoll(x['identifier'], y['identifier']))
        product_changes_file.close()
        additions.close()


        # metadata
        meta_stats = None
        old_meta_dups_count = None
        new_meta_dups_count = None
        if os.path.exists(old_meta_path) and os.path.exists(new_meta_path):
            if os.path.exists(old_meta_path):
                old_meta_dups_count = remove_duplicates_meta(old_meta_path)
            if os.path.exists(new_meta_path):
                new_meta_dups_count = remove_duplicates_meta(new_meta_path)

            old_meta_file = SortedFile(old_meta_path, sort_metadata_file, reader=JsonLinesReader)
            new_meta_file = SortedFile(new_meta_path, sort_metadata_file, reader=JsonLinesReader)
            new_meta_merged_file = open(new_meta_merged_path, 'w')

            def format_meta_merge(result):
                if result.new_element:
                    return json.dumps(result.new_element)
                else:
                    r = copy.copy(result.old_element)
                    r['_status'] = 'old'
                    return json.dumps(r)

            meta_merged_export = Exporter(output_file=new_meta_merged_file,
                                          format_func=format_meta_merge)

            merge_function = JoinFunction(MetadataChange, [MergeReviews(), meta_merged_export],
                                          settings=self.settings)
            meta_join = SortedJoin(old_meta_file, new_meta_file)
            meta_join.full_join(merge_function, lambda x, y: locale.strcoll(x['identifier'], y['identifier']))
            new_meta_file.close()
            new_meta_merged_file.close()
            shutil.move(new_meta_merged_path, new_meta_path)

            old_meta_file = SortedFile(old_meta_path, sort_metadata_file, reader=JsonLinesReader)
            new_meta_file = SortedFile(new_meta_path, sort_metadata_file, reader=JsonLinesReader)
            meta_join = SortedJoin(old_meta_file, new_meta_file)
            meta_changes_file = open(meta_changes_path, 'w')
            meta_changes_exporter = Exporter(output_file=meta_changes_file, accept_codes=[Change.UPDATE],
                                             format_func=lambda result: result.format_json())
            meta_validators = [cls(errors_exporter, settings=self.settings)
                               for cls in self.metadata_changes_validators]
            meta_stats = MetadataChangesStats()
            meta_function = JoinFunction(MetadataChange,
                                         [meta_changes_exporter, meta_stats] + meta_validators,
                                         settings=self.settings)
            meta_join.full_join(meta_function, lambda x, y: locale.strcoll(x['identifier'], y['identifier']))

        stats = changes_stats.stats.copy()
        matched_deletions, matched = self._compute_matched_deletions(folder_path, all_products_path,
                                                                     product_changes_path)
        stats['matched_deletions'] = matched_deletions
        stats['matched'] = matched
        stats.update(additional_stats.stats)

        if meta_stats:
            stats.update(meta_stats.stats)
            stats['old_meta_dups_count'] = old_meta_dups_count
            stats['new_meta_dups_count'] = new_meta_dups_count
        change_val = ChangesValidator(settings=self.settings)
        additional_val = AdditionalChangesValidator(settings=self.settings)
        meta_val = MetadataChangesValidator(settings=self.settings)
        for error in change_val.validate(stats):
            errors_exporter.export(error)
        for error in additional_val.validate(stats):
            errors_exporter.export(error)
        if meta_stats:
            for error in meta_val.validate(stats):
                errors_exporter.export(error)

        if not self.settings.get('ignore_identifier_changes'):
            self._detect_identifier_changes(folder_path, all_products_path, new_products_path,
                                            additions_path, errors_exporter, identifier_changes_path)

        stats['errors_found'] = errors_exporter.exported_lines > 0
        stats['old_dups_count'] = old_dups_count
        stats['new_dups_count'] = new_dups_count

        return stats
