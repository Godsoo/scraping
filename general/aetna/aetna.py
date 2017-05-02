from scrapex import *
import time
import sys
import json
import urlparse
import re


def search_plan(state):
	url = plansearch_url % state
	logger.info( url )
	doc = s.load_html( site_url )
	logger.info(doc)
	# plans = []
	# plans_q = doc.q( '//div' )
	# logger.info(len(plans_q))
	# for plan in plans_q:
	# 	plans.append( { 'value': plan.x('@value'), 'text': plan.x('text()') } )
	# logger.info( plans )

# does not seem to work when set use_cache as True
# site is full of javascript
s = Scraper(
	use_cache=False, #enable cache globally
	retries=3, 
	timeout=60,
	# proxy_file = '/users/cung/scrape/proxy.txt'
	)

logger = s.logger

site_name = 'aetna'
site_url = 'http://www.aetna.com/dse/search?site_id=medicare&langpref=en&tabKey=tab2&site_id=medicare&langpref=en&tabKey=tab2'
search_url = 'http://www.aetna.com/dse/search/results?searchQuery=Acute+Rehab&geoSearch=85117&q=Acute+Rehab&r=85117&pagination.offset=25&zipCode=85117&distance=25&filterValues=&useZipForLatLonSearch=true&fastProduct=&currentSelectedPlan=&selectedMemberForZip=&sessionCachingKey=&loggedInZip=true&modalSelectedPlan=MEHMO&isTab1Clicked=&isTab2Clicked=&quickSearchTypeMainTypeAhead=&quickSearchTypeThrCol=&mainTypeAheadSelectionVal=&thrdColSelectedVal=&isMultiSpecSelected=&hospitalNavigator=&productPlanName=Aetna+Medicare%E2%84%A0+Plan+(HMO)&hospitalNameFromDetails=&planCodeFromDetails=&hospitalFromDetails=false&aetnaId=&Quicklastname=&Quickfirstname=&QuickZipcode=&QuickCoordinates=&quickSearchTerm=&ipaFromDetails=&ipaFromResults=&ipaNameForProvider=&porgId=&officeLocation=&otherOfficeProviderName=&officesLinkIsTrueDetails=false&groupnavigator=&groupFromDetails=&groupFromResults=&groupNameForProvider=&suppressFASTCall=&classificationLimit=&suppressFASTDocCall=true&axcelSpecialtyAddCatTierTrueInd=&suppressHLCall=&pcpSearchIndicator=&specSearchIndicator=&stateCode=&geoMainTypeAheadLastQuickSelectedVal=&geoBoxSearch=&lastPageTravVal=&debugInfo=&linkwithoutplan=&site_id=medicare&langPref=en&sendZipLimitInd=&ioeqSelectionInd=&ioe_qType=&sortOrder=&healthLineErrorMessage=&QuickGeoType=&originalWhereBoxVal=&quickCategoryCode=&comServletUrlWithParms=http%3A%2F%2Fwww30.aetna.com%2Fcom%2Forgmapping%2FCOMServlet%3FrequestoruniqueKey%3Dhttp%253A%252F%252Fwww.aetna.com%252Fdse%252Fsearch%253Fsite_id%253Dmedicare%26keyType%3DURL%26commPurpose%3DDSE%26callingPage%3Dcall_servlet.html&orgId=39934088&orgArrangementid=19200955&productPlanPipeName=MEHMO%7CAetna+Medicare(SM)+Plan+(HMO)&quickZipCodeFromFirstHLCall=&quickStateCodeFromFirstHLCall='
plansearch_url = 'http://www.aetna.com/dse/search/populateStateProducts?searchVal=%s'

zipcodes = json.load(open('zipcodes_byfirst3_groupedbystate.json'))

if __name__ == '__main__':
	# logger.info( zipcodes )
	search_plan('AZ')

