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
					'Content-Type'		: 'application/x-www-form-urlencoded; charset=UTF-8',
					'X-Requested-With'	: 'XMLHttpRequest',
					'Referer'			: site_url,
					}
	PageNo = 0
	while ( True ) :
		PageNo = PageNo + 1
		req_param = { 
					'search_text'				:'',
					'ctl01$hdnVertical'			:'TermDeposit',
					'ctl01$hdnScreen'			:'InfoChoice:Savings+Account:Sales+Funnel:Term+Deposit+Interest+Rates',
					'ctl01$hdnDevice'			:'desktop',
					'ctl01$hdnBackToResultsUrl'	:'/banking/savings-account/term-deposit-interest-rates.aspx',
					'Vertical'					:'TermDeposit',
					'ProductSelectorSchemaName'	:'SavingsAccountSelector',
					'ProductDefinitionId'		:'107',
					'PublisherInstitutionId'	:'10',
					'PinnedProductDataIds'		:'',
					'ReportName'				:'Rate',
					'SortField'					:'MainSortColumn',
					'SortOrder'					:'Descending',
					'SelectedTabName'			:'',
					'SortReportName'			:'ProductList_107_Rate',
					'MaxResultCount'			:'20',
					'IsGroupBy'					:'True',
					'GroupBy'					:'Apply',
					'IsPaging'					:'True',
					'PageNo'					:str(PageNo),
					'PageSize'					:'20',
					'PageRange'					:'5',
					'rawUrl'					:'/banking/savings-account/term-deposit-interest-rates.aspx?search_text=',
					'StateIds'					:'-1',
					'SavingsAmount'				:'$10,000',
					'SavingsTerm'				:'1Year',
					'AccountType'				:'Savings',
					'AccountType'				:'Online',
					'AccountType'				:'CMA',
					'AccountPurpose'			:'FixedTerm',
					'ctl01$PageContent$ProductSelectorReport$hdnReportNumberning': hdnReportNumberning,
					'WebsitePanelIdMainReport'	:'10735',
					'chkGroupBy'				:'on',
					'chkGroupByApply'			:'on',
						}

		doc = s.load(url = req_url, headers = req_header, post = req_param)
		rs = doc.q("//tr[contains(@class, 'productId_')]")
		if rs:
			logger.info('page %s, rs: %s', PageNo, len(rs))
			for r in rs :
				get_product_info( r.x('td[3]/a[@class="reportProductLink"]/@href'), r)

			########## for test #######
			# if ( PageNo > 2 ):
			# 	return
			hdnReportNumberning = hdnReportNumberning + ',,'
		else :
			#finish
			break

def get_product_info(product_url, r) :
	doc = s.load(url = product_url)
	s.save( [ 	
				'_id', doc.url,
				'product_name'					 	, doc.x('//div[@class="contentPanel"]/div[@class="backgroungFactsheetTitle"]/text()').strip(),
				
				# 'institution', doc.x("//div[@id='ctl01_PageContent_MoreFromPanel']//text()[contains(.,'More from')]").replace('More from') , #r.x("td[2]//img/@src").subreg('/([^/]+)$').rr('_small.*?$'),
				
				'Days_90', r.x("td[4]"),
				'Days_180', r.x("td[5]"),
				'Year_1', r.x("td[6]"),
				'Years_2', r.x("td[7]"),
				'Years_3', r.x("td[8]"),
				'Years_4', r.x("td[9]"),
				'Years_5', r.x("td[10]"),
				'Rate_For_Selected_Term', r.x("td[11]/strong"),

				 #########################################   All Benefits  ################################################

				 'All_Benefits'			 		 	, doc.q("//div[@class='benifitsSummary']/div[contains(@class,'accountFeature')]").join('\n'),

				 ####################################################   Account Details   #########################################################

				 'Minimum_Amount'					, doc.x('//div[@class="label" and contains(text(), "Minimum Amount")]/following-sibling::div[@class="details"]/text()'),
				 'Maximum_Amount'					, doc.x('//div[@class="label" and contains(text(), "Maximum Amount")]/following-sibling::div[@class="details"]/text()'),
				 'Interest_Payment_Method'			, doc.x('//div[@class="label" and contains(text(), "Interest Payment Method")]/following-sibling::div[@class="details"]/text()'),
				 'Penalties_for_Early_Withdrawal'	, doc.x('//div[@class="label" and contains(text(), "Penalties for Early Withdrawal")]/following-sibling::div[@class="details"]/text()'),

				 ###################################################  Featured Term Deposits  ######################################################

				 'UBank_Term_Deposits_online', doc.q('//div[contains(@class, "featuredProduct")]/div[@class="productDetails"]/p/a[contains(text(), "UBank Term Deposits (online)")]/../../p[@class="productDescription"]/text()').join(' '),
				 'Term_Deposit'				 , doc.q('//div[contains(@class, "featuredProduct")]/div[@class="productDetails"]/p/a[contains(text(), "Term Deposit") and not(contains(text(), "Term Deposits"))]/../../p[@class="productDescription"]/text()').join(' '),

				 ###################################################### Calculators  ##############################################################

				 'Savings_Term_Deposits', doc.q('//div[@class="calculatorPanel"]/div[contains(@class, "list")]/h4[contains(text(), "Savings & Term Deposits")]/following-sibling::ul/li/a/text()').join('\n'),
				 'Home_Loans'			, doc.q('//div[@class="calculatorPanel"]/div[contains(@class, "list")]/h4[contains(text(), "Home Loans")]/following-sibling::ul/li/a/text()').join('\n'),
				 ],
				  target_csv_file )

def test():
	get_product_info('http://www.infochoice.com.au/banking/term-deposits/mystate/on-line-term-deposit/9039')

s = Scraper(use_cache=False, retries=3, timeout=30, show_status_message = False)
logger = s.logger
# site_url = 'http://www.infochoice.com.au/banking/savings-account/list.aspx?search_text='
site_url = 'http://www.infochoice.com.au/banking/savings-account/term-deposit-interest-rates.aspx?search_text='
target_csv_file = 'items.csv'

if __name__ == '__main__':
	scrape_all()
