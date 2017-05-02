import csv
import os
import shutil
from json import JSONEncoder
from scrapy.exceptions import DropItem
from scrapy import signals
try:
    from scrapy.project import crawler
except ImportError:
    pass

from scrapy.xlib.pydispatch import dispatcher
from scrapy.contrib.exporter import CsvItemExporter, JsonItemExporter, JsonLinesItemExporter
from scrapy.item import Item, Field
import decimal

from utils import remove_punctuation_and_spaces

from config import DATA_DIR


class ProductSpidersPipeline(object):
    def process_item(self, item, spider):
        if not item.get('name'):
            raise DropItem('Product without name')

        # replace line breaks as they mess up the resulting csv
        for k in item:
            if type(item[k]) in [str, unicode]:
                item[k] = item[k].replace('\n', '').replace('\r', '')

        # restrict dealer if required by the spider
        if hasattr(spider, 'allowed_dealers') and item.get('dealer', '').lower() not in spider.allowed_dealers:
            raise DropItem('Dealer is not in the allowed dealers list')

        if hasattr(spider, 'field_modifiers'):
            for k in spider.field_modifiers:
                if k in item:
                    item[k] = spider.field_modifiers[k](item[k])

        return item

class PriceConversionRatePipeline(object):
    def process_item(self, item, spider):
        if hasattr(spider, 'price_conversion_rate') and item.get('price'):
            item['price'] = item['price'] * spider.price_conversion_rate
            if item.get('shipping_cost'):
                item['shipping_cost'] = item['shipping_cost'] * spider.price_conversion_rate

        return item

class RequiredFieldsPipeline(object):
    def __init__(self, crawler):
        self.crawler = crawler

    def process_item(self, item, spider):
        if not item.get('identifier'):
            if not hasattr(spider, 'errors'):
                spider.errors = []
            msg = 'Product without identifier collected "%s"' % item['name']
            spider.errors.append(msg)
            self.crawler.engine.close_spider(spider)
            raise DropItem('Item without identifier: %s' % item)

        return item

    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler)

class ReplaceIdentifierPipeline(object):
    def __init__(self):
        self.duplicates = {}
        dispatcher.connect(self.spider_opened, signals.spider_opened)

    def process_item(self, item, spider):
        if self.identifier_replacements is not None:
            identifier = item.get('identifier')
            if identifier:
                replacement_found = self.identifier_replacements[self.identifier_replacements['identifier'] == identifier]
                if not replacement_found.empty:
                    item['identifier'] = replacement_found.iloc[0]['old_identifier']
        return item

    def spider_opened(self, spider):
        filename = os.path.join(DATA_DIR, '%s_identifier_replacements.csv' % spider.website_id)
        if os.path.exists(filename):
            import pandas as pd
            self.identifier_replacements = pd.read_csv(filename, dtype=pd.np.str)
        else:
            self.identifier_replacements = None

class DuplicateProductsPipeline(object):
    def __init__(self):
        self.duplicates = {}
        dispatcher.connect(self.spider_opened, signals.spider_opened)
        dispatcher.connect(self.spider_closed, signals.spider_closed)

    def process_item(self, item, spider):
        item_key = item.get('identifier')
        if not item_key:
            item_key = item['name']

        if not getattr(spider, 'deduplicate_identifiers', False):
            str_price = str(item['price'])
            if '.' in str_price:
                str_price = str_price.rstrip('0').rstrip('.')
            item_id = '%s:%s' % (str_price, item_key)
        else:
            item_id = '%s' % item_key

        if item_id in self.duplicates[spider]:
            raise DropItem('Duplicate item found: %s' % item)
        else:
            self.duplicates[spider].add(item_id)

        return item

    def spider_opened(self, spider):
        self.duplicates[spider] = set()

    def spider_closed(self, spider):
        del self.duplicates[spider]


