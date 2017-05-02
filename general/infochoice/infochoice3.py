from scrapex import *
import time
import sys
import json

def scrape_all() :
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
					'ctl01$hdnVertical'			:'TransactionAccount',
					'ctl01$hdnScreen'			:'',
					'ctl01$hdnDevice'			:'desktop',
					'ctl01$hdnBackToResultsUrl'	:'/banking/transaction-account/comparison/',
					'Vertical'					:'TransactionAccount',
					'ProductSelectorSchemaName'	:'TransactionAccountSelector',
					'ProductDefinitionId'		:'34',
					'PublisherInstitutionId'	:'10',
					'PinnedProductDataIds'		:'',
					'ReportName'				:'Rate',
					'SortField'					:'MainSortColumn',
					'SortOrder'					:'Descending',
					'SelectedTabName'			:'',
					'SortReportName'			:'ProductList_34_Rate',
					'MaxResultCount'			:'50',
					'IsGroupBy'					:'True',
					'GroupBy'					:'Apply',
					'IsPaging'					:'True',
					'PageNo'					:str(PageNo),
					'PageSize'					:'20',
					'PageRange'					:'5',
					'rawUrl'					:'/banking/transaction-account/comparison/',
					'StateIds'					:'-1',
					'TransactionAccountType'    :'Transaction',
					'ctl01$PageContent$ProductSelectorReport$hdnReportNumberning': hdnReportNumberning,
					'WebsitePanelIdMainReport'	:'13188',
					'chkGroupBy'				:'on',
					'chkGroupByApply'			:'on',
						}

		doc = s.load(url = req_url, headers = req_header, post = req_param)

		# product_urls = doc.q('//span[@id="IC_ProductList34Rate"]/table/tr[contains(@class,"productId")]/td[3]/a[@class="reportProductLink"]/@href')
		rs = doc.q("//tr[contains(@class, 'productId_')]")
		if rs:
			logger.info('page %s, rs: %s', PageNo, len(rs))
			for r in rs:
				get_product_info( r.x('td[3]/a[@class="reportProductLink"]/@href'), r)
			########## for test #######
			# if ( PageNo > 2 ):
			# 	return
			hdnReportNumberning = hdnReportNumberning + ',,'
		else :
			#finish
			break


def convert_imgsrc2text(img_url) :
	img_url = img_url.lower()
	if ( ('true' in img_url) or ('darkblue-tick' in img_url) ) :
		return 'Yes'
	if ( ('cross-grey' in img_url) or ('grey-cross' in img_url) ) :
		return 'No'
	return ''

def get_product_info(product_url, r) :
	doc = s.load(url=product_url)
	s.save( [ 	
				'_id', doc.url,
				'product_name' , doc.x('//div[@class="contentPanel"]/div[@class="backgroungFactsheetTitle"]/text()').strip(),
				
				# 'institution', doc.x("//div[@id='ctl01_PageContent_MoreFromPanel']//text()[contains(.,'More from')]").replace('More from') , #r.x("td[2]//img/@src").subreg('/([^/]+)$').rr('_small.*?$'),
				'Linked_Account_Required', r.x("td[4]"),
				'Max_Interest_Rate'		 , r.x("td[5]/strong"),
				'Max_Monthly_Interest'	 , r.x("td[6]"),
				'Base_Interest_Rate'	 , r.x("td[7]/strong"),
				'Base_Monthly_Interest'	 , r.x("td[8]"),

				 #########################################   Variable Rate  ################################################

				 # 'Variable_Rate' 		 , doc.q('//div[@class="rateSummary"]/div[@class="baseRatePanel"]/div[@class="interestRate"]/span/text()').join(' ').strip(),

				 #########################################   All Benefits  ################################################

				 'All_Benefits'			 		 	, doc.q("//div[@class='benifitsSummary']/div[contains(@class,'accountFeature')]/text()").join('\n').strip(),

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

				 ###################################################  Featured Savings Accounts  ######################################################

				 'Bankwest_Smart_eSaver_Smart_Rate_if_no_withdrawals', doc.q('//div[contains(@class, "featuredProduct")]/div[@class="productDetails"]/p/a[contains(text(), "Bankwest Smart eSaver (Smart Rate if no withdrawals)")]/../../p[@class="productDescription"]/text()').join('\n').strip(),
				 'USaver '				 							 , doc.q('//div[contains(@class, "featuredProduct")]/div[@class="productDetails"]/p/a[contains(text(), "USaver")]/../../p[@class="productDescription"]/text()').join('\n').strip(),

				 ###################################################### Calculators  ##############################################################

				 'Savings_Term_Deposits', doc.q('//div[@class="calculatorPanel"]/div[contains(@class, "list")]/h4[contains(text(), "Savings & Term Deposits")]/following-sibling::ul/li/a/text()').join('\n'),
				 'Home_Loans'			, doc.q('//div[@class="calculatorPanel"]/div[contains(@class, "list")]/h4[contains(text(), "Home Loans")]/following-sibling::ul/li/a/text()').join('\n'),
				 ],
				  target_csv_file )

def test():
	get_product_info('http://www.infochoice.com.au/banking/savings-account/bankwest/bankwest-qantas-transaction-account/33883')

s = Scraper(use_cache=False, retries=3, timeout=30, show_status_message = False)

logger = s.logger
site_url = 'http://www.infochoice.com.au/banking/transaction-account/comparison/'
target_csv_file = 'items.csv'

if __name__ == '__main__':
	scrape_all()




