import unittest
import mock
import sys
import os
import json
from datetime import timedelta, datetime, date, time
from time import gmtime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

HERE = os.path.dirname(os.path.abspath(__file__))

sys.path.append(os.path.abspath(os.path.join(HERE,
                                             '../../productspidersweb')))

from productspidersweb.models import initialize_sql
from productspidersweb.models import Spider, Crawl, Account, WorkerServer

sys.path.append(os.path.abspath(os.path.join(HERE, '..')))
from product_spiders.dateutils import gmt_datetime, gmt_date
from product_spiders.scheduler import crawl_required, upload_required
from product_spiders.scheduler.scheduler import schedule_crawls_on_workers, SchedulingError
# need this to mock "run_spider" method

engine = create_engine('sqlite:///:memory:')
Session = sessionmaker()


class TestCrawlUploadRequired(unittest.TestCase):
    def setUp(self):
        self.connection = engine.connect()
        self.trans = self.connection.begin()
        initialize_sql(engine, create_ws=False)
        self.db_session = Session(bind=self.connection)

    def tearDown(self):
        self.trans.rollback()
        self.db_session.close()
        self.connection.close()

    def test_crawl_upload_required_spider_account_disabled(self):
        account = Account()
        spider = Spider()
        spider.account = account

        spider.enabled = True
        account.enabled = False

        self.assertFalse(crawl_required(spider))
        self.assertFalse(upload_required(spider))

        spider.enabled = False
        account.enabled = True

        self.assertFalse(crawl_required(spider))
        self.assertFalse(upload_required(spider))

    def test_crawl_required_done_today(self):
        account = Account()
        account.enabled = True
        account.member_id = 1
        self.db_session.add(account)
        self.db_session.commit()

        spider = Spider()
        spider.name = 'test'
        spider.enabled = True
        spider.website_id = 1
        spider.account = account

        crawl = Crawl(gmt_date(gmtime()), spider, 'upload_finished')

        self.db_session.add(spider)
        self.db_session.add(crawl)
        self.db_session.commit()

        self.assertFalse(crawl_required(spider))

    def test_crawl_required_last_crawl_unfinished(self):
        account = Account()
        account.enabled = True
        account.member_id = 1
        self.db_session.add(account)
        self.db_session.commit()

        spider = Spider()
        spider.name = 'test'
        spider.enabled = True
        spider.website_id = 1
        spider.account = account

        crawl = Crawl(gmt_date(gmtime()) - timedelta(days=1), spider, 'processing_finished')

        self.db_session.add(spider)
        self.db_session.add(crawl)
        self.db_session.commit()

        self.assertFalse(crawl_required(spider))

    def test_crawl_required_hour_true(self):
        account = Account()
        account.enabled = True
        account.member_id = 1
        self.db_session.add(account)
        self.db_session.commit()

        spider = Spider()
        spider.name = 'test'
        spider.enabled = True
        spider.start_hour = gmt_datetime(gmtime()).hour
        spider.website_id = 1
        spider.account = account


        self.db_session.add(spider)
        self.db_session.commit()

        self.assertTrue(crawl_required(spider))

    def test_crawl_required_crawl_day_true(self):
        account = Account()
        account.enabled = True
        account.member_id = 1
        self.db_session.add(account)
        self.db_session.commit()

        spider = Spider()
        spider.name = 'test'
        spider.enabled = True
        spider.start_hour = gmt_datetime(gmtime()).hour
        spider.crawl_day = gmt_datetime(gmtime()).weekday()
        spider.website_id = 1
        spider.account = account


        self.db_session.add(spider)
        self.db_session.commit()

        self.assertTrue(crawl_required(spider))

    def test_crawl_required_crawl_day_false(self):
        account = Account()
        account.enabled = True
        account.member_id = 1
        self.db_session.add(account)
        self.db_session.commit()

        spider = Spider()
        spider.name = 'test'
        spider.enabled = True
        spider.start_hour = gmt_datetime(gmtime()).hour
        d = gmt_datetime(gmtime()).weekday()
        crawl_day = d - 1 if d else 6
        spider.crawl_cron = '* * * * %d' % crawl_day
        spider.website_id = 1
        spider.account = account

        self.db_session.add(spider)
        self.db_session.commit()

        self.assertFalse(crawl_required(spider))

    def test_upload_required_wrong_crawl_state(self):
        account = Account()
        account.enabled = True
        account.member_id = 1
        self.db_session.add(account)
        self.db_session.commit()

        spider = Spider()
        spider.name = 'test'
        spider.enabled = True
        spider.website_id = 1
        spider.account = account

        crawl = Crawl(gmt_date(gmtime()), spider, 'errors_found')

        self.db_session.add(spider)
        self.db_session.add(crawl)
        self.db_session.commit()

        self.assertFalse(upload_required(spider))

    def test_upload_required_scheduled(self):
        account = Account()
        account.enabled = True
        account.member_id = 1
        self.db_session.add(account)
        self.db_session.commit()

        spider = Spider()
        spider.name = 'test'
        spider.enabled = True
        spider.website_id = 1
        spider.account = account

        crawl = Crawl(gmt_date(gmtime()), spider, 'scheduled')

        self.db_session.add(spider)
        self.db_session.add(crawl)
        self.db_session.commit()

        self.assertFalse(upload_required(spider))

    def test_crawl_required_scheduled(self):
        account = Account()
        account.enabled = True
        account.member_id = 1
        self.db_session.add(account)
        self.db_session.commit()

        spider = Spider()
        spider.name = 'test'
        spider.enabled = True
        spider.website_id = 1
        spider.account = account

        crawl = Crawl(gmt_date(gmtime()), spider, 'scheduled')

        self.db_session.add(spider)
        self.db_session.add(crawl)
        self.db_session.commit()

        self.assertFalse(crawl_required(spider))


    def test_upload_required_auto_upload_disabled(self):
        account = Account()
        account.enabled = True
        account.member_id = 1

        spider = Spider()
        spider.name = 'test'
        spider.enabled = True
        spider.website_id = 1
        spider.automatic_upload = False
        spider.account = account

        self.assertFalse(upload_required(spider))

    def test_upload_required_true(self):
        account = Account()
        account.enabled = True
        account.member_id = 1
        self.db_session.add(account)
        self.db_session.commit()

        spider = Spider()
        spider.name = 'test'
        spider.enabled = True
        spider.website_id = 1
        spider.upload_hour = gmt_datetime(gmtime()).hour
        spider.account = account

        crawl = Crawl(gmt_date(gmtime()), spider, 'processing_finished')

        self.db_session.add(spider)
        self.db_session.add(crawl)
        self.db_session.commit()

        self.assertTrue(upload_required(spider))