class LocalDataMixin(object):
    data_folder = 'local_data'
    nfs_data_folder = 'data'

    def __init__(self):
        for folder in [self.data_folder, os.path.join(self.data_folder, 'meta'),
                       os.path.join(self.data_folder, 'unified_marketplace')]:
            if not os.path.exists(folder) or not os.path.isdir(folder):
                os.makedirs(folder)

    def get_data_filename(self, spider):
        raise NotImplementedError("Method `_get_data_filename` must be implemented!")

    def get_unified_marketplace_data_filename(self, spider):
        raise NotImplementedError("Method `_get_unified_marketplace_data_filename` must be implemented!")

    def get_local_data_filepath(self, spider):
        return os.path.join(self.data_folder, self.get_data_filename(spider))

    def get_local_data_unified_marketplace_data_filepath(self, spider):
        return os.path.join(self.data_folder, self.get_unified_marketplace_data_filename(spider))

    def move_local_data_file_to_nfs(self, spider):
        products_filename = self.get_data_filename(spider)
        src = os.path.join(self.data_folder, products_filename)
        dst = os.path.join(self.nfs_data_folder, products_filename)
        shutil.move(src, dst)

    def move_local_unified_marketplace_data_file_to_nfs(self, spider):
        products_filename = self.get_unified_marketplace_data_filename(spider)
        src = os.path.join(self.data_folder, products_filename)
        dst = os.path.join(self.nfs_data_folder, products_filename)
        shutil.move(src, dst)


class CsvExportPipeline(LocalDataMixin, object):
    data_folder = 'local_data'
    nfs_data_folder = 'data'

    def __init__(self):
        super(CsvExportPipeline, self).__init__()

        dispatcher.connect(self.spider_opened,
                           signal=signals.spider_opened)
        dispatcher.connect(self.spider_closed,
                           signal=signals.spider_closed)
        self.files = {}
        self.unified_marketplace_files = {}
        self.exporter_market = None

    def get_data_filename(self, spider):
        return '%s_products.csv' % spider.crawl_id

    def get_unified_marketplace_data_filename(self, spider):
        return 'unified_marketplace/' + spider.data_filename + '.csv'

    def spider_opened(self, spider):
        f = open(self.get_local_data_filepath(spider), 'w')
        self.files[spider] = f
        self.exporter = CsvItemExporter(f)
        self.exporter.fields_to_export = ['identifier', 'sku',
                                          'name', 'price', 'url', 'category',
                                          'brand', 'image_url', 'shipping_cost', 'stock', 'dealer']
        self.exporter.start_exporting()
        if hasattr(spider, 'market_type') and getattr(spider, 'market_type') == 'direct':
            f1 = open(self.get_local_data_unified_marketplace_data_filepath(spider), 'w')
            self.unified_marketplace_files[spider] = f1
            self.exporter_market = CsvItemExporter(f1)
            self.exporter_market.fields_to_export = self.exporter.fields_to_export[:]
            self.exporter_market.start_exporting()

    def spider_closed(self, spider):
        self.exporter.finish_exporting()
        f = self.files.pop(spider)
        f.close()

        self.move_local_data_file_to_nfs(spider)

        if spider in self.unified_marketplace_files:
            self.exporter_market.finish_exporting()
            f = self.unified_marketplace_files.pop(spider)
            f.close()

            self.move_local_unified_marketplace_data_file_to_nfs(spider)

    def process_item(self, item, spider):
        item = self._truncate_values(item)
        if self.exporter_market and item.get('dealer'):
            self.exporter_market.export_item(item)
        else:
            self.exporter.export_item(item)

        return item

    def _truncate_values(self, item):
        for field, value in item.items():
            if field in ('name', 'category') and len(value) > 1024:
                item[field] = value[:1021] + '...'
        return item

