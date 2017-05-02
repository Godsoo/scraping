from scrapex import *
import json
import time

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common import exceptions as EX
import zipfile

# configuration for proxy
manifest_json = """
{
    "version": "1.0.0",
    "manifest_version": 2,
    "name": "Chrome Proxy",
    "permissions": [
        "proxy",
        "tabs",
        "unlimitedStorage",
        "storage",
        "<all_urls>",
        "webRequest",
        "webRequestBlocking"
    ],
    "background": {
        "scripts": ["background.js"]
    },
    "minimum_chrome_version":"22.0.0"
}
"""

background_js = """
var config = {
        mode: "fixed_servers",
        rules: {
          singleProxy: {
            scheme: "http",
            host: "38.141.0.8",
            port: parseInt(60000)
          },
          bypassList: ["foobar.com"]
        }
      };

chrome.proxy.settings.set({value: config, scope: "regular"}, function() {});

function callbackFn(details) {
    return {
        authCredentials: {
            username: "silicons",
            password: "1pRnQcg87F"
        }
    };
}

chrome.webRequest.onAuthRequired.addListener(
            callbackFn,
            {urls: ["<all_urls>"]},
            ['blocking']
);
"""

pluginfile = 'proxy_auth_plugin.zip'

def start_scrape():
    logger.info('loading site...')
    doc = s.load( site_url, use_cache=False )
    logger.info('requesting json result...')
    result_json = json.loads( s.load_html( search_url, use_cache=False ) )

    for product in result_json:
        # get one tier which has max TOTAL_RATE of several tiers
        max_tier = 0
        for i in range(len(product['tiers'])):
            if float(product['tiers'][i]['BONUS_RATE']) > float(product['tiers'][max_tier]['BONUS_RATE']):
                max_tier = i

        product_result = [  'Company'     , product['Company'],
                            'Product_Name', product['Product Name'],
                            'Star_Rating' , product['Star Rating'],
                            'Total_interest_including_bonus', product['tiers'][max_tier]['TOTAL_RATE'],
                            'Bonus_interest_only'           , product['tiers'][max_tier]['BONUS_RATE'],
                            'Promotional_period_conditions' , product['Promotional period / conditions'].replace('<br/>', '\n'),    # take care of html elements such as <br/> -> \n
                            'Monthly_interest_earned', '-',
                            'Account_Keeping_Fee'    , product['Account Keeping Fee'],
                            'Minimum_opening_deposit', product['Minimum opening deposit'],
                            'Linked_Account_required', product['Linked Account required'] ]

        s.save( product_result, 'history.csv' )
        logger.info( product_result )
    logger.info( 'all done' )

def start_scrape_with_selenium():

    with zipfile.ZipFile(pluginfile, 'w') as zp:
        zp.writestr("manifest.json", manifest_json)
        zp.writestr("background.js", background_js)

    co = Options()
    co.add_argument("--start-maximized")
    co.add_extension(pluginfile)

    driver = webdriver.Chrome(chrome_options=co)
    driver.get(site_url)

    try:
        WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.XPATH, '//div[@id="dynatable"]')))
    except EX.TimeoutException:
        return

    while ( 1 ):
        for row in driver.find_elements_by_xpath('//div[@id="dynatable"]//table[@class="full-width table table-faceted-search"]/tbody/tr'):
            # print(  row.find_element_by_xpath('td[@class=" company company"]/a/img').get_attribute('value'),
            #         row.find_element_by_xpath('td[@class=" product-name"]/span/a').text.strip(),
            #         row.find_element_by_xpath('td[contains(@class, " star-rating")]/div').get_attribute('value'),
            #         row.find_element_by_xpath('td[contains(@class, "total-interest-(including-bonus)")]').text.strip(),
            #         row.find_element_by_xpath('td[contains(@class, "bonus-interest-only")]').text.strip(),
            #         row.find_element_by_xpath('td[contains(@class, "promotional-period-conditions")]').text.strip().replace('<br/>', '\n'),
            #         row.find_element_by_xpath('td[contains(@class, "monthly-interest-earned")]').text.strip(),
            #         row.find_element_by_xpath('td[contains(@class, "account-keeping-fee")]/span').get_attribute('textContent').strip(),
            #         row.find_element_by_xpath('td[contains(@class, "minimum-opening-deposit")]/span').get_attribute('textContent').strip(),
            #         row.find_element_by_xpath('td[contains(@class, "linked-account-required")]/span').get_attribute('value'))

            try:
                Star_Rating = row.find_element_by_xpath('td[contains(@class, " star-rating")]/div').get_attribute('value')
            except:
                Star_Rating = row.find_element_by_xpath('td[contains(@class, " star-rating")]/span').get_attribute('title')
            product_result = [  'Company'     , row.find_element_by_xpath('td[@class=" company company"]/a/img').get_attribute('value'),
                                'Product_Name', row.find_element_by_xpath('td[@class=" product-name"]/span/a').text.strip(),
                                'Star_Rating' , Star_Rating,
                                'Total_interest_including_bonus', row.find_element_by_xpath('td[contains(@class, "total-interest-(including-bonus)")]').text.strip(),
                                'Bonus_interest_only'           , row.find_element_by_xpath('td[contains(@class, "bonus-interest-only")]').text.strip(),
                                'Promotional_period_conditions' , row.find_element_by_xpath('td[contains(@class, "promotional-period-conditions")]').text.strip().replace('<br/>', '\n'),    # take care of html elements such as <br/> -> \n
                                'Monthly_interest_earned', row.find_element_by_xpath('td[contains(@class, "monthly-interest-earned")]').text.strip(),
                                'Account_Keeping_Fee'    , row.find_element_by_xpath('td[contains(@class, "account-keeping-fee")]/span').get_attribute('textContent').strip(),
                                'Minimum_opening_deposit', row.find_element_by_xpath('td[contains(@class, "minimum-opening-deposit")]/span').get_attribute('textContent').strip(),
                                'Linked_Account_required', 'Yes' if int(row.find_element_by_xpath('td[contains(@class, "linked-account-required")]/span').get_attribute('value')) == 1 else 'No' ]

            print( product_result )
            s.save( product_result, 'history.csv' )
            
        try:
            next_button = driver.find_element_by_xpath('//div[@id="faceted-search"]//ul[@id="dynatable-pagination-links-"]/li/a[@class="dynatable-page-link dynatable-page-next" and contains(text(), "Next")]')
            driver.execute_script('window.scrollTo(0, ' + str(next_button.location['y']) + ');')
            next_button.click()
            time.sleep(1)
        except:
            break
            
    # while ( 1 ):
    #     pass

# does not seem to work when set use_cache as True
# site is full of javascript
s = Scraper(
    use_cache=False, #enable cache globally
    retries=3, 
    timeout=60,
    proxy_file = 'proxy.txt'
    )

logger = s.logger

site_name = 'canstar'
site_url = 'https://www.canstar.com.au/compare/savings-accounts/'
search_url = 'https://widgets.canstar.com.au/widgets/api_v2/facets/data?distributor=canstar&compare_enabled=false&container=container_component&table=savingsaccounts&category=Savings+Accounts&per_page_default=20&details_url=%2Fdetails&profile=Bonus+Saver&amount=1000&state=NSW&base_url=https%3A%2F%2Fwidgets.canstar.com.au%2Fwidgets%2F&collection=canstar_savingsaccounts'

if __name__ == '__main__':
    # start_scrape()
    start_scrape_with_selenium()

