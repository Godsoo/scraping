import time
from subprocess import call
from tempfile import NamedTemporaryFile
import os

from selenium import webdriver
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities

from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementNotVisibleException

PHANTOM_PATH = '/home/innodev/phantomjs/bin/phantomjs'
DEFAULT_USER_AGENT = 'Mozilla/5.0 (X11; Ubuntu; Linux i686; rv:23.0) Gecko/20100101 Firefox/23.0'
DEFAULT_PROXY_TYPE = 'http'

class NoProxyException(Exception):
    def __str__(self):
        return 'ERROR: No proxy host!'


class PhantomJS(object):
    def __init__(self, *args, **kwargs):
        created = False
        retry = 5
        error = None
        while not created and retry:
            try:
                self._browser = PhantomJS.create_browser(*args, **kwargs)
            except Exception, e:
                retry -= 1
                error = e
            else:
                created = True

        # If error found
        if not created and error:
            raise error
        elif not created:
            raise Exception('Could not instantiate PhantomJS, an error has occurred')

    def get(self, url, sleep=5, retry=4):
        ok = False
        error = None
        while not ok and retry:
            try:
                self._browser.get(url)
                time.sleep(sleep)
            except Exception, e:
                retry -= 1
                error = e
            else:
                ok = True
        if not ok and error:
            raise error
        elif not ok:
            raise Exception('Could not get %s, an error has occurred' % url)

    def close(self):
        self._browser.quit()

    @property
    def driver(self):
        return self._browser

    @classmethod
    def create_browser(cls, user_agent=DEFAULT_USER_AGENT, proxy=None, load_images=True):
        dcap = dict(DesiredCapabilities.PHANTOMJS)
        dcap['phantomjs.page.settings.userAgent'] = user_agent
        service_args = []
        if not load_images:
            service_args.append('--load-images=no')
        if proxy:
            try:
                proxy_host = proxy['host']
            except IndexError:
                raise NoProxyException
            proxy_type = proxy.get('type', DEFAULT_PROXY_TYPE)
            proxy_auth = proxy.get('auth')
            service_args += [
                '--proxy=%s' % proxy_host,
                '--proxy-type=%s' % proxy_type,
            ]
            if proxy_auth:
                service_args.append('--proxy-auth=%s' % proxy_auth)
            browser = webdriver.PhantomJS(PHANTOM_PATH,
                                          desired_capabilities=dcap,
                                          service_args=service_args)
        else:
            browser = webdriver.PhantomJS(PHANTOM_PATH,
                                          desired_capabilities=dcap,
                                          service_args=service_args)

        browser.set_window_size(1024, 768)

        max_wait = 180
        browser.set_page_load_timeout(max_wait)
        browser.set_script_timeout(max_wait)

        return browser

def do_browser_action_tries(function, tries=10):
    try_number = 1
    while try_number <= tries:
        try:
            function()
        except TimeoutException:
            pass
        except (NoSuchElementException, ElementNotVisibleException):
            time.sleep(0.5)
        else:
            return True
    return False

def browser_load_page_with_tries(browser, url, tries=10):
    return do_browser_action_tries(lambda: browser.get(url), tries)


JS = '''
var page = require('webpage').create();
page.settings.userAgent = '%s';
var fs = require('fs');
page.open('%s', function () {

    just_wait();
});

function just_wait() {
    setTimeout(function() {
            page.switchToFrame(0);

            fs.write('%s', page.frameContent, 'w');
            phantom.exit();
    }, %s);
}
'''


def get_page(url, js=JS, user_agent=DEFAULT_USER_AGENT, proxy=None, delay=5):
    f1 = NamedTemporaryFile(delete=False, suffix='.js')
    f2 = NamedTemporaryFile(delete=False, suffix='.html')
    js = js % (user_agent, url, f2.name, delay * 1000)
    f1.write(js)
    f1.close()
    f2.close()
    args = [PHANTOM_PATH, '--load-images=no']
    if proxy:
        args.append('--proxy=%s' % proxy)
        args.append('--proxy-type=http')

    args.append(f1.name)

    call(args)
    f2 = open(f2.name)
    data = f2.read()
    os.unlink(f1.name)
    os.unlink(f2.name)
    return data

JS_WAIT = '''
var page = require('webpage').create();
page.settings.userAgent = '%s';
var fs = require('fs');
page.open('%s', function () {

    page.onResourceReceived = function(response) {
        if (response.url.search('translate_p') != -1) {
            just_wait();
        }
    }
});

function just_wait() {
    setTimeout(function() {
            page.switchToFrame(0);

            fs.write('%s', page.frameContent, 'w');
            phantom.exit();
    }, 50);
}
'''
def get_page_wait(url, js=JS_WAIT, user_agent=DEFAULT_USER_AGENT, proxy=None):
    f1 = NamedTemporaryFile(delete=False, suffix='.js')
    f2 = NamedTemporaryFile(delete=False, suffix='.html')
    js = js % (user_agent, url, f2.name)
    f1.write(js)
    f1.close()
    f2.close()
    args = [PHANTOM_PATH, '--load-images=no']
    if proxy:
        args.append('--proxy=%s' % proxy)
        args.append('--proxy-type=http')

    args.append(f1.name)

    call(args)
    f2 = open(f2.name)
    data = f2.read()
    os.unlink(f1.name)
    os.unlink(f2.name)
    return data
