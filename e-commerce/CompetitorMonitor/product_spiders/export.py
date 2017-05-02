import csv
import json
import config
from decimal import Decimal
import pandas as pd

from product_spiders.utils import write_to_json_lines_file

from db import Session
from productspidersweb.models import DelistedDuplicateError

def export_changes(path, changes, date, site_id, client_id, upload_testing):
    change_types = {'addition': 'new',
                    'deletion': 'removed',
                    'update': 'updated',
                    'silent_update': 'normal'}

    if upload_testing:
        client_id = config.TESTING_ACCOUNT

    f = open(path, 'w')
    writer = csv.writer(f)

    writer.writerow(['date', 'client_id', 'site_id', 'name', 'url', 'price',
                     'old_price', 'difference', 'status', 'sku', 'category',
                     'brand', 'image_url', 'shipping_cost', 'identifier', 'stock', 'dealer'])
    for change in changes:
        # for col in ['name', 'sku', 'url']:
        #    change[col] = change[col].encode('utf8', 'ignore')

        writer.writerow([date.strftime('%Y-%m-%d'), client_id, site_id,
                         change['name'], change['url'], change['price'],
                         change.get('old_price', ''),
                         change.get('difference', ''),
                         change_types[change['change_type']],
                         change.get('sku', ''), change.get('category', ''),
                         change.get('brand', ''), change.get('image_url', ''),
                         change.get('shipping_cost', ''),
                         change.get('identifier', ''),
                         change.get('stock', ''),
                         change.get('dealer', '')])

    f.close()

def export_changes_new(path, changes, site_id):
    change_types = {'addition': 'new',
                    'deletion': 'old',
                    'update': 'updated',
                    'silent_update': 'normal'}

    f = open(path, 'w')
    writer = csv.writer(f)

    writer.writerow(['identifier', 'website_id', 'name', 'url', 'price',
                     'old_price', 'status', 'sku', 'category',
                     'brand', 'image_url', 'shipping_cost', 'stock', 'dealer'])
    for change in changes:
        # for col in ['name', 'sku', 'url']:
        #    change[col] = change[col].encode('utf8', 'ignore')

        writer.writerow([change.get('identifier', ''), site_id,
                         change['name'], change['url'], change['price'],
                         change.get('old_price', ''),
                         change_types[change['change_type']],
                         change.get('sku', ''), change.get('category', ''),
                         change.get('brand', ''), change.get('image_url', ''),
                         change.get('shipping_cost', ''),
                         change.get('stock'),
                         change.get('dealer', '')])

    f.close()

def export_additional_changes(path, changes):
    write_to_json_lines_file(path, changes, json_serialize)

def json_serialize(o):
    if isinstance(o, Decimal):
        return str(o)
    else:
        return encoder.default(o)

def export_metadata_changes(path, changes):
    write_to_json_lines_file(path, changes, json_serialize)

def export_metadata(path, products, meta_db, crawl_id):
    with open(path, 'w+') as f:
        for l in products:
            l['metadata'] = meta_db.get_metadata(l['identifier'], crawl_id)
            f.write(json.dumps(l, default=json_serialize))
            f.write('\n')
            l['metadata'] = None

    return True

def export_errors(path, errors):
    f = open(path, 'w')
    writer = csv.writer(f)

    writer.writerow(['code', 'error'])
    for code, error in errors:
        if isinstance(error, unicode):
            error = error.encode('utf-8')
        writer.writerow([code, error])

    f.close()

def export_delisted_duplicate_errors(errors, current_crawl):
    db_session = Session()

    for i, error in enumerate(errors):
        dd = DelistedDuplicateError()
        dd.website_id = current_crawl.spider.website_id
        dd.crawl_id = current_crawl.id
        dd.name = error['name']
        dd.old_identifier = error['old_identifier']
        dd.new_identifier = error['new_identifier']
        dd.old_url = error['old_url']
        dd.new_url = error['new_url']

        db_session.add(dd)

        if i % 50 == 0 and i > 0:
            db_session.commit()

    db_session.commit()
    db_session.close()


def export_delisted_duplicate_errors_new(current_crawl, filename):
    website_id = current_crawl.spider.website_id
    crawl_id = current_crawl.id

    db_session = Session()
    dd_error = db_session.query(DelistedDuplicateError)\
        .filter(DelistedDuplicateError.website_id == website_id,
                DelistedDuplicateError.crawl_id == crawl_id)\
        .first()

    if not dd_error:
        dd_error = DelistedDuplicateError()
    dd_error.website_id = website_id
    dd_error.crawl_id = crawl_id
    dd_error.filename = filename
    db_session.add(dd_error)
    db_session.commit()
    db_session.close()
