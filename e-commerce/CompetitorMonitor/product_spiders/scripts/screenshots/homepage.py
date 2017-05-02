import sys
from datetime import datetime

sys.path.append('../..')

from config import BROKER_URL
from celery import Celery

IMAGES_DIR = 'home_images'

WEBSITES = {
    1464: {
        'url': 'http://www.victorianplumbing.co.uk/',
        'method': 'phantomjs',
        'proxy': None,
        'retry_blocked': False,
        'proxy_service_id': None,
        'proxy_service_profile': None,
        'proxy_service_types': '',
        'proxy_service_locations': '',
        'dirname': IMAGES_DIR,
        'time_sleep': 20,
        'slides_click_xpath': '//div[@id="vpSlideBanner"]//li[contains(@class, "tab_button")]',
        'slide_wait': 0.5},
    1465: {
        'url': 'https://victoriaplum.com/',
        'method': 'phantomjs',
        'proxy': None,
        'retry_blocked': False,
        'proxy_service_id': None,
        'proxy_service_profile': None,
        'proxy_service_types': '',
        'proxy_service_locations': '',
        'dirname': IMAGES_DIR,
        'time_sleep': 20,
        'click_xpath': '//*[@id="newsletter-modal"]//i[contains(@class, "modal__dismiss")]',
        'slides_click_xpath': '//div[@class="b-homepage__slideshow"]//ul[@class="slick-dots" and @role="tablist"]/li[contains(@id, "slick-slide")]',
        'slide_wait': 1},
    1466: {
        'url': 'http://www.bestheating.com/',
        'method': 'phantomjs',
        'proxy': None,
        'retry_blocked': False,
        'proxy_service_id': None,
        'proxy_service_profile': None,
        'proxy_service_types': '',
        'proxy_service_locations': '',
        'dirname': IMAGES_DIR,
        'time_sleep': 10,
        'click_xpath': '//a[contains(@class, "fancybox-item") and contains(@class, "fancybox-close")]'},
    1467: {
        'url': 'http://www.plumbworld.co.uk/',
        'method': 'phantomjs',
        'proxy': None,
        'retry_blocked': False,
        'proxy_service_id': None,
        'proxy_service_profile': None,
        'proxy_service_types': '',
        'proxy_service_locations': '',
        'dirname': IMAGES_DIR,
        'time_sleep': 5},
    1470: {
        'url': 'http://www.betterbathrooms.com/',
        'method': 'phantomjs',
        'proxy': None,
        'retry_blocked': False,
        'proxy_service_id': None,
        'proxy_service_profile': None,
        'proxy_service_types': '',
        'proxy_service_locations': '',
        'dirname': IMAGES_DIR,
        'time_sleep': 40,
        'click_xpath': '//button[contains(@class, "ui-dialog-titlebar-close")]',
        'slides_click_xpath': '//ul[@class="slider-nav"]/li/a',
        'slide_wait': 0.5},
}

def main():
    celery = Celery(broker=BROKER_URL)

    today = datetime.today().date()

    for website_id, kwargs in WEBSITES.items():
        kwargs['imagename'] = '%s_%s.jpg' % (str(website_id), str(today))
        celery.send_task('product_spiders.tasks.screenshots.take_screenshot', [], kwargs, queue='screenshot')


if __name__ == '__main__':
    main()
