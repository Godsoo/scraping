from scrapex import *
import time
import sys
import json
from bs4 import BeautifulSoup

def get_product_urls(pages_num) :

	hdnReportNumberning = ''

	req_url = 'http://www.infochoice.com.au/handler/productselectorreporthandler.ashx'

	req_header = {	'Host'				: 'www.infochoice.com.au',
					'Accept'			: '*/*',
					'Accept-Language'	: 'en-US,en;q=0.5',
					'Accept-Encoding'	: 'gzip, deflate',
					'Content-Type'		: 'application/x-www-form-urlencoded',
					'X-Requested-With'	: 'XMLHttpRequest',
					'Referer'			: site_url,
					}

	PageNo = 0

	while ( True ) :

		PageNo = PageNo + 1

		req_param = { 
					'search_text'				:'',
					'ctl01$hdnVertical'			:'SavingsAccount',
					'ctl01$hdnScreen'			:'InfoChoice:Savings+Account:Sales+Funnel:Compare+Savings+Account',
					'ctl01$hdnDevice'			:'desktop',
					'ctl01$hdnBackToResultsUrl'	:'/banking/savings-account/list.aspx',
					'Vertical'					:'SavingsAccount',
					'ProductSelectorSchemaName'	:'SavingsAccountSelector',
					'ProductDefinitionId'		:'34',
					'PublisherInstitutionId'	:'10',
					'PinnedProductDataIds'		:'',
					'ReportName'				:'Rate',
					'SortField'					:'MainSortColumn',
					'SortOrder'					:'Descending',
					'SelectedTabName'			:'',
					'SortReportName'			:'ProductList_34_Rate',
					'MaxResultCount'			:'20',
					'IsGroupBy'					:'True',
					'GroupBy'					:'Apply',
					'IsPaging'					:'True',
					'PageNo'					:str(PageNo),
					'PageSize'					:'20',
					'PageRange'					:'5',
					'rawUrl'					:'/banking/savings-account/list.aspx?search_text=',
					'StateIds'					:'-1',
					'SavingsAmount'				:'$10,000',
					'ProductType'				:'Standard',
					'ProductType'				:'Online',
					'AccountPurpose'			:'AtCallSavings',
					'ctl01$PageContent$ProductSelectorReport$hdnReportNumberning': hdnReportNumberning,
					'WebsitePanelIdMainReport'	:'8054',
					'chkGroupBy'				:'on',
					'chkGroupByApply'			:'on',
						}

		doc = s.load(url = req_url, headers = req_header, post = req_param)

		product_urls = doc.q('//span[@id="IC_ProductList34Rate"]/table/tr[contains(@class,"productId")]/td[3]/a[@class="reportProductLink"]/@href')

		if ( product_urls and ((pages_num == 'all') or (PageNo <= int(pages_num))) ) :

			for product_url in product_urls :
				get_product_info( '' + product_url.nodevalue() )

			logger.info( 'Page %d done.' % PageNo)

			hdnReportNumberning = hdnReportNumberning + ',,'
		else :
			break


def convert_imgsrc2text(img_url) :

	if ( ('true' in img_url) or ('darkblue-tick' in img_url) ) :
		return 'true'

	if ( ('cross-grey' in img_url) or ('grey-cross' in img_url) ) :
		return 'false'

	return ''


