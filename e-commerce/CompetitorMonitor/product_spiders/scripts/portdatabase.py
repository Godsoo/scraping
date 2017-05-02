import sys
import os
import cPickle

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.abspath(os.path.join(HERE,
                                             '../../productspidersweb')))

from productspidersweb.models import Account, Spider, Crawl
sys.path.append('..')

from db import Session

if __name__ == '__main__':
    db_session = Session()
    with open('db.data') as f:
        accounts = cPickle.load(f)
        for account_data in accounts:
            account = Account()
            print account_data['id']
            account.id = account_data['id']
            account.name = account_data['name']
            account.member_id = account_data['member_id']
            account.enabled = account_data['enabled']

            for spider_data in account_data['spiders']:
                spider = Spider()
                spider.id = spider_data['id']
                spider.name = spider_data['name']
                spider.website_id = spider_data['website_id']
                spider.start_hour = spider_data['start_hour']
                spider.upload_hour = spider_data['upload_hour']
                spider.enabled = spider_data['enabled']
                spider.automatic_upload = spider_data['automatic_upload']
                spider.update_percentage_error = spider_data['update_percentage_error']
                
                for crawl_data in spider_data['crawls']:
                    crawl = Crawl(crawl_data['crawl_date'], spider, crawl_data['status'])
                    crawl.id = crawl_data['id']
                    spider.crawls.append(crawl)

                account.spiders.append(spider)
            
            db_session.add(account)
            db_session.commit()
                    