class TestScheduler(unittest.TestCase):
    def setUp(self):
        self.connection = engine.connect()
        self.trans = self.connection.begin()
        initialize_sql(engine, create_ws=False)
        self.db_session = Session(bind=self.connection)

        self._spider_number = 1
        self._ws_number = 1

    def tearDown(self):
        self.trans.rollback()
        self.db_session.close()
        self.connection.close()

    def mock_account(self, db_session_add=True):
        account = Account()
        account.enabled = True
        if db_session_add:
            self.db_session.add(account)
        return account

    def mock_spider(self, account, priority=None, multicrawl=False, db_session_add=True):
        spider = Spider()
        spider.name = 'spider%d' % self._spider_number
        spider.account = account
        spider.enabled = True
        if priority is not None:
            spider.priority = priority
        if multicrawl:
            spider.enable_multicrawling = True

        if db_session_add:
            self.db_session.add(account)

        # bookkeeping
        self._spider_number += 1

        return spider

    def mock_ws(self, slots, db_session_add=True):
        worker_server = WorkerServer()
        worker_server.enabled = True
        worker_server.name = 'ws%d' % self._ws_number
        worker_server.host = str(self._ws_number)
        worker_server.port = 6800
        worker_server.user = str(self._ws_number)
        worker_server.password = str(self._ws_number)
        worker_server.worker_slots = slots
        worker_server.scrapy_url = 'ws%d' % self._ws_number

        if db_session_add:
            self.db_session.add(worker_server)

        # bookkeeping
        self._ws_number += 1

        return worker_server

    def mock_crawl(self, spider, crawl_date=date.today(), crawl_time=datetime.now().time(), ws_id=None,
                   status='scheduled', db_session_add=True):
        crawl = Crawl(crawl_date, spider, status=status)
        crawl.crawl_time = crawl_time
        if ws_id is not None:
            crawl.worker_server_id = ws_id
        if db_session_add:
            self.db_session.add(crawl)
        return crawl

    def schedule_collecting_data(self):
        scheduled_spiders = {}

        with mock.patch('product_spiders.scheduler.scheduler.run_spider') as MockClass:
            MockClass.return_value = {'jobid': ''}
            with mock.patch('product_spiders.scheduler.scheduler.get_jobs_list') as MockClass2:
                MockClass2.return_value = {'running': [], 'pending': []}
                schedule_crawls_on_workers(self.db_session)
                for call_obj in MockClass.call_args_list:
                    spider_name = call_obj[0][0]
                    schedule_url = call_obj[0][1]
                    ws_id = schedule_url.replace('schedule.json', '')
                    scheduled_spiders[spider_name] = ws_id
        return scheduled_spiders

    def test_1_slot_1_crawl(self):
        ws = self.mock_ws(1)
        self.db_session.commit()
        account = self.mock_account()
        spider = self.mock_spider(account)
        self.assertTrue(crawl_required(spider))
        # add one crawl to queue
        self.mock_crawl(spider, crawl_date=date.today(), status='scheduled')
        self.db_session.commit()

        scheduled_spiders = self.schedule_collecting_data()

        self.assertEqual(len(scheduled_spiders), 1)
        self.assertIn(spider.name, scheduled_spiders)

    def test_1_slot_2_crawls(self):
        ws = self.mock_ws(1)
        self.db_session.commit()
        account = self.mock_account()
        spider1 = self.mock_spider(account)
        spider2 = self.mock_spider(account)
        self.assertTrue(crawl_required(spider1))
        self.assertTrue(crawl_required(spider2))
        # add two crawls to queue
        self.mock_crawl(spider1, crawl_date=date.today(), status='scheduled')
        self.mock_crawl(spider2, crawl_date=date.today(), status='scheduled')
        self.db_session.commit()

        scheduled_spiders = self.schedule_collecting_data()

        self.assertEqual(len(scheduled_spiders), 1)
        scheduled_spider = spider1 if spider1.name in scheduled_spiders else spider2 \
            if spider2.name in scheduled_spiders else None
        self.assertIsNotNone(scheduled_spider)

    def test_3_slots_2_crawls(self):
        ws = self.mock_ws(3)
        self.db_session.commit()
        account = self.mock_account()
        spider1 = self.mock_spider(account)
        spider2 = self.mock_spider(account)
        self.assertTrue(crawl_required(spider1))
        self.assertTrue(crawl_required(spider2))
        # add two crawls to queue
        self.mock_crawl(spider1, crawl_date=date.today(), status='scheduled')
        self.mock_crawl(spider2, crawl_date=date.today(), status='scheduled')
        self.db_session.commit()

        scheduled_spiders = self.schedule_collecting_data()

        self.assertEqual(len(scheduled_spiders), 2)
        self.assertIn(spider1.name, scheduled_spiders)
        self.assertIn(spider2.name, scheduled_spiders)

    def test_2_slots_3_crawls_several_ws(self):
        ws1 = self.mock_ws(1)
        ws2 = self.mock_ws(1)
        self.db_session.commit()
        account = self.mock_account()
        spider1 = self.mock_spider(account)
        spider2 = self.mock_spider(account)
        spider3 = self.mock_spider(account)
        self.assertTrue(crawl_required(spider1))
        self.assertTrue(crawl_required(spider2))
        self.assertTrue(crawl_required(spider3))
        # add two crawls to queue
        self.mock_crawl(spider1, crawl_date=date.today(), status='scheduled')
        self.mock_crawl(spider2, crawl_date=date.today(), status='scheduled')
        self.mock_crawl(spider3, crawl_date=date.today(), status='scheduled')
        self.db_session.commit()

        scheduled_spiders = self.schedule_collecting_data()

        self.assertEqual(len(scheduled_spiders), 2)
        all_spiders = [spider1, spider2, spider3]
        # exactly two spiders got scheduled
        self.assertEqual(sum([s.name in scheduled_spiders for s in all_spiders]), 2)
        # each worker got exactly number of scheduled spiders equal to available slots
        for ws in [ws1, ws2]:
            self.assertEqual(sum([ws.scrapy_url == scrapy_url for scrapy_url in scheduled_spiders.values()]),
                             ws.worker_slots)

    def test_3_slots_3_crawls(self):
        ws = self.mock_ws(3)
        self.db_session.commit()
        account = self.mock_account()
        spider1 = self.mock_spider(account)
        spider2 = self.mock_spider(account)
        spider3 = self.mock_spider(account)
        self.assertTrue(crawl_required(spider1))
        self.assertTrue(crawl_required(spider2))
        # add two crawls to queue
        self.mock_crawl(spider1, crawl_date=date.today(), status='scheduled')
        self.mock_crawl(spider2, crawl_date=date.today(), status='scheduled')
        self.mock_crawl(spider3, crawl_date=date.today(), status='scheduled')
        self.db_session.commit()

        scheduled_spiders = self.schedule_collecting_data()

        self.assertEqual(len(scheduled_spiders), 3)
        # all spiders got scheduled
        for spider in [spider1, spider2, spider3]:
            self.assertIn(spider.name, scheduled_spiders)

    def test_3_slots_3_crawls_several_workers(self):
        ws1 = self.mock_ws(1)
        ws2 = self.mock_ws(2)
        self.db_session.commit()
        account = self.mock_account()
        spider1 = self.mock_spider(account)
        spider2 = self.mock_spider(account)
        spider3 = self.mock_spider(account)
        self.assertTrue(crawl_required(spider1))
        self.assertTrue(crawl_required(spider2))
        # add two crawls to queue
        self.mock_crawl(spider1, crawl_date=date.today(), status='scheduled')
        self.mock_crawl(spider2, crawl_date=date.today(), status='scheduled')
        self.mock_crawl(spider3, crawl_date=date.today(), status='scheduled')
        self.db_session.commit()

        scheduled_spiders = self.schedule_collecting_data()

        self.assertEqual(len(scheduled_spiders), 3)
        # all spiders got scheduled
        for spider in [spider1, spider2, spider3]:
            self.assertIn(spider.name, scheduled_spiders)
        # each worker got exactly number of scheduled spiders equal to available slots
        for ws in [ws1, ws2]:
            self.assertEqual(sum([ws.scrapy_url == scrapy_url for scrapy_url in scheduled_spiders.values()]),
                             ws.worker_slots)

    def test_priority_crawl_1_slot(self):
        ws = self.mock_ws(1)
        self.db_session.commit()
        account = self.mock_account()
        spider1 = self.mock_spider(account)
        spider2 = self.mock_spider(account)
        priority_spider = self.mock_spider(account, priority=1)
        self.assertTrue(crawl_required(spider1))
        self.assertTrue(crawl_required(spider2))
        self.assertTrue(crawl_required(priority_spider))
        # add two crawls to queue
        self.mock_crawl(spider1, crawl_date=date.today(), status='scheduled')
        self.mock_crawl(spider2, crawl_date=date.today(), status='scheduled')
        self.mock_crawl(priority_spider, crawl_date=date.today(), status='scheduled')
        self.db_session.commit()

        scheduled_spiders = self.schedule_collecting_data()

        self.assertEqual(len(scheduled_spiders), 1)
        self.assertIn(priority_spider.name, scheduled_spiders)

    def test_priority_crawl_2_slots_several_workers(self):
        ws1 = self.mock_ws(1)
        ws2 = self.mock_ws(1)
        self.db_session.commit()
        account = self.mock_account()
        spider1 = self.mock_spider(account)
        spider2 = self.mock_spider(account)
        priority_spider = self.mock_spider(account, priority=1)
        self.assertTrue(crawl_required(spider1))
        self.assertTrue(crawl_required(spider2))
        self.assertTrue(crawl_required(priority_spider))
        # add two crawls to queue
        self.mock_crawl(spider1, crawl_date=date.today(), status='scheduled')
        self.mock_crawl(spider2, crawl_date=date.today(), status='scheduled')
        self.mock_crawl(priority_spider, crawl_date=date.today(), status='scheduled')
        self.db_session.commit()

        scheduled_spiders = self.schedule_collecting_data()

        self.assertEqual(len(scheduled_spiders), 2)
        self.assertIn(priority_spider.name, scheduled_spiders)

        # each worker got exactly number of scheduled spiders equal to available slots
        for ws in [ws1, ws2]:
            self.assertEqual(sum([ws.scrapy_url == scrapy_url for scrapy_url in scheduled_spiders.values()]),
                             ws.worker_slots)

    def test_crawl_time_1_slot(self):
        ws = self.mock_ws(1)
        self.db_session.commit()
        account = self.mock_account()
        spider1 = self.mock_spider(account)
        earliest_spider = self.mock_spider(account)
        spider2 = self.mock_spider(account)
        self.assertTrue(crawl_required(spider1))
        self.assertTrue(crawl_required(earliest_spider))
        self.assertTrue(crawl_required(spider2))
        # add two crawls to queue
        self.mock_crawl(spider1, crawl_date=date.today(), crawl_time=time(hour=5), status='scheduled')
        self.mock_crawl(earliest_spider, crawl_date=date.today(), crawl_time=time(hour=2), status='scheduled')
        self.mock_crawl(spider2, crawl_date=date.today(), status='scheduled')
        self.db_session.commit()

        scheduled_spiders = self.schedule_collecting_data()

        self.assertEqual(len(scheduled_spiders), 1)
        self.assertIn(earliest_spider.name, scheduled_spiders)

    def test_crawl_time_2_slots_several_workers(self):
        ws1 = self.mock_ws(1)
        ws2 = self.mock_ws(1)
        self.db_session.commit()
        account = self.mock_account()
        spider1 = self.mock_spider(account)
        earliest_spider = self.mock_spider(account)
        spider2 = self.mock_spider(account)
        self.assertTrue(crawl_required(spider1))
        self.assertTrue(crawl_required(earliest_spider))
        self.assertTrue(crawl_required(spider2))
        # add two crawls to queue
        self.mock_crawl(spider1, crawl_date=date.today(), crawl_time=time(hour=5), status='scheduled')
        self.mock_crawl(earliest_spider, crawl_date=date.today(), crawl_time=time(hour=2), status='scheduled')
        self.mock_crawl(spider2, crawl_date=date.today(), status='scheduled')
        self.db_session.commit()

        scheduled_spiders = self.schedule_collecting_data()

        self.assertEqual(len(scheduled_spiders), 2)
        self.assertIn(earliest_spider.name, scheduled_spiders)

        # each worker got exactly number of scheduled spiders equal to available slots
        for ws in [ws1, ws2]:
            self.assertEqual(sum([ws.scrapy_url == scrapy_url for scrapy_url in scheduled_spiders.values()]),
                             ws.worker_slots)

    def test_multicrawl_crawl_1_slot(self):
        ws = self.mock_ws(1)
        self.db_session.commit()
        account = self.mock_account()
        spider1 = self.mock_spider(account)
        spider2 = self.mock_spider(account)
        multicrawl_spider = self.mock_spider(account, multicrawl=True)
        self.assertTrue(crawl_required(spider1))
        self.assertTrue(crawl_required(spider2))
        self.assertTrue(crawl_required(multicrawl_spider))
        # add two crawls to queue
        self.mock_crawl(spider1, crawl_date=date.today(), status='scheduled')
        self.mock_crawl(spider2, crawl_date=date.today(), status='scheduled')
        self.mock_crawl(multicrawl_spider, crawl_date=date.today(), status='scheduled')
        self.db_session.commit()

        scheduled_spiders = self.schedule_collecting_data()

        self.assertEqual(len(scheduled_spiders), 1)
        self.assertIn(multicrawl_spider.name, scheduled_spiders)

    def test_multicrawl_crawl_2_slots_several_workers(self):
        ws1 = self.mock_ws(1)
        ws2 = self.mock_ws(1)
        self.db_session.commit()
        account = self.mock_account()
        spider1 = self.mock_spider(account)
        spider2 = self.mock_spider(account)
        multicrawl = self.mock_spider(account, multicrawl=True)
        self.assertTrue(crawl_required(spider1))
        self.assertTrue(crawl_required(spider2))
        self.assertTrue(crawl_required(multicrawl))
        # add two crawls to queue
        self.mock_crawl(spider1, crawl_date=date.today(), status='scheduled')
        self.mock_crawl(spider2, crawl_date=date.today(), status='scheduled')
        self.mock_crawl(multicrawl, crawl_date=date.today(), status='scheduled')
        self.db_session.commit()

        scheduled_spiders = self.schedule_collecting_data()

        self.assertEqual(len(scheduled_spiders), 2)
        self.assertIn(multicrawl.name, scheduled_spiders)

        # each worker got exactly number of scheduled spiders equal to available slots
        for ws in [ws1, ws2]:
            self.assertEqual(sum([ws.scrapy_url == scrapy_url for scrapy_url in scheduled_spiders.values()]),
                             ws.worker_slots)

    def test_priority_over_crawl_time(self):
        ws = self.mock_ws(1)
        self.db_session.commit()
        account = self.mock_account()
        spider1 = self.mock_spider(account)
        earliest_spider = self.mock_spider(account)
        priority_spider = self.mock_spider(account, priority=1)
        self.assertTrue(crawl_required(spider1))
        self.assertTrue(crawl_required(earliest_spider))
        self.assertTrue(crawl_required(priority_spider))
        # add two crawls to queue
        self.mock_crawl(spider1, crawl_date=date.today(), crawl_time=time(hour=5), status='scheduled')
        self.mock_crawl(earliest_spider, crawl_date=date.today(), crawl_time=time(hour=2), status='scheduled')
        self.mock_crawl(priority_spider, crawl_date=date.today(), status='scheduled')
        self.db_session.commit()

        scheduled_spiders = self.schedule_collecting_data()

        self.assertEqual(len(scheduled_spiders), 1)
        self.assertIn(priority_spider.name, scheduled_spiders)

    def test_priority_over_crawl_time_several_workers(self):
        ws1 = self.mock_ws(1)
        ws2 = self.mock_ws(1)
        self.db_session.commit()
        account = self.mock_account()
        earliest_spider = self.mock_spider(account)
        priority_spider1 = self.mock_spider(account, priority=1)
        priority_spider2 = self.mock_spider(account, priority=1)
        self.assertTrue(crawl_required(earliest_spider))
        self.assertTrue(crawl_required(priority_spider1))
        self.assertTrue(crawl_required(priority_spider2))
        # add two crawls to queue
        self.mock_crawl(earliest_spider, crawl_date=date.today(), crawl_time=time(hour=0), status='scheduled')
        self.mock_crawl(priority_spider1, crawl_date=date.today(), status='scheduled')
        self.mock_crawl(priority_spider2, crawl_date=date.today(), status='scheduled')
        self.db_session.commit()

        scheduled_spiders = self.schedule_collecting_data()

        self.assertEqual(len(scheduled_spiders), 2)
        self.assertIn(priority_spider1.name, scheduled_spiders)
        self.assertIn(priority_spider2.name, scheduled_spiders)
        # each worker got exactly number of scheduled spiders equal to available slots
        for ws in [ws1, ws2]:
            self.assertEqual(sum([ws.scrapy_url == scrapy_url for scrapy_url in scheduled_spiders.values()]),
                             ws.worker_slots)

    def test_multicrawl_over_priority(self):
        ws = self.mock_ws(1)
        self.db_session.commit()
        account = self.mock_account()
        spider1 = self.mock_spider(account)
        priority_spider = self.mock_spider(account, priority=1)
        multicrawl_spider = self.mock_spider(account, multicrawl=True)
        self.assertTrue(crawl_required(spider1))
        self.assertTrue(crawl_required(priority_spider))
        self.assertTrue(crawl_required(multicrawl_spider))
        # add two crawls to queue
        self.mock_crawl(spider1, crawl_date=date.today(), status='scheduled')
        self.mock_crawl(priority_spider, crawl_date=date.today(), status='scheduled')
        self.mock_crawl(multicrawl_spider, crawl_date=date.today(), status='scheduled')
        self.db_session.commit()

        scheduled_spiders = self.schedule_collecting_data()

        self.assertEqual(len(scheduled_spiders), 1)
        self.assertIn(multicrawl_spider.name, scheduled_spiders)

    def test_multicrawl_over_priority_several_workers(self):
        ws1 = self.mock_ws(1)
        ws2 = self.mock_ws(1)
        self.db_session.commit()
        account = self.mock_account()
        priority_spider = self.mock_spider(account, priority=1)
        multicrawl_spider1 = self.mock_spider(account, multicrawl=True)
        multicrawl_spider2 = self.mock_spider(account, multicrawl=True)
        self.assertTrue(crawl_required(priority_spider))
        self.assertTrue(crawl_required(multicrawl_spider1))
        self.assertTrue(crawl_required(multicrawl_spider2))
        # add two crawls to queue
        self.mock_crawl(priority_spider, crawl_date=date.today(), status='scheduled')
        self.mock_crawl(multicrawl_spider1, crawl_date=date.today(), status='scheduled')
        self.mock_crawl(multicrawl_spider2, crawl_date=date.today(), status='scheduled')
        self.db_session.commit()

        scheduled_spiders = self.schedule_collecting_data()

        self.assertEqual(len(scheduled_spiders), 2)
        self.assertIn(multicrawl_spider1.name, scheduled_spiders)
        self.assertIn(multicrawl_spider2.name, scheduled_spiders)
        # each worker got exactly number of scheduled spiders equal to available slots
        for ws in [ws1, ws2]:
            self.assertEqual(sum([ws.scrapy_url == scrapy_url for scrapy_url in scheduled_spiders.values()]),
                             ws.worker_slots)

    def test_multicrawl_and_priority(self):
        ws = self.mock_ws(1)
        self.db_session.commit()
        account = self.mock_account()
        spider1 = self.mock_spider(account)
        multicrawl_spider = self.mock_spider(account, multicrawl=True)
        priority_multicrawl_spider = self.mock_spider(account, multicrawl=True, priority=1)
        self.assertTrue(crawl_required(spider1))
        self.assertTrue(crawl_required(multicrawl_spider))
        self.assertTrue(crawl_required(priority_multicrawl_spider))
        # add two crawls to queue
        self.mock_crawl(spider1, crawl_date=date.today(), status='scheduled')
        self.mock_crawl(multicrawl_spider, crawl_date=date.today(), status='scheduled')
        self.mock_crawl(priority_multicrawl_spider, crawl_date=date.today(), status='scheduled')
        self.db_session.commit()

        scheduled_spiders = self.schedule_collecting_data()

        self.assertEqual(len(scheduled_spiders), 1)
        self.assertIn(priority_multicrawl_spider.name, scheduled_spiders)

    def test_multicrawl_and_priority_several_workers(self):
        ws1 = self.mock_ws(1)
        ws2 = self.mock_ws(1)
        self.db_session.commit()
        account = self.mock_account()
        multicrawl_spider = self.mock_spider(account, multicrawl=True)
        priority_multicrawl_spider1 = self.mock_spider(account, multicrawl=True, priority=2)
        priority_multicrawl_spider2 = self.mock_spider(account, multicrawl=True, priority=1)
        self.assertTrue(crawl_required(multicrawl_spider))
        self.assertTrue(crawl_required(priority_multicrawl_spider1))
        self.assertTrue(crawl_required(priority_multicrawl_spider2))
        # add two crawls to queue
        self.mock_crawl(multicrawl_spider, crawl_date=date.today(), status='scheduled')
        self.mock_crawl(priority_multicrawl_spider1, crawl_date=date.today(), status='scheduled')
        self.mock_crawl(priority_multicrawl_spider2, crawl_date=date.today(), status='scheduled')
        self.db_session.commit()

        scheduled_spiders = self.schedule_collecting_data()

        self.assertEqual(len(scheduled_spiders), 2)
        self.assertIn(priority_multicrawl_spider1.name, scheduled_spiders)
        self.assertIn(priority_multicrawl_spider2.name, scheduled_spiders)
        # each worker got exactly number of scheduled spiders equal to available slots
        for ws in [ws1, ws2]:
            self.assertEqual(sum([ws.scrapy_url == scrapy_url for scrapy_url in scheduled_spiders.values()]),
                             ws.worker_slots)

    def test_multicrawl_over_crawl_time(self):
        ws = self.mock_ws(1)
        self.db_session.commit()
        account = self.mock_account()
        spider1 = self.mock_spider(account)
        earliest_spider = self.mock_spider(account)
        multicrawl_spider = self.mock_spider(account, multicrawl=True)
        self.assertTrue(crawl_required(spider1))
        self.assertTrue(crawl_required(earliest_spider))
        self.assertTrue(crawl_required(multicrawl_spider))
        # add two crawls to queue
        self.mock_crawl(spider1, crawl_date=date.today(), crawl_time=time(hour=5), status='scheduled')
        self.mock_crawl(earliest_spider, crawl_date=date.today(), crawl_time=time(hour=2), status='scheduled')
        self.mock_crawl(multicrawl_spider, crawl_date=date.today(), status='scheduled')
        self.db_session.commit()

        scheduled_spiders = self.schedule_collecting_data()

        self.assertEqual(len(scheduled_spiders), 1)
        self.assertIn(multicrawl_spider.name, scheduled_spiders)

    def test_multicrawl_over_crawl_time_several_workers(self):
        ws1 = self.mock_ws(1)
        ws2 = self.mock_ws(1)
        self.db_session.commit()
        account = self.mock_account()
        earliest_spider = self.mock_spider(account)
        multicrawl_spider1 = self.mock_spider(account, multicrawl=True)
        multicrawl_spider2 = self.mock_spider(account, multicrawl=True)
        self.assertTrue(crawl_required(earliest_spider))
        self.assertTrue(crawl_required(multicrawl_spider1))
        self.assertTrue(crawl_required(multicrawl_spider2))
        # add two crawls to queue
        self.mock_crawl(earliest_spider, crawl_date=date.today(), crawl_time=time(hour=0), status='scheduled')
        self.mock_crawl(multicrawl_spider1, crawl_date=date.today(), status='scheduled')
        self.mock_crawl(multicrawl_spider2, crawl_date=date.today(), status='scheduled')
        self.db_session.commit()

        scheduled_spiders = self.schedule_collecting_data()

        self.assertEqual(len(scheduled_spiders), 2)
        self.assertIn(multicrawl_spider1.name, scheduled_spiders)
        self.assertIn(multicrawl_spider2.name, scheduled_spiders)
        # each worker got exactly number of scheduled spiders equal to available slots
        for ws in [ws1, ws2]:
            self.assertEqual(sum([ws.scrapy_url == scrapy_url for scrapy_url in scheduled_spiders.values()]),
                             ws.worker_slots)

    def test_multicrawl_over_priority_and_crawl_time(self):
        ws = self.mock_ws(1)
        self.db_session.commit()
        account = self.mock_account()
        spider1 = self.mock_spider(account)
        earliest_spider = self.mock_spider(account)
        priority_spider = self.mock_spider(account, priority=1)
        multicrawl_spider = self.mock_spider(account, multicrawl=True)
        self.assertTrue(crawl_required(spider1))
        self.assertTrue(crawl_required(earliest_spider))
        self.assertTrue(crawl_required(priority_spider))
        self.assertTrue(crawl_required(multicrawl_spider))
        # add two crawls to queue
        self.mock_crawl(spider1, crawl_date=date.today(), crawl_time=time(hour=5), status='scheduled')
        self.mock_crawl(earliest_spider, crawl_date=date.today(), crawl_time=time(hour=2), status='scheduled')
        self.mock_crawl(priority_spider, crawl_date=date.today(), status='scheduled')
        self.mock_crawl(multicrawl_spider, crawl_date=date.today(), status='scheduled')
        self.db_session.commit()

        scheduled_spiders = self.schedule_collecting_data()

        self.assertEqual(len(scheduled_spiders), 1)
        self.assertIn(multicrawl_spider.name, scheduled_spiders)

    def test_multicrawl_over_priority_and_crawl_time_several_workers(self):
        ws1 = self.mock_ws(1)
        ws2 = self.mock_ws(1)
        self.db_session.commit()
        account = self.mock_account()
        earliest_spider = self.mock_spider(account)
        priority_spider = self.mock_spider(account, priority=1)
        multicrawl_spider1 = self.mock_spider(account, multicrawl=True)
        multicrawl_spider2 = self.mock_spider(account, multicrawl=True)
        self.assertTrue(crawl_required(earliest_spider))
        self.assertTrue(crawl_required(priority_spider))
        self.assertTrue(crawl_required(multicrawl_spider1))
        self.assertTrue(crawl_required(multicrawl_spider2))
        # add two crawls to queue
        self.mock_crawl(earliest_spider, crawl_date=date.today(), crawl_time=time(hour=0), status='scheduled')
        self.mock_crawl(priority_spider, crawl_date=date.today(), status='scheduled')
        self.mock_crawl(multicrawl_spider1, crawl_date=date.today(), status='scheduled')
        self.mock_crawl(multicrawl_spider2, crawl_date=date.today(), status='scheduled')
        self.db_session.commit()

        scheduled_spiders = self.schedule_collecting_data()

        self.assertEqual(len(scheduled_spiders), 2)
        self.assertIn(multicrawl_spider1.name, scheduled_spiders)
        self.assertIn(multicrawl_spider2.name, scheduled_spiders)
        # each worker got exactly number of scheduled spiders equal to available slots
        for ws in [ws1, ws2]:
            self.assertEqual(sum([ws.scrapy_url == scrapy_url for scrapy_url in scheduled_spiders.values()]),
                             ws.worker_slots)

    def test_priority_and_crawl_time_several_workers(self):
        ws1 = self.mock_ws(1)
        ws2 = self.mock_ws(1)
        self.db_session.commit()
        account = self.mock_account()
        second_earliest_spider = self.mock_spider(account)
        earliest_spider = self.mock_spider(account)
        priority_spider = self.mock_spider(account, priority=1)
        self.assertTrue(crawl_required(second_earliest_spider))
        self.assertTrue(crawl_required(earliest_spider))
        self.assertTrue(crawl_required(priority_spider))
        # add two crawls to queue
        self.mock_crawl(second_earliest_spider, crawl_date=date.today(), crawl_time=time(hour=5), status='scheduled')
        self.mock_crawl(earliest_spider, crawl_date=date.today(), crawl_time=time(hour=2), status='scheduled')
        self.mock_crawl(priority_spider, crawl_date=date.today(), status='scheduled')
        self.db_session.commit()

        scheduled_spiders = self.schedule_collecting_data()

        self.assertEqual(len(scheduled_spiders), 2)
        self.assertIn(priority_spider.name, scheduled_spiders)
        self.assertIn(earliest_spider.name, scheduled_spiders)
        # each worker got exactly number of scheduled spiders equal to available slots
        for ws in [ws1, ws2]:
            self.assertEqual(sum([ws.scrapy_url == scrapy_url for scrapy_url in scheduled_spiders.values()]),
                             ws.worker_slots)

    def test_multicrawl_and_priority_several_workers(self):
        ws1 = self.mock_ws(1)
        ws2 = self.mock_ws(1)
        self.db_session.commit()
        account = self.mock_account()
        second_priority_spider = self.mock_spider(account, priority=1)
        priority_spider = self.mock_spider(account, priority=2)
        multicrawl_spider = self.mock_spider(account, multicrawl=True)
        self.assertTrue(crawl_required(second_priority_spider))
        self.assertTrue(crawl_required(priority_spider))
        self.assertTrue(crawl_required(multicrawl_spider))
        # add two crawls to queue
        self.mock_crawl(second_priority_spider, crawl_date=date.today(), status='scheduled')
        self.mock_crawl(priority_spider, crawl_date=date.today(), status='scheduled')
        self.mock_crawl(multicrawl_spider, crawl_date=date.today(), status='scheduled')
        self.db_session.commit()

        scheduled_spiders = self.schedule_collecting_data()

        self.assertEqual(len(scheduled_spiders), 2)
        self.assertIn(multicrawl_spider.name, scheduled_spiders)
        self.assertIn(priority_spider.name, scheduled_spiders)
        # each worker got exactly number of scheduled spiders equal to available slots
        for ws in [ws1, ws2]:
            self.assertEqual(sum([ws.scrapy_url == scrapy_url for scrapy_url in scheduled_spiders.values()]),
                             ws.worker_slots)

    def test_multicrawl_and_crawl_time_several_workers(self):
        ws1 = self.mock_ws(1)
        ws2 = self.mock_ws(1)
        self.db_session.commit()
        account = self.mock_account()
        second_earliest_spider = self.mock_spider(account)
        earliest_spider = self.mock_spider(account)
        multicrawl_spider = self.mock_spider(account, multicrawl=True)
        self.assertTrue(crawl_required(second_earliest_spider))
        self.assertTrue(crawl_required(earliest_spider))
        self.assertTrue(crawl_required(multicrawl_spider))
        # add two crawls to queue
        self.mock_crawl(second_earliest_spider, crawl_date=date.today(), crawl_time=time(hour=5), status='scheduled')
        self.mock_crawl(earliest_spider, crawl_date=date.today(), crawl_time=time(hour=2), status='scheduled')
        self.mock_crawl(multicrawl_spider, crawl_date=date.today(), status='scheduled')
        self.db_session.commit()

        scheduled_spiders = self.schedule_collecting_data()

        self.assertEqual(len(scheduled_spiders), 2)
        self.assertIn(multicrawl_spider.name, scheduled_spiders)
        self.assertIn(earliest_spider.name, scheduled_spiders)
        # each worker got exactly number of scheduled spiders equal to available slots
        for ws in [ws1, ws2]:
            self.assertEqual(sum([ws.scrapy_url == scrapy_url for scrapy_url in scheduled_spiders.values()]),
                             ws.worker_slots)

    def test_multicrawl_and_priority_and_crawl_time_several_workers(self):
        ws1 = self.mock_ws(1)
        ws2 = self.mock_ws(1)
        ws3 = self.mock_ws(1)
        self.db_session.commit()
        account = self.mock_account()
        second_earliest_spider = self.mock_spider(account)
        earliest_spider = self.mock_spider(account)
        priority_spider = self.mock_spider(account, priority=1)
        multicrawl_spider = self.mock_spider(account, multicrawl=True)
        self.assertTrue(crawl_required(second_earliest_spider))
        self.assertTrue(crawl_required(earliest_spider))
        self.assertTrue(crawl_required(priority_spider))
        self.assertTrue(crawl_required(multicrawl_spider))
        # add two crawls to queue
        self.mock_crawl(second_earliest_spider, crawl_date=date.today(), crawl_time=time(hour=5), status='scheduled')
        self.mock_crawl(earliest_spider, crawl_date=date.today(), crawl_time=time(hour=2), status='scheduled')
        self.mock_crawl(priority_spider, crawl_date=date.today(), status='scheduled')
        self.mock_crawl(multicrawl_spider, crawl_date=date.today(), status='scheduled')
        self.db_session.commit()

        scheduled_spiders = self.schedule_collecting_data()

        self.assertEqual(len(scheduled_spiders), 3)
        self.assertIn(multicrawl_spider.name, scheduled_spiders)
        self.assertIn(priority_spider.name, scheduled_spiders)
        self.assertIn(earliest_spider.name, scheduled_spiders)
        # each worker got exactly number of scheduled spiders equal to available slots
        for ws in [ws1, ws2, ws3]:
            self.assertEqual(sum([ws.scrapy_url == scrapy_url for scrapy_url in scheduled_spiders.values()]),
                             ws.worker_slots)

    def test_predefined_worker_server_empty_slots(self):
        ws1 = self.mock_ws(1)
        empty_slot_ws = self.mock_ws(0)
        self.db_session.commit()
        account = self.mock_account()
        spider1 = self.mock_spider(account)
        priority_spider = self.mock_spider(account, priority=1)
        self.assertTrue(crawl_required(spider1))
        self.assertTrue(crawl_required(priority_spider))
        # add two crawls to queue
        self.mock_crawl(spider1, crawl_date=date.today(), status='scheduled')
        self.mock_crawl(priority_spider, crawl_date=date.today(), status='scheduled', ws_id=empty_slot_ws.id)
        self.db_session.commit()

        scheduled_spiders = self.schedule_collecting_data()

        self.assertEqual(len(scheduled_spiders), 1)
        self.assertIn(spider1.name, scheduled_spiders)

    def test_predefined_worker_server(self):
        ws1 = self.mock_ws(1)
        predefined_ws = self.mock_ws(1)
        self.db_session.commit()
        account = self.mock_account()
        spider1 = self.mock_spider(account)
        predefined_ws_spider = self.mock_spider(account, priority=1)
        self.assertTrue(crawl_required(spider1))
        self.assertTrue(crawl_required(predefined_ws_spider))
        # add two crawls to queue
        self.mock_crawl(spider1, crawl_date=date.today(), status='scheduled')
        self.mock_crawl(predefined_ws_spider, crawl_date=date.today(), status='scheduled', ws_id=predefined_ws.id)
        self.db_session.commit()

        scheduled_spiders = self.schedule_collecting_data()

        self.assertEqual(len(scheduled_spiders), 2)
        self.assertIn(predefined_ws_spider.name, scheduled_spiders)
        self.assertEqual(scheduled_spiders[predefined_ws_spider.name], predefined_ws.scrapy_url)

    def test_predefined_worker_server_ignored_if_not_exits(self):
        ws = self.mock_ws(1)
        self.db_session.commit()
        non_existante_ws_id = ws.id + 1
        account = self.mock_account()
        spider1 = self.mock_spider(account)
        priority_spider = self.mock_spider(account, priority=1)
        self.assertTrue(crawl_required(spider1))
        self.assertTrue(crawl_required(priority_spider))
        # add two crawls to queue
        self.mock_crawl(spider1, crawl_date=date.today(), status='scheduled')
        self.mock_crawl(priority_spider, crawl_date=date.today(), status='scheduled', ws_id=non_existante_ws_id)
        self.db_session.commit()

        scheduled_spiders = self.schedule_collecting_data()

        self.assertEqual(len(scheduled_spiders), 1)
        self.assertIn(priority_spider.name, scheduled_spiders)

    def test_priority_over_predefined(self):
        ws = self.mock_ws(1)
        self.db_session.commit()
        account = self.mock_account()
        predefined_ws_spider = self.mock_spider(account)
        priority_spider = self.mock_spider(account, priority=1)
        self.assertTrue(crawl_required(predefined_ws_spider))
        self.assertTrue(crawl_required(priority_spider))
        # add two crawls to queue
        self.mock_crawl(predefined_ws_spider, crawl_date=date.today(), status='scheduled', ws_id=ws.id)
        self.mock_crawl(priority_spider, crawl_date=date.today(), status='scheduled')
        self.db_session.commit()

        scheduled_spiders = self.schedule_collecting_data()

        self.assertEqual(len(scheduled_spiders), 1)
        self.assertIn(priority_spider.name, scheduled_spiders)

    def test_crawl_time_over_predefined(self):
        ws = self.mock_ws(1)
        self.db_session.commit()
        account = self.mock_account()
        predefined_ws_spider = self.mock_spider(account)
        earliest_spider = self.mock_spider(account)
        self.assertTrue(crawl_required(predefined_ws_spider))
        self.assertTrue(crawl_required(earliest_spider))
        # add two crawls to queue
        self.mock_crawl(predefined_ws_spider, crawl_date=date.today(), status='scheduled', ws_id=ws.id)
        self.mock_crawl(earliest_spider, crawl_date=date.today(), crawl_time=time(hour=0), status='scheduled')
        self.db_session.commit()

        scheduled_spiders = self.schedule_collecting_data()

        self.assertEqual(len(scheduled_spiders), 1)
        self.assertIn(earliest_spider.name, scheduled_spiders)

    def test_multicrawl_over_predefined(self):
        ws = self.mock_ws(1)
        self.db_session.commit()
        account = self.mock_account()
        predefined_ws_spider = self.mock_spider(account)
        multicrawl_spider = self.mock_spider(account, multicrawl=True)
        self.assertTrue(crawl_required(predefined_ws_spider))
        self.assertTrue(crawl_required(multicrawl_spider))
        # add two crawls to queue
        self.mock_crawl(predefined_ws_spider, crawl_date=date.today(), status='scheduled', ws_id=ws.id)
        self.mock_crawl(multicrawl_spider, crawl_date=date.today(), status='scheduled')
        self.db_session.commit()

        scheduled_spiders = self.schedule_collecting_data()

        self.assertEqual(len(scheduled_spiders), 1)
        self.assertIn(multicrawl_spider.name, scheduled_spiders)

    def test_exception_when_scheduling(self):
        ws = self.mock_ws(1)
        self.db_session.commit()
        account = self.mock_account()
        spider = self.mock_spider(account)
        self.assertTrue(crawl_required(spider))
        # add two crawls to queue
        crawl = self.mock_crawl(spider, crawl_date=date.today(), status='scheduled')
        self.db_session.commit()

        with mock.patch('product_spiders.scheduler.scheduler.run_spider') as MockClass:
            MockClass.side_effect = SchedulingError()
            with mock.patch('product_spiders.scheduler.scheduler.get_jobs_list') as MockClass2:
                MockClass2.return_value = {'running': [], 'pending': []}
                schedule_crawls_on_workers(self.db_session)

        self.assertEqual(crawl.status, 'schedule_errors')


if __name__ == '__main__':
    unittest.main()