def get_product_info(product_url) :

	doc = s.load(url = product_url)

	######################################################  Product Name  #####################################################

	product_name = doc.x('//div[@class="contentPanel"]/div[@class="backgroungFactsheetTitle"]/text()').strip()

	#########################################   Variable Interest Rates: All Balances  ################################################

	tbl_Variable_Interest_Rates = doc.q('//table[@id="ctl01_PageContent_ctl01_RatesTableGrid"]//tr[contains(@class,"ratesTableRow ")]')

	Variable_Interest_Rates = []

	for tr_rate in tbl_Variable_Interest_Rates :

		price     = tr_rate.x('td[1]/div/text()').strip()
		price     = tr_rate.x('td[1]/div').strip()
		logger.info( price )
		base_rate = tr_rate.x('td[2]/div/text()').strip()
		max_rate  = tr_rate.x('td[3]/div/text()').strip()

		Variable_Interest_Rates.append({
										'price'     : price,
										'base_rate' : base_rate,
										'max_rate'  : max_rate } )

	#########################################   All Benefits  ################################################

	All_Benefits = doc.q('//div[@class="benifitsSummary"]/div[contains(@class,"accountFeature")]/text()')

	temp = []

	for benefit in All_Benefits :

		temp.append( '' + benefit.nodevalue() )

	All_Benefits = temp

	s.save( [ 	 'product_name'					 	, doc.x('//div[@class="contentPanel"]/div[@class="backgroungFactsheetTitle"]/text()').strip(),

				 #########################################   Variable Interest Rates: All Balances  ################################################

				 'Variable_Interest_Rates' 		 	, Variable_Interest_Rates,

				 #########################################   All Benefits  ################################################

				 'All_Benefits'			 		 	, All_Benefits,

				 #########################################  feature icons  ###################################################

				 'No_Account_Keeping_Fee'			, convert_imgsrc2text( doc.x('//div[@class="featureIcons"]/div[@class="newBackgroundFeatures"]/p[contains(text(), "No Account Keeping Fee")]/following-sibling::img/@src') ),
				 'Internet_Banking'			 	 	, convert_imgsrc2text( doc.x('//div[@class="featureIcons"]/div[@class="newBackgroundFeatures"]/p[contains(text(), "Internet Banking")]/following-sibling::img/@src') ),
				 'Counter_Service'			 	 	, convert_imgsrc2text( doc.x('//div[@class="featureIcons"]/div[@class="newBackgroundFeatures"]/p[contains(text(), "Counter Service")]/following-sibling::img/@src') ),
				 'Phone_Banking'			 		, convert_imgsrc2text( doc.x('//div[@class="featureIcons"]/div[@class="newBackgroundFeatures"]/p[contains(text(), "Phone Banking")]/following-sibling::img/@src') ),
				 'Atm'			 		 		 	, convert_imgsrc2text( doc.x('//div[@class="featureIcons"]/div[@class="newBackgroundFeatures"]/p[contains(text(), "Atm")]/following-sibling::img/@src') ),
				 'Required_Linked_Account'		 	, convert_imgsrc2text( doc.x('//div[@class="featureIcons"]/div[@class="newBackgroundFeatures"]/p[contains(text(), "Required Linked Account")]/following-sibling::img/@src') ),

				 ####################################################   Account Details   #########################################################

				 'Account_Type'			 	 	 	, doc.x('//div[@class="label" and contains(text(), "Account Type")]/following-sibling::div[@class="details"]/text()'),
				 'Min_Opening_Amount'		 		, doc.x('//div[@class="label" and contains(text(), "Min. Opening Amount")]/following-sibling::div[@class="details"]/text()'),
				 'Min_Balance'			 		 	, doc.x('//div[@class="label" and contains(text(), "Min. Balance")]/following-sibling::div[@class="details"]/text()'),
				 'Monthly_Account_Fee'	 		 	, doc.x('//div[@class="label" and contains(text(), "Monthly Account Fee")]/following-sibling::div[@class="details"]/text()'),

				 ## Interest
				 'Interest_Calculation_Frequency'	, doc.x('//div[@class="label" and contains(text(), "Interest Calculation Frequency")]/following-sibling::div[@class="details"]/text()'),
				 'Interest_Payment_Frequency'	 	, doc.x('//div[@class="label" and contains(text(), "Interest Payment Frequency")]/following-sibling::div[@class="details"]/text()'),
				 'Interest_Paid_In_Steps'	 		, convert_imgsrc2text( doc.x('//div[@class="label" and contains(text(), "Interest Paid In Steps?")]/following-sibling::div[@class="details"]/img/@src') ),

				 ## ATM & EFTPOS Fees
				 'ATM_Withdrawal_Fee'	 			, doc.x('//div[@class="label" and contains(text(), "ATM Withdrawal Fee")]/following-sibling::div[@class="details"]/text()'),
				 'ATM_Balance_Fee'	 			 	, doc.x('//div[@class="label" and contains(text(), "ATM Balance Fee")]/following-sibling::div[@class="details"]/text()'),
				 'Daily_ATM_Withdrawal_Limit'	 	, doc.x('//div[@class="label" and contains(text(), "Daily ATM Withdrawal Limit")]/following-sibling::div[@class="details"]/text()'),
				 'EFTPOS_Fee'	 					, doc.x('//div[@class="label" and contains(text(), "EFTPOS Fee")]/following-sibling::div[@class="details"]/text()'),
				 'Debit_Card_Replacement_Fee'	 	, doc.x('//div[@class="label" and contains(text(), "Debit Card Replacement Fee")]/following-sibling::div[@class="details"]/text()'),

				 ## Fee Details
				 'Service_Fee_Frequency'	 		, doc.x('//div[@class="label" and contains(text(), "Service Fee Frequency")]/following-sibling::div[@class="details"]/text()'),
				 'Fee_Rebate_Available'	 		 	, convert_imgsrc2text( doc.x('//div[@class="label" and contains(text(), "Fee Rebate Available")]/following-sibling::div[@class="details"]/img/@src') ),
				 'Balance_Required_for_Fee_Free'	, doc.x('//div[@class="label" and contains(text(), "Balance Required for Fee-Free")]/following-sibling::div[@class="details"]/text()'),

				 ## Online Savings Account Transactions
				 'Cheque_Deposit'	 				, convert_imgsrc2text( doc.x('//div[@class="label" and contains(text(), "Cheque Deposit")]/following-sibling::div[@class="details"]/img/@src') ),
				 'Cheque_Withdrawal'	 			, convert_imgsrc2text( doc.x('//div[@class="label" and contains(text(), "Cheque Withdrawal")]/following-sibling::div[@class="details"]/img/@src') ),
				 'Direct_Credit'	 				, convert_imgsrc2text( doc.x('//div[@class="label" and contains(text(), "Direct Credit")]/following-sibling::div[@class="details"]/img/@src') ),
				 'Direct_Debit'	 				 	, convert_imgsrc2text( doc.x('//div[@class="label" and contains(text(), "Direct Debit")]/following-sibling::div[@class="details"]/img/@src') ),
				 'BPAY'	 				 		 	, convert_imgsrc2text( doc.x('//div[@class="label" and contains(text(), "BPAY")]/following-sibling::div[@class="details"]/img/@src') ),

				 ## Internet & Phone Fees
				 'Phone_Transaction_Fee'	 		, doc.x('//div[@class="label" and contains(text(), "Phone Transaction Fee")]/following-sibling::div[@class="details"]/text()'),
				 'Internet_Transaction_Fee'	 	 	, doc.x('//div[@class="label" and contains(text(), "Internet Transaction Fee")]/following-sibling::div[@class="details"]/text()'),
				 'Free_Electronic_Trans_per_Month' 	, doc.x('//div[@class="label" and contains(text(), "Free Electronic Trans. per Month")]/following-sibling::div[@class="details"]/text()'),

				 ## Counter & Cheque Fees
				 'Counter_Deposit_Fee'	 		 	, doc.x('//div[@class="label" and contains(text(), "Counter Deposit Fee")]/following-sibling::div[@class="details"]/text()'),
				 'Counter_Withdrawal_Fee'	 		, doc.x('//div[@class="label" and contains(text(), "Counter Withdrawal Fee")]/following-sibling::div[@class="details"]/text()'),
				 'Free_Counter_Trans_Per_Month'	 	, doc.x('//div[@class="label" and contains(text(), "Free Counter Trans. Per Month")]/following-sibling::div[@class="details"]/text()'),

				 'Cheque_Fee'	 				 	, doc.x('//div[@class="label" and contains(text(), "Cheque Fee")]/following-sibling::div[@class="details"]/text()'),
				 'Cheque_Dishonour_Fee'	 		 	, doc.x('//div[@class="label" and contains(text(), "Cheque Dishonour Fee")]/following-sibling::div[@class="details"]/text()'),
				 'Debit_Item_Dishonour_Fee'	 	 	, doc.x('//div[@class="label" and contains(text(), "Debit Item Dishonour Fee")]/following-sibling::div[@class="details"]/text()'),

				 ## Overseas Access
				 'Overseas_ATM_Facilities'	 	 	, doc.x('//div[@class="label" and contains(text(), "Overseas ATM Facilities")]/following-sibling::div[@class="details"]/text()'),
				 'Overseas_ATM_Balance_Fee'	 	 	, doc.x('//div[@class="label" and contains(text(), "Overseas ATM Balance Fee")]/following-sibling::div[@class="details"]/text()'),
				 'Overseas_ATM_Withdrawal_Fee'	 	, doc.x('//div[@class="label" and contains(text(), "Overseas ATM Withdrawal Fee")]/following-sibling::div[@class="details"]/text()'),
				 'Overseas_EFTPOS_Fee'	 	 	 	, doc.x('//div[@class="label" and contains(text(), "Overseas EFTPOS Fee")]/following-sibling::div[@class="details"]/text()'),
				 'OS_Emergency_Card_Replacement'	, doc.x('//div[@class="label" and contains(text(), "OS Emergency Card Replacement")]/following-sibling::div[@class="details"]/text()'),
				 'Foreign_Transaction_Fee'	 	 	, doc.x('//div[@class="label" and contains(text(), "Foreign Transaction Fee")]/following-sibling::div[@class="details"]/text()'),
				 ],
				  'history.csv' )

	return Variable_Interest_Rates


# does not seem to work when set use_cache as True
# site is full of javascript
s = Scraper(use_cache=False, retries=3, timeout=30)

logger = s.logger

site_name = 'infochoice'
site_url = 'http://www.infochoice.com.au/banking/savings-account/list.aspx?search_text='

if __name__ == '__main__':

	# get_product_urls('all') 	# for all pages
	get_product_urls('1') 	# for testing





