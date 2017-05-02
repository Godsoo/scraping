import json
import hashlib
import re
from datetime import datetime
import os

here = os.path.abspath(os.path.dirname(__file__))

import MySQLdb

MYSQL_DB = 'compmon_main'
MYSQL_USER = 'compmon_main'
MYSQL_PASS = 'ZocKDL13'

def get_hashkey_type(conn, member_id, website_id):
    c = conn.cursor()
    c.execute('SELECT hashtype FROM websites WHERE id=%s', (website_id,))
    r = c.fetchone()
    if r[0]:
        return r[0]
    
    c.execute('SELECT hash_url, hash_sku FROM members WHERE id=%s', (member_id,))
    r = c.fetchone()
    if r[0]:
        return 'NAME_URL'
    elif r[1]:
        return 'SKU'
    else:
        return 'NAME'

def get_hashkey(product, hashkey_type):
    hashkey_strs = {'SKU': product.get('sku', ''), 'NAME': product.get('name', ''),
                   'URL': product.get('url', ''), 
                   'SKU_NAME': product.get('sku', '') + product.get('name', ''),
                   'NAME_URL': product.get('name', '') + product.get('url', ''),
                   'IDENT': product.get('identifier', '')}
    
    return hashlib.md5(hashkey_strs[hashkey_type].encode('utf8')).hexdigest()
        

def add_product_metadata_changes(conn, product, metadata_update_pass_id, hashkey):
    c = conn.cursor()
    c.execute('''INSERT INTO products_metadata_update (hashkey, metadata_update_pass_id, metadata)
                 VALUES (%s, %s, %s)''', (hashkey, metadata_update_pass_id, json.dumps(product)))
    conn.commit()

def update_product_metadata(conn, product, hashkey, website_id):
    c = conn.cursor()
    c.execute('SELECT id, metadata FROM products_metadata WHERE hashkey=%s', (hashkey,))
    product_row = c.fetchone()
    if not product_row:
        c.execute('INSERT INTO products_metadata (hashkey, metadata, website_id) VALUES (%s, %s, %s)',
                  (hashkey, '', website_id))
        conn.commit()
        c.execute('SELECT LAST_INSERT_ID()')
        row_id = c.fetchone()[0]
        metadata = {}
    else:
        row_id = product_row[0]
        if product_row[1]:    
            metadata = json.loads(product_row[1])
        else:
            metadata = {}
        
    for change in product.get('insert', []):
        if type(change['value']) != dict:
            metadata[change['field']] = change['value']
        else:
            new_value = metadata.get(change['field'], [])
            new_value.append(change['value'])
            metadata[change['field']] = new_value
            
    for change in product.get('delete', []):
        if type(change['value']) != dict:
            metadata[change['field']] = ''
        else:
            if change['value'] in metadata.get(change['field'], []):
                metadata[change['field']].remove(change['value'])
                
    c.execute('UPDATE products_metadata SET metadata=%s WHERE id=%s', (json.dumps(metadata), row_id))
    conn.commit()
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         

def import_metadata_changes(filename):
    with open(os.path.join(here, filename)) as f:
        member_id, website_id, crawl_date = re.search('(\d+)-(\d+)-(\d+-\d+-\d+)\.json', filename).groups(0)
        member_id = int(member_id)
        website_id = int(website_id)
        crawl_date = datetime.strptime(crawl_date, '%Y-%m-%d')
            
        conn = MySQLdb.connect(host='localhost', user=MYSQL_USER, passwd=MYSQL_PASS, db=MYSQL_DB)
        c = conn.cursor()
        c.execute('INSERT INTO metadata_update_pass (date, website_id) VALUES (%s, %s)', 
                  (crawl_date, website_id))
        
        conn.commit()
        c.execute('SELECT LAST_INSERT_ID()')
        metadata_update_pass_id = c.fetchone()[0]
        
        products = json.load(f)
        hashkey_type = get_hashkey_type(conn, member_id, website_id)
        for product in products:
            hashkey = get_hashkey(product, hashkey_type)
            add_product_metadata_changes(conn, product, metadata_update_pass_id, hashkey)
            update_product_metadata(conn, product, hashkey, website_id)
            
