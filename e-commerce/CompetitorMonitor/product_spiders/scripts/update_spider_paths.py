import sys
import os.path
from sqlalchemy.sql import text

HERE = os.path.dirname(os.path.abspath(__file__))
product_spiders_root = os.path.dirname(HERE)
project_root = os.path.dirname(product_spiders_root)

sys.path.append(project_root)
sys.path.append(os.path.join(project_root, 'product_spiders'))

from product_spiders.db import Session
from scrapy.utils.misc import walk_modules
from scrapy.utils.spider import iter_spider_classes
from productspidersweb.models import Spider

print sys.path
here = os.path.abspath(os.path.dirname(__file__))

db_session = Session()

spider_modules = ['product_spiders.spiders']

for name in spider_modules:
    for module in walk_modules(name):
        for spider in iter_spider_classes(module):
            sp = db_session.query(Spider).filter(Spider.name == spider.name).first()
            if sp:
                sp.module = str(spider.__module__)
                db_session.add(sp)
                
db_session.commit()