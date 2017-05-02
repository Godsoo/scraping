import os
import csv
import cStringIO

HERE = os.path.abspath(os.path.dirname(__file__))

def normalize_space(s):
    ''' Cleans up space/newline characters '''
    import re
    return re.sub(r'\s+', ' ', s.replace(u'\xa0', ' ').strip())

def mksearch(brand, sku, cat):
    ''' Generates search strings from category and sku
        Try to search for sku + cat first and then start removing words from cat
        until just SKU is left.
        XXX: Hack for SKUs like Sixty Black (don't search SKU without a brand from cat)
    '''
    if brand.lower() in sku.lower():
        brand = ''
    cats = cat.split()
    results = []
    while cats:
        results.append(' '.join([brand] + [sku] + cats))
        cats.pop(-1)

    if len(cat.split()) > 1 and len(sku.split()) > 1:
        results.append(' '.join([brand] + sku.split()[:-1] + cat.split()[:1]))

    results.append(brand + ' ' + sku)
    return results

def get_product_list(site_id):
    with open(os.path.join(HERE, 'products.csv')) as f:
        reader = list(csv.DictReader(cStringIO.StringIO(f.read())))

        # First get specific URLs
        for row in reader:
            search = []
            url = row[site_id]
            if url and not url.startswith('http://') and not url.startswith('https://'):
                search = [url]
                url = ''

            if not url: continue
            yield {
                'brand': row['Brand'],
                'category': row['Category'],
                'sku': url and normalize_space(row['Products / Retailers']) or '',
                'url': url,
                'search': search + mksearch(row['Brand'], normalize_space(row['Products / Retailers']), row['Category'])
            }

        # Perform search on pages
        for row in reader:
            search = []
            url = row[site_id]
            if url and not url.startswith('http://') and not url.startswith('https://'):
                search = [url]
                url = ''

            if url: continue
            yield {
                'brand': row['Brand'],
                'category': row['Category'],
                'sku': url and normalize_space(row['Products / Retailers']) or '',
                'url': url,
                'search': search + mksearch(row['Brand'], normalize_space(row['Products / Retailers']), row['Category'])
            }


if __name__ == '__main__':
    for r in get_product_list('Asda'):
        print r['search']
