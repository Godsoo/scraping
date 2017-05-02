import os.path
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
product_spiders_root = os.path.dirname(HERE)
project_root = os.path.dirname(product_spiders_root)
productspiders_web_root = os.path.join(project_root, 'productspidersweb')
sys.path.append(productspiders_web_root)


from scheduler import crawl_required, upload_required, schedule_spiders, reschedule_crawls, schedule_crawls_on_workers