class DuplicateProductPickerPipeline(object):
    """
    Checks for duplicate identifier+name products, leaves only the one with lowest price, removes the rest
    """
    def __init__(self):
        dispatcher.connect(self.spider_closed,
                           signal=signals.spider_closed)
        self.files = {}

    def _get_product_key(self, product):
        """
        >>> pipeline = DuplicateProductPickerPipeline()
        >>> a = {'name': 'Burgess Excel Tasty Nuggets for Adult Rabbits-4kg', 'identifier': '1928'}
        >>> b = {'name': 'Burgess Excel Tasty Nuggets for Adult Rabbits 4kg', 'identifier': '1928'}
        >>> res1 = pipeline._get_product_key(a)
        >>> res2 = pipeline._get_product_key(b)
        >>> res1 == res2
        True
        >>> res1
        ('1928', 'burgessexceltastynuggetsforadultrabbits4kg')
        """
        identifier = product['identifier']
        name = remove_punctuation_and_spaces(product['name']).lower()
        return identifier, name

    def spider_closed(self, spider):
        """
        Find 'identifier', 'name' duplicates
        We process products right from file
        cause some spiders have too many products to load them to memory all at once
        """
        filename = 'data/%s_products.csv' % spider.crawl_id
        h = open(filename, 'r')
        reader = csv.DictReader(h)
        fields = reader.fieldnames
        ids = set()
        duplicates = set()
        duplicate_items = {}
        for row in reader:
            if not row['identifier']:
                continue
            key = self._get_product_key(row)
            if key not in ids:
                ids.add(key)
            else:
                duplicates.add(key)

        if not duplicates:
            h.close()
            return

        # collect all duplicates into dict where key is (identifier, name) pair
        h.close()
        h = open(filename, 'r')
        reader = csv.DictReader(h)  # rewind file to second row, we don't need first row cause it contains header
        for row in reader:
            key = self._get_product_key(row)
            if key in duplicates:
                if not key in duplicate_items.keys():
                    duplicate_items[key] = []
                duplicate_items[key].append(row)

        unique_items_from_duplicates = self._pick_lowest_for_duplicates(duplicate_items)

        # write to new file
        filename2 = 'data/%s_products_temp.csv' % spider.crawl_id
        h2 = open(filename2, 'w')
        writer = csv.DictWriter(h2, fields)
        writer.writeheader()
        h.close()
        h = open(filename, 'r')
        reader = csv.DictReader(h)  # rewind again
        for row in reader:
            key = self._get_product_key(row)
            if not key in duplicates:
                writer.writerow(row)
        for row in unique_items_from_duplicates:
            writer.writerow(row)
        h.close()
        h2.close()

        filename3 = 'data/%s_products_temp.csv_temp' % spider.crawl_id
        os.rename(filename, filename3)
        os.rename(filename2, filename)
        os.rename(filename3, filename2)


    def _pick_lowest_for_duplicates(self, duplicate_items):
        """
        >>> item1 = {'name': 'asd', 'desc': 'asd1', 'price': 3}
        >>> item2 = {'name': 'asd', 'desc': 'asd2', 'price': 2}
        >>> item3 = {'name': 'qwe', 'desc': 'qwe', 'price': 1}
        >>> items = {}
        >>> items['asd'] = [item1, item2]
        >>> items['qwe'] = [item3]
        >>> a = DuplicateProductPickerPipeline()
        >>> res = a._pick_lowest_for_duplicates(items)
        >>> len(res)
        2
        >>> res.sort(key=lambda x: x['name'])
        >>> res[0]['name'], res[0]['desc'], res[0]['price']
        ('asd', 'asd2', 2)
        >>> res[1]['name'], res[1]['desc'], res[1]['price']
        ('qwe', 'qwe', 1)

        >>> item1 = {'name': 'asd', 'desc': 'asd1', 'price': 2}
        >>> item2 = {'name': 'asd', 'desc': 'asd2', 'price': 3}
        >>> item3 = {'name': 'qwe', 'desc': 'qwe', 'price': 1}
        >>> items = {}
        >>> items['asd'] = [item1, item2]
        >>> items['qwe'] = [item3]
        >>> a = DuplicateProductPickerPipeline()
        >>> res = a._pick_lowest_for_duplicates(items)
        >>> len(res)
        2
        >>> res.sort(key=lambda x: x['name'])
        >>> res[0]['name'], res[0]['desc'], res[0]['price']
        ('asd', 'asd1', 2)
        >>> res[1]['name'], res[1]['desc'], res[1]['price']
        ('qwe', 'qwe', 1)
        """
        res = []
        for key, products in duplicate_items.items():
            min_product = products[0]
            min_price = decimal.Decimal(min_product['price'])
            for p in products:
                if decimal.Decimal(p['price']) < min_price:
                    min_product = p
                    min_price = decimal.Decimal(min_product['price'])
            res.append(min_product)

        return res

encoder = JSONEncoder()

def json_serialize(o):
    if isinstance(o, Field) or isinstance(o, Item):
        return dict(o)
    elif isinstance(o, decimal.Decimal):
        return float(o)
    else:
        return encoder.default(o)

class ConfigurableJsonItemExporter(JsonItemExporter):
    def _configure(self, options, **kwargs):
        return super(ConfigurableJsonItemExporter, self)._configure(options, dont_fail=True)

class ConfigurableJsonLinesItemExporter(JsonLinesItemExporter):
    def _configure(self, options, **kwargs):
        return super(ConfigurableJsonLinesItemExporter, self)._configure(options, dont_fail=True)

class MetadataExportPipeline(LocalDataMixin, object):
    data_folder = 'local_data'
    nfs_data_folder = 'data'

    def __init__(self, stats):
        super(MetadataExportPipeline, self).__init__()
        dispatcher.connect(self.spider_opened,
                           signal=signals.spider_opened)
        dispatcher.connect(self.stats_spider_closed,
                           signal=signals.stats_spider_closed)
        self.files = {}
        self.unified_marketplace_files = {}
        self.exporter_market = None
        self.stats = stats

    def get_data_filename(self, spider):
        return 'meta/%s_meta.json-lines' % spider.crawl_id

    def get_unified_marketplace_data_filename(self, spider):
        return 'unified_marketplace/' + spider.data_filename + '.json-lines'

    def spider_opened(self, spider):
        if spider.enable_metadata:
            f = open(self.get_local_data_filepath(spider), 'w')
            self.files[spider] = f
            self.exporter = ConfigurableJsonLinesItemExporter(f, default=json_serialize)
            self.exporter.start_exporting()
            if hasattr(spider, 'market_type') and getattr(spider, 'market_type') == 'direct':
                f1 = open(self.get_local_data_unified_marketplace_data_filepath(spider), 'w')
                self.unified_marketplace_files[spider] = f1
                self.exporter_market = ConfigurableJsonLinesItemExporter(f1, default=json_serialize)
                self.exporter_market.start_exporting()

    def stats_spider_closed(self, spider):
        if spider.enable_metadata:
            self.exporter.finish_exporting()
            f = self.files.pop(spider)
            f.close()
            self.move_local_data_file_to_nfs(spider)
            if spider in self.unified_marketplace_files:
                self.exporter_market.finish_exporting()
                f = self.unified_marketplace_files.pop(spider)
                f.close()
                self.move_local_unified_marketplace_data_file_to_nfs(spider)

        dispatcher.send('export_finished', None, spider, self.stats.get_stats())

    def process_item(self, item, spider):
        if spider.enable_metadata:
            meta = dict(item.get('metadata', {}))
            item['metadata'] = dict(meta)
            item['price'] = str(item.get('price', ''))
            if 'shipping_cost' in item and item['shipping_cost'] is not None:
                item['shipping_cost'] = str(item['shipping_cost'])
            if meta:
                if self.exporter_market and item.get('dealer'):
                    self.exporter_market.export_item(item)
                else:
                    self.exporter.export_item(item)

        return item

    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler.stats)
