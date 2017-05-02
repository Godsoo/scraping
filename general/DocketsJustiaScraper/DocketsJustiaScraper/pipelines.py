# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: http://doc.scrapy.org/en/latest/topics/item-pipeline.html
import csv
from DocketsJustiaScraper import settings
import re

new_file = True
def write_to_csv(item):
    global new_file
    keys = []
    values = []
    for key in sorted(item):
        keys.append( re.sub(r'^[\d]+.', '', key) )
        values.append( item[key] )
    if ( new_file ):
        writer = csv.writer(open(settings.csv_file_path, 'w'), lineterminator='\n')
        writer.writerow(keys)
        new_file = False
    else:
        writer = csv.writer(open(settings.csv_file_path, 'a'), lineterminator='\n')
    writer.writerow(values)
    # if not os.path.exists(settings.csv_file_path):
    #     writer.writerow(keys)
    # writer.writerow(values)

class DocketsjustiascraperPipeline(object):
    def process_item(self, item, spider):
        write_to_csv(item)
        return item
