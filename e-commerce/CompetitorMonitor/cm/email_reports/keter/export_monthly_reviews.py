__author__ = 'lucas'

import csv
import json
import MySQLdb

MYSQL_DB = 'compmon_main'
MYSQL_USER = 'compmon_main'
MYSQL_PASS = 'ZocKDL13'

def get_product_name(conn, website_id, hashkey):
    c = conn.cursor()
    c.execute('''select p.name from products p
                 inner join websites w on p.website_id = w.id
                 where p.hashkey=%s and if(w.parent_id, w.parent_id, w.id)=%s''', (hashkey, website_id))
    r = c.fetchone()
    if r:
        return r[0]

def get_website_name(conn, website_id):
    c = conn.cursor()
    c.execute('select url from websites where id=%s', (website_id,))
    url = c.fetchone()[0]

    return url.split('//')[1].replace('www.', '')


if __name__ == '__main__':
    member_id = 2067
    conn = MySQLdb.connect(host='localhost', user=MYSQL_USER, passwd=MYSQL_PASS, db=MYSQL_DB)
    c = conn.cursor()
    c.execute('select id from websites where parent_id=0 and member_id=%s', (member_id,))
    websites = [x[0] for x in c.fetchall()]
    f = open('monthly.csv', 'w')
    writer = csv.writer(f)
    writer.writerow(['Website Name', 'Product', 'Date', 'Rating', 'URL', 'Review'])
    for website in websites:
        website_name = get_website_name(conn, website)
        print website_name
        c.execute('select id from metadata_update_pass where website_id=%s '
                  'and date >= date_sub(curdate(), interval 30 day)', (website,))
        updates = [x[0] for x in c.fetchall()]
        for update in updates:
            c.execute('''select hashkey, metadata from products_metadata_update
                         where metadata_update_pass_id=%s''', (update,))
            metadata_results = c.fetchmany(100)
            while metadata_results:
                for result in metadata_results:
                    hashkey = result[0]
                    metadata = json.loads(result[1])
                    try:
                        name = get_product_name(conn, website, hashkey).decode('utf8', 'ignore')
                    except AttributeError:
                        continue

                    for insert in metadata.get('insert'):
                        if insert['field'] == 'reviews':
                            review = insert['value']
                            date = review.get('date', '')
                            full_text = review.get('full_text', '').encode('utf8')
                            rating = review.get('rating', '')
                            url = review.get('url', '').encode('utf8')
                            writer.writerow([website_name, name, date, rating, url, full_text])

                    metadata_results = c.fetchmany(100)

