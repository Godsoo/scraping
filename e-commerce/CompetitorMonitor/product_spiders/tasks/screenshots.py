import os
import time
from celery import task
from product_spiders.phantomjs import PhantomJS
from product_spiders.config import (
    DATA_DIR,
    PROXY_SERVICE_HOST,
    PROXY_SERVICE_USER,
    PROXY_SERVICE_PSWD,
)
from PIL import Image
from scrapy.http import HtmlResponse

from contrib.proxyservice import ProxyServiceAPI


from product_spiders.base_spiders.amazonspider2.scraper import AmazonScraper

def screenshot_is_blocked(response):
    if ('www.amazon.' in response.url):
        scraper = AmazonScraper()
        return scraper.antibot_protection_raised(response.body_as_unicode())
    return False

def take_save_screenshot(browser, imagedir, imagename):
    imagepath = os.path.join(imagedir, imagename)
    browser.driver.save_screenshot(imagepath + '.png')
    return imagepath


@task(time_limit=900)
def take_screenshot(url, imagename, method,
                    proxy=None,
                    retry_blocked=False,
                    proxy_service_id=None, proxy_service_profile=None,
                    proxy_service_types='', proxy_service_locations='',
                    dirname='map_images', time_sleep=10, click_xpath='',
                    slides_click_xpath='', slide_wait=0, slide_wait_from=0):

    imagedir = os.path.join(DATA_DIR, dirname)
    if not os.path.exists(imagedir):
        try:
            os.mkdir(imagedir)
        except:
            pass
    browser = PhantomJS(proxy=proxy, load_images=True)
    if method == 'scrapy_response':
        url = os.path.join(imagedir, url)

    retry = True
    retry_no = 0
    is_blocked = False
    current_proxy = None
    while retry:
        browser.get(url, sleep=time_sleep)
        if retry_blocked:
            response = HtmlResponse(url=url,
                                    encoding='utf-8',
                                    body=browser.driver.page_source)
            is_blocked = screenshot_is_blocked(response)
        if is_blocked and retry_no < 5:
            retry_no += 1
            if proxy_service_id is not None:
                proxy_service_api = ProxyServiceAPI(
                    host=PROXY_SERVICE_HOST,
                    user=PROXY_SERVICE_USER,
                    password=PROXY_SERVICE_PSWD)
                proxy_list = proxy_service_api.get_proxy_list(
                    proxy_service_id,
                    locations=proxy_service_locations,
                    types=proxy_service_types,
                    profile=proxy_service_profile,
                    blocked=current_proxy,
                    length=1)
                if proxy_list:
                    proxy_data = proxy_list[0]
                    proxy_type, proxy_host = proxy_data['url'].split('://')
                    proxy = {
                        'host': proxy_host,
                        'type': proxy_type,
                    }
                    current_proxy = [proxy_data['id']]
                    browser.close()
                    browser = PhantomJS(proxy=proxy)
            time.sleep(60)
        else:
            retry = False

    if not is_blocked:
        if click_xpath:
            for item in browser.driver.find_elements_by_xpath(click_xpath):
                if item.is_displayed():
                    item.click()

        images_paths = []

        if slides_click_xpath:
            tab_buttons = browser.driver.find_elements_by_xpath(slides_click_xpath)
            i = 0
            while i < len(tab_buttons):
                imagename_slide = imagename.split('.jpg')[0] + ('_slide_%s' % (i + 1)) + '.jpg'
                tab_buttons[i].click()
                if slide_wait and i >= slide_wait_from:
                    # print 'SLIDE WAIT => %s/%s - %s' % (i, slide_wait_from, slide_wait)
                    time.sleep(slide_wait)
                images_paths.append(take_save_screenshot(browser, imagedir, imagename_slide))
                i += 1
        else:
            images_paths.append(take_save_screenshot(browser, imagedir, imagename))

        browser.close()

        for imagepath in images_paths:
            im = Image.open(imagepath + '.png')
            new_im = Image.new('RGB', im.size, (255, 255, 255))
            new_im.paste(im, im)
            new_im.save(imagepath)

            os.unlink(imagepath + '.png')

        try:
            # If local path
            os.unlink(url)
        except:
            pass
    else:
        browser.close()
        raise Exception('Screenshot Feature: Screenshot aborted ... blocked in => %s' % url)
