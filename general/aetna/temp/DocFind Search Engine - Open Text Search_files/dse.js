/* The last person to modify this file is identified here:
 * Resource_Type_Infosys_Offshore
 * Resource_ID_n596307
 *
 */

CN_name = window.location.host;
function getCnNameUrl() {
	return CN_name;
}
var urlProtocol = window.location.protocol;
//var urlProtocol = "https:";
var ieVersion = IEVersionCheck();
var selectionChange = "";
var prevSelection = "";
var currentValue = "";
var isRenderLeftSection = true;
var currentGeolocationZip = null;
var whyPressed = null;
var dseDomain = getPublicDseDomainName();
var urlProtocolSecure = "https:";
var urlProtocolNonSecure = "http:";
/*var urlProtocolSecure = "http:";
var urlProtocolNonSecure = "https:";*/
var landingPage = '';
var landingPageState = 'false';
var planTypeForPublic = '';
var narrowNetworkModalCheck = true;
var chk = false;
var ie6Check = ieVersion!=null && ieVersion!='' && ieVersion < 7;
/* SR 1385 Changes start*/
var preValOfGeoBox = "";
/* SR 1385 Changes End*/

//Chrome issue for future/current plan view - n596307
var browserName = detectBrowserName();

/*-- START CHANGES P20751b ACO Branding - n596307 --*/
var locationDialogBoxFormed;
/*-- END CHANGES P20751b ACO Branding - n596307 --*/
/* Start fix for session context time our error page */
var pageNullInd = false;
/* End fix for session context time our error page */
/*-- START CHANGES P23695 Medicare Spanish Translation - n709197 --*/
var ghostTextWhatBox = "";
var ghostTextWhereBox = "";
var tellUsYourLocation = "";
var hlLocationPopUpErrorMsg = "";
var planNetworkInformation = "";
var zipCityState = "";
var ghostTextLocationBox = "";
var noneText = "";
var site_id = "";
var langPref = "";
/*-- END CHANGES P23695 Medicare Spanish Translation - n709197 --*/
/*-- Start changes for P23419a Aug16 release - N204183 --*/
var ratingReviewPleat = "";
/*-- End changes for P23419a Aug16 release - N204183 --*/
var directLinkSiteFound;
function setAnnLaunchParamSecure(){
	 $("#askann").attr('href', "javascript:askann1appidFunctionSecure();");
}

function openMedicare(){
	NIT.RaiseAgentEvent(NIT.DocFindMedicarePlanSelection);
	window.location.href = 'http://www.aetna.com/docfind/standard.do?site_id=groupmedicare';
}

function setAnnPlanSelCancel(){
	NIT.RaiseAgentEvent(NIT.DocFindPlanSelectionCancel);
}

$(document).ready(function () {
	/*--- START CHANGES P23695 Medicare Spanish Translation - n596307 ---*/
	manageGlobalVarsForCustomization();
	/*--- END CHANGES P23695 Medicare Spanish Translation - n596307 ---*/
	//content 0420
	$('#oo_tab').click(function(){
		redirectFeedback();
	});
	var stateCode = getCookie('stateCode');
	var selectedPlan = getCookie('selectedPlan');
	var currentPage = window.location.href;
	var isDetailsPage = (currentPage != null && currentPage.indexOf('search/detail') != -1);
	var isLeftLinkPage = (currentPage != null && currentPage.indexOf('search/redirect') != -1); 
	if(stateCode != null && stateCode != ''){
	    if(!isDetailsPage && !isLeftLinkPage){ 
			if($('#stateDD') != undefined){
				$('#stateDD').val(stateCode);
				prefillPlanFromStateCode(trim(stateCode));
				if(selectedPlan != null && selectedPlan != ''){
					if($("#modal_aetna_plans") != undefined){
						$('#modal_aetna_plans :selected').val(selectedPlan);
					}
				}
			}
	    }
	}
	//a tactical approach to hide 'Make My PCP/PCD' link for future providers - will be fixed later
	var hideMakeMyPCPDLinkOnDetailsPage = false;
	if(isDetailsPage){
		if(urlProtocol == urlProtocolNonSecure){
			hideMakeMyPCPDLinkOnDetailsPage = true;
		}
		else if($.getUrlVar('isFutureProvider') != null && $.getUrlVar('isFutureProvider') == 'true'){
			hideMakeMyPCPDLinkOnDetailsPage = true
		}
	}
	if(hideMakeMyPCPDLinkOnDetailsPage){
		$('#navPcpDeepLinkMedFormDetailsPage').hide();
		$('#navPcpDeepLinkDenFormDetailsPage').hide();
	}
	/*-- START CHANGES SR1399 DEC'14 - n596307 --*/
	var planDisplayName = getCookie('planDisplayName');
	var externalPlanCode = getCookie('externalPlanCode');
	var planPrefillFlowSwitch = getCookie('planPrefillFlowSwitch');
	 if(!isDetailsPage && planPrefillFlowSwitch != null && planPrefillFlowSwitch == 'true'
		 && planDisplayName != null && planDisplayName != '' && externalPlanCode != null && externalPlanCode != ''){
		 if($("#modal_aetna_plans") != undefined){
			 $('#modal_aetna_plans :selected').text(planDisplayName);
			 $('#modal_aetna_plans :selected').val(externalPlanCode);
			 continueButtonSelected();
		 }
	 }
	 //pshydv - fix - commented to fix prefilling issue
	 /*if(!isDetailsPage && planPrefillFlowSwitch != null && planPrefillFlowSwitch == 'true' 
		 && planDisplayName != null && planDisplayName == '' 
			 && externalPlanCode != null && externalPlanCode == ''){
		 searchWithOutPlanPrefillFlow("None");
	 }*/
	 /*-- END CHANGES SR1399 DEC'14 - n596307 --*/
    // listen for page events
    $.Topic( "restorePage" ).subscribe( restoreState );
    $.Topic( "savePage" ).subscribe( saveState );

    // monitor the back/forward button
    startChangeHandler();
    var currentPage = window.location.href;
    if(currentPage != null && currentPage.indexOf('search/detail') != -1){
    	populateUrlParameters();
    	var seePlans = $.getUrlVar('seePlans');
    	if(seePlans != null && seePlans == "true"){
    		/*--- START CHANGES P23695 Medicare Spanish Translation - n709197 ---*/
    		javascript:focusPanel('contentDivImg7', 'imageDivLink7', planNetworkInformation);
    		/*--- END CHANGES P23695 Medicare Spanish Translation - n709197 ---*/
    	}
    	
    	/*-- Start changes for P23419a Aug16 release - N204183 --*/
    	var seeReviewRatingsPleat = $.getUrlVar('seeReviewRatingsPleat');
    	if(seeReviewRatingsPleat != null && seeReviewRatingsPleat == "true"){
    		javascript:focusPanel('contentDivImg11', 'imageDivLink11', ratingReviewPleat);
    	}
    	/*-- End changes for P23419a Aug16 release - N204183 --*/
	/* Start Changes SR1398 Dec14 release */
    	var lastUpdatedDatabaseDocfindDate = $('#lastUpdatedDatabaseDocfindDate').text();
		if(lastUpdatedDatabaseDocfindDate != null && lastUpdatedDatabaseDocfindDate != ""){
			$('#lastUpdatedDatabaseDate').text(lastUpdatedDatabaseDocfindDate);
		}
	/* End Changes SR1398 Dec14 release */		
    }
    if($('#site_id').val()!=null && $('#site_id').val()!=undefined && $('#site_id').val()!=''){
    	$('#site_id').val($.getUrlVar('site_id'));
    }
    
    var PageLastUpdatedText = $('#PageLastUpdated').text();
    if(PageLastUpdatedText != null && PageLastUpdatedText != ''){
    	if($('#PageLastUpdatedFooter') != undefined)
    		$('#PageLastUpdatedFooter').text(PageLastUpdatedText);
    			if($('#site_id').val() == 'medicare' || $.getUrlVar('site_id') == 'medicare'){
    				$('#PageLastUpdatedFooter').prepend("");
    			}
	}

if($('#site_id').val() == 'innovationhealth' || $.getUrlVar('site_id') == 'innovationhealth'){
    	 var url = window.location.href;
    	 if(url != null && url.indexOf('www.aetna.com/dse/search?site_id=innovationhealth') != -1){
    		 window.location.href = 'http://'+getIhDseDomainNameForPublic()+'/dse/search?site_id=innovationhealth';
    	 }
    }
if($('#site_id').val()!=null && $('#site_id').val()!=undefined && ($('#site_id').val() == 'innovationhealth' ||  $('#site_id').val() == 'DirectLinkIH')){
	$('#loginSection').click(function(){
		window.location = 'https://'+getIhDseDomainName()+'/MbrLanding/RoutingServlet?createSession=true';
	});
	$('#loginSection1').click(function(){
		window.location = 'https://'+getIhDseDomainName()+'/MbrLanding/RoutingServlet?createSession=true';
	});
}else{
$('#loginSection').click(function(){
	window.location = $('#loginBoxUrl').text();
});
$('#loginSection1').click(function(){
	window.location = $('#loginBoxUrl').text();
});
}


if(urlProtocol == urlProtocolSecure){
	$('#header').css('border-bottom','none');
	$('#header').css('margin-bottom','0px;');
}else{
	$('#header').css('border-bottom','1px solid #cccccc');
	$('#header').css('margin-bottom','10px;');
}

//Findings
configuringBindEvents();

});



// listen for page changes
function restoreState(page) {
     
	// Restoring landing page when first page of application is loaded.
	if(landingPageState ==  true  && landingPage == window.location){
		location.href = window.location;
	}
	// Setting landing page when first page of application is loaded.
	if(landingPageState == 'false'){
		landingPage = window.location;
		landingPageState =  true;
	}
	
	// If no state, just create the first page
	
	if (page == null) {
		/* Start fix for session context time our error page */
		pageNullInd = true;
		/* End fix for session context time our error page */
		documentReady();
		return;
	}else if(urlProtocol == urlProtocolNonSecure){
		documentReady();
	}
	
	// restore all state variables
	var reason = page.markPage;
	whyPressed = page.whyPressed;
	
	$('#searchQuery').val(page.searchQuery);
	/* $('body').append('<div id=zipCodeEntryFieldStore style=display:none;>' + page.zip + '</div>');
	$('#zipCodeEntryField').val(page.zip); */
	$('#distance').val(page.radius);
	$('#withinMilesVal').val(page.withinMilesVal);
	$('#zipCode').val(page.zip);
	$('#quickSearchTypeMainTypeAhead').val(page.searchTypeMainTypeAhead);
	$('#quickSearchTypeThrCol').val(page.searchTypeThrCol);
	$('#mainTypeAheadSelectionVal').val(page.mainTypeAheadSelectionVal);
	$('#thrdColSelectedVal').val(page.thrdColSelectedVal);
	/* Start changes for story 9523/9533/9517/9532/9261 */
	$('#aetnaId').val(page.aetnaId);
	$('#Quicklastname').val(page.Quicklastname);
	$('#Quickfirstname').val(page.Quickfirstname);
	$('#QuickZipcode').val(page.QuickZipcode);
	$('#QuickCoordinates').val(page.QuickCoordinates);
	/* End changes for story 9523/9533/9517/9532/9261 */
	/*-- START CHANGES P20751b ACO Branding - n596307 --*/
	$('#quickCategoryCode').val(page.quickCategoryCode);
	$('#QuickGeoType').val(page.QuickGeoType);
	/*-- END CHANGES P20751b ACO Branding - n596307 --*/
	$('#quickSearchTerm').val(page.quickSearchTerm);
	$('#classificationLimit').val(page.classificationLimit);
	$('#pcpSearchIndicator').val(page.pcpSearchIndicator);
	$('#specSearchIndicator').val(page.specSearchIndicator);
	$('#suppressFASTDocCall').val(page.suppressFASTDocCall);
	$('#listPlanSelected').text(page.displayPlan);
	$('#modal_aetna_plans :selected').text(page.displayPlan);
	/*-- START CHANGES P8551c QHP_IVL PCR - n596307 --*/
	if($('#switchForShowPlansFamilyWise')!=null && $.trim($('#switchForShowPlansFamilyWise').text()) == 'ON')
	{
		$('#modal_aetna_plans :selected').val(page.displayPlanFullName);
		$('#listPlanSelected').val(page.displayPlan);
	}
	/*-- END CHANGES P8551c QHP_IVL PCR - n596307 --*/
	$('#lastPageTravVal').val(page.lastPageTravVal);
      /*Story 10253 Start*/
	$('#linkwithoutplan').val(page.linkwithoutplan);
      /*Story 10253 End*/
	if(urlProtocol == urlProtocolSecure){
		$('#memberZipCode').val(page.memberZipCode);
	}	
	$('#geoSearch').val(page.geoSearch);
	$('#geoBoxSearch').val(page.geoBoxSearch);
	$('#stateCode').val(page.stateCode);
	$('#geoMainTypeAheadLastQuickSelectedVal').val(page.geoMainTypeAheadLastQuickSelectedVal);
	$('#sendZipLimitInd').val(page.sendZipLimitInd);
	$('#site_id').val(page.site_id);
                  $('#sortOrder').val(page.sortOrder);
	/*-----START CHANGES A9991-1034 A615A-1094 Nov 2013-----*/
	$('#ioeqSelectionInd').val(page.ioeqSelectionInd);
	$('#ioe_qType').val(page.ioe_qType);
	if(page.publicPlan != undefined && page.publicPlan != null  && page.publicPlan != ''){
		$("#modalSelectedPlan").val(page.publicPlan);
		$('#columnPlanSelected').css('display','block');
		searchWithPlan(page.displayPlan,page.publicPlan)
	}
	/*-- START CHANGES P20941a August2014 - Medicare Advantage - n596307 --*/
	else if($('#switchForStatePlanSelectionPopUp')!=null && $.trim($('#switchForStatePlanSelectionPopUp').text()) == 'ON' 
			&& page.publicPlan != undefined && page.publicPlan != null  && (page.publicPlan == 'Select' || page.publicPlan == '')){
		$("#modalSelectedPlan").val();
		$('#columnPlanSelected').css('display','block');
		searchWithOutStatePlan(noneText);
	}
	/*-- END CHANGES P20941a August2014 - Medicare Advantage - n596307 --*/
	else{
		$("#modalSelectedPlan").val('');
		$('#columnPlanSelected').css('display','none');
	}
	
	if(urlProtocol == urlProtocolSecure){
		documentReady();
		$('.cmidx_select').val(page.selectedMemberDiv);
		$('.cmidx_select span').text(page.selectedMember);
		$('#selectedMemberForZip').val(page.member);
		$('#currentSelectedPlan').val(page.selectedPlan);
	}else{
		showDirectionsModal();
		showFilterDialogBox();
	}
	// do the last thing the user did
	if (reason == null) {
		
	} else if (reason == 'clickedPagination') {
		if (page.filterValues != undefined && page.filterValues != null){
			$("#filterValues").val(page.filterValues);
		}
		clickedPagination(page.pagination);
	} else if (reason == 'clickedFilter') {
		/*-----START CHANGES P19791a Exchange August 2013-----*/
		if($('#site_id').val() == 'QualifiedHealthPlanDoctors'){
			filteredCode = page.filteredCode;
			filteredDisplay = page.filteredDisplay;
		}
		/*-----END CHANGES P19791a Exchange August 2013-----*/
		clickedFilter(page.filterValues);
	} else if (reason == 'freeText') {
		searchSubmit('true');
		$("#docfindSearchEngineForm").submit();
	} else if (reason == 'publicPlanSelected'){
		$("#modalSelectedPlan").val(page.publicPlan);
		$('#columnPlanSelected').css('display','block');
		searchWithPlan(page.displayPlan,page.publicPlan)
		searchSubmit('true');
		$("#docfindSearchEngineForm").submit();
	}else if (reason == 'clickedDistance'){
		searchSubmit('true');
		$("#docfindSearchEngineForm").submit();
	}
	
	/*-- START CHANGES P20941a August2014 - Medicare Advantage - n596307 --*/
	$('#switchForStatePlanSelectionPopUp').val(page.switchForStatePlanSelectionPopUp);
	/*-- END CHANGES P20941a August2014 - Medicare Advantage - n596307 --*/
	
	/*--- START CHANGES P23695 Medicare Spanish Translation - n204189 ---*/
	$('#actualDisplayTerm').val(page.actualDisplayTerm);
	
	/*--- END CHANGES P23695 Medicare Spanish Translation - n204189 ---*/
}

// listen for page saves
function saveState(page) {
	var reason =  page.markPage;
	if (whyPressed != null){
		page.whyPressed = whyPressed;
	} 
	page.searchQuery = $('#searchQuery').val();
	if (page.searchQuery == undefined) {
		delete page.searchQuery;
	}

	page.searchTypeMainTypeAhead = $('#quickSearchTypeMainTypeAhead').val();
	if(page.searchTypeMainTypeAhead == undefined){
		delete page.searchTypeMainTypeAhead;
	}
	
	page.searchTypeThrCol = $('#quickSearchTypeThrCol').val();
	if(page.searchTypeThrCol == undefined){
		delete page.searchTypeThrCol;
	}
	
	page.mainTypeAheadSelectionVal = $('#mainTypeAheadSelectionVal').val();
	if(page.mainTypeAheadSelectionVal == undefined){
		delete page.mainTypeAheadSelectionVal;
	}
	
	page.thrdColSelectedVal = $('#thrdColSelectedVal').val();
	if(page.thrdColSelectedVal == undefined){
		delete page.thrdColSelectedVal;
	}
	
	/* Start changes for story 9523/9533/9517/9532/9261 */	
	page.aetnaId = $('#aetnaId').val();
	if(page.aetnaId == undefined){
		delete page.aetnaId;
	}

	page.Quicklastname = $('#Quicklastname').val();
	if(page.Quicklastname == undefined){
		delete page.Quicklastname;
	}
	
	page.Quickfirstname = $('#Quickfirstname').val();
	if(page.Quickfirstname == undefined){
		delete page.Quickfirstname;
	}
	
	page.QuickZipcode = $('#QuickZipcode').val();
	if(page.QuickZipcode == undefined){
		delete page.QuickZipcode;
	}
	
	page.QuickCoordinates = $('#QuickCoordinates').val();
	if(page.QuickCoordinates == undefined){
		delete page.QuickCoordinates;
	}
	
	/*-- START CHANGES P20751b ACO Branding - n596307 --*/
	page.quickCategoryCode = $('#quickCategoryCode').val();
	if(page.quickCategoryCode == undefined){
		delete page.quickCategoryCode;
	}
	
	page.QuickGeoType = $('#QuickGeoType').val();
	if(page.QuickGeoType == undefined){
		delete page.QuickGeoType;
	}
	/*-- END CHANGES P20751b ACO Branding - n596307 --*/
	
	/* End changes for story 9523/9533/9517/9532/9261 */
	
	page.geoSearch = $('#geoSearch').val();
	if(page.geoSearch == undefined){
		delete page.geoSearch;
	}
	
	page.geoMainTypeAheadLastQuickSelectedVal = $('#geoMainTypeAheadLastQuickSelectedVal').val();
	if(page.geoMainTypeAheadLastQuickSelectedVal == undefined){
		delete page.geoMainTypeAheadLastQuickSelectedVal;
	}
	
	page.geoBoxSearch = $('#geoBoxSearch').val();
	if(page.geoBoxSearch == undefined){
		delete page.geoBoxSearch;
	}
	
	page.stateCode = $('#stateCode').val();
	if(page.stateCode == undefined){
		delete page.stateCode;
	}
	if(urlProtocol == urlProtocolSecure){		
		page.memberZipCode = $('#memberZipCode').val();
		if(page.memberZipCode == undefined){
			delete page.memberZipCode;
		}
	}
	
	page.quickSearchTerm = $('#quickSearchTerm').val();
        if(page.quickSearchTerm == undefined){
                delete page.quickSearchTerm;
        }

	page.classificationLimit = $('#classificationLimit').val();
	  if(page.classificationLimit == undefined){
			delete page.classificationLimit;
	  }

	page.pcpSearchIndicator = $('#pcpSearchIndicator').val();
	  if(page.pcpSearchIndicator == undefined){
			delete page.pcpSearchIndicator;
	  }

	page.specSearchIndicator = $('#specSearchIndicator').val();
	  if(page.specSearchIndicator == undefined){
			delete page.specSearchIndicator;
	  }
	
	page.suppressFASTDocCall = $('#suppressFASTDocCall').val();
	  if(page.suppressFASTDocCall == undefined){
			delete page.suppressFASTDocCall;
	  }
	
	//alert(whyPressed);
     /*Story 10253 Start*/
	page.linkwithoutplan = $('#linkwithoutplan').val();
	if (page.linkwithoutplan == undefined) delete page.linkwithoutplan;
	/*Story 10253 End*/

	page.publicPlan = $("#modalSelectedPlan").val();
	if (page.publicPlan == undefined) delete page.publicPlan;
	
	/*-- START CHANGES P8551c QHP_IVL PCR - n596307 --*/
	if($('#switchForShowPlansFamilyWise')!=null && $.trim($('#switchForShowPlansFamilyWise').text()) == 'ON')
	{

		var fullPlan = $('#modal_aetna_plans :selected').val();
		var indexPlanHeader = fullPlan.indexOf("_PLANHEADER_");
		if( indexPlanHeader > 372 && browserName != null && browserName == 'IE')
		{
			var totalLength = $('#modal_aetna_plans :selected').val().length;
			fullPlan = ($('#modal_aetna_plans :selected').val()).substring(0, 7) +
					($('#modal_aetna_plans :selected').val()).substring(indexPlanHeader, totalLength ); 
			page.displayPlanFullName = fullPlan;
		}
		else
		{
			page.displayPlanFullName = $('#modal_aetna_plans :selected').val();
		}
		page.displayPlan = addPlanFamilyToSelectedPlan();
	}
	else{
	page.displayPlan = $('#modal_aetna_plans :selected').text();
	}
	/*-- END CHANGES P8551c QHP_IVL PCR - n596307 --*/
	if (page.displayPlan == undefined) delete page.displayPlan;
	
	/* page.zip = $("#zipCodeEntryField").val();
	if (page.zip == undefined) delete page.zip; */
	
	page.zip = $("#zipCode").val();
	if (page.zip == undefined) delete page.zip;
	
	page.filterValues = $("#filterValues").val();
	if (page.filterValues == undefined) delete page.filterValues;
	
	/*-----START CHANGES P19791a Exchange August 2013-----*/
	if($('#site_id').val() == 'QualifiedHealthPlanDoctors'){
		page.filteredCode = filteredCode;
		if (page.filteredCode == undefined || page.filteredCode == null  ) 
			delete page.filteredCode;
		
		page.filteredDisplay = filteredDisplay;
		if (page.filteredDisplay == undefined || page.filteredDisplay == null  ) 
			delete page.filteredDisplay;
	}
	/*-----END CHANGES P19791a Exchange August 2013-----*/

	page.pagination = $("#pagination").val();
	if (page.pagination == undefined) delete page.pagination;
	
	page.radius = $('#distance').val();
	if (page.radius == undefined || page.radius == null  ) delete page.radius;
	
	if(urlProtocol == urlProtocolSecure){
		page.member = $('#selectedMemberForZip').val();
		if (page.member == undefined) delete page.member;
		
		page.selectedPlan = $('#currentSelectedPlan').val();
		if (page.selectedPlan == undefined) delete page.selectedPlan;

		page.selectedMember = $('.cmidx_select span').text();
		if (page.selectedMember == undefined) delete page.selectedMember;

		page.selectedMemberDiv = $('.cmidx_select').val();
		if (page.selectedMemberDiv== undefined) delete page.selectedMemberDiv;
	}
	
	page.lastPageTravVal = $('#lastPageTravVal').val();
	if(page.lastPageTravVal == undefined){
		delete page.lastPageTravVal;
	}
	
	page.sendZipLimitInd = $('#sendZipLimitInd').val();
	if(page.sendZipLimitInd == undefined){
		delete page.sendZipLimitInd;
	}
	
	page.site_id = $('#site_id').val();
	if(page.site_id == undefined){
		delete page.site_id;
	}
                  page.sortOrder = $('#sortOrder').val();
	if (page.sortOrder == undefined || page.sortOrder == null  ) delete page.sortOrder;
	/*-----START CHANGES A9991-1034 A615A-1094 Nov 2013-----*/
	page.ioeqSelectionInd = $('#ioeqSelectionInd').val();
	if(page.ioeqSelectionInd == undefined){
		delete page.ioeqSelectionInd;
	}
	page.ioe_qType = $('#ioe_qType').val();
	if(page.ioe_qType == undefined){
		delete page.ioe_qType;
	}
	
	/*-- START CHANGES P20941a August2014 - Medicare Advantage - n596307 --*/
	page.switchForStatePlanSelectionPopUp = $('#switchForStatePlanSelectionPopUp').val();
	if (page.switchForStatePlanSelectionPopUp == undefined) {
		delete page.switchForStatePlanSelectionPopUp;
	}
	/*-- END CHANGES P20941a August2014 - Medicare Advantage - n596307 --*/
	
	/*--- START CHANGES P23695 Medicare Spanish Translation - n204189 ---*/
	page.actualDisplayTerm = $('#actualDisplayTerm').val();
	if (page.actualDisplayTerm == undefined) {
		delete page.actualDisplayTerm;
	}
	
	/*--- END CHANGES P23695 Medicare Spanish Translation - n204189 ---*/
	page.withinMilesVal = $('#withinMilesVal').val();
	if(page.withinMilesVal == undefined){
		delete page.withinMilesVal;
	}
}


function documentReady(){
	populateUrlParameters();
	/*P8423a Sprint21 - Story8898 Changes Start*/
	if($("#searchSection").css('display') == 'block'){
		$("#leftStaticSectionFt").css('display','none');
		/*P8423a Sprint1 - Story9702 Changes Start*/
		$("#showGANlink").css('display','none');
		/*P8423a Sprint1 - Story9702 Changes End*/
	}
	else{
		$("#leftStaticSectionFt").css('display','block');
		/*P8423a Sprint1 - Story9702 Changes Start*/
		$("#showGANlink").css('display','block');
		/*P8423a Sprint1 - Story9702 Changes End*/
		var fromPage = $('#flowIndicator').text();
		var referrer =  document.referrer;
		var showbacktosearch = true;
		/* Start fix for session context time our error page */
		if(pageNullInd){
			var currentPage = window.location.href;
			var isSecureSessionTimeOutExceptionPage = (currentPage != null && currentPage.indexOf('/search?') != -1);
			if(isSecureSessionTimeOutExceptionPage){
				showbacktosearch = false;
			}
		}
		/* End fix for session context time our error page */
		if(referrer.indexOf('search/detail')> 0){
			showbacktosearch = false;
		}
		if(referrer.indexOf('search/redirect')> 0){
			showbacktosearch = false;
		}
		if($.getUrlVar('searchResultsInd')){
			showbacktosearch = false;
		}
		if(ieVersion <= 8 ){
			if($.getUrlVar('showBackButton')){
				showbacktosearch = false;
			}
		}
		
		/*-- START CHANGES P23695 Medicare Spanish Translation - n596307 --*/
		/*var backToSearchResultsDivContent = $('#backToSearchResultsDiv').html();
		if(urlProtocol == urlProtocolSecure){
			$(".left_section_public_ft").css('background-color','#E9ECBF');
			if(showbacktosearch == true){
				$("#sideNav_secure_ft ul").prepend('<li><a style="cursor: pointer; cursor: hand" href="javaScript:prevAnnCookie();javaScript:window.history.go(-1);">' + backToSearchResultsDivContent + '</a></li>');
			}
			$("#sideNav_secure_ft ul").css("border-top-width","0px");
		}
		else{
		if(showbacktosearch == true){
			$("#sideNav_home_ft ul").prepend('<li><a style="cursor: pointer; cursor: hand" href="javaScript:prevAnnCookie();javaScript:window.history.go(-1);">' + backToSearchResultsDivContent + '</a></li>');
		}
			$("#sideNav_home_ft ul").css("border-top-width","0px");
		}*/
		/*-- END CHANGES P23695 Medicare Spanish Translation - n596307 --*/
	}
	/*P8423a Sprint21 - Story8898 Changes End*/
	
	setAnnLaunchParamSecure();
	/*P8423a Sprint18 - Story6904 Changes Start*/
	showSpinnerFromNav();
	/*P8423a Sprint18 - Story6904 Changes End*/
	hideLeftSection();
	convertFormsToDynamicForms('cmidx');
	
	// getGeolocation();
	searchSubmit('false');
	renderLeftSection();
	onLoadEvents();
	$('input:radio[name=geo1]').filter('[value=zip]').attr('checked', true);
	
	// add hooks into the type-ahead functionality from Healthline
	triggerSearchButtonEvent();
	scrollPositionForTakeActionBox();
	var parameter = $.getUrlVars();
	var byName = ($.getUrlVar('isHospitalFromDetails') || $.getUrlVar('officesLinkIsTrueDetails'));
	if(byName == 'true'){
		idetifyFlowsToEnableFormSubmit = false;
		callFromDetails();
	}

	var ipaFlowResults = $.getUrlVar('isIpaFromResults');
	if(ipaFlowResults == 'true'){
		idetifyFlowsToEnableFormSubmit = false;
		callFromResultsIPA();
	}
	
	ipaFlowResults = $.getUrlVar('isIpaFromDetails');
	if(ipaFlowResults == 'true'){
		idetifyFlowsToEnableFormSubmit = false;
		callFromDetailsIPA();
	}
      
      /* Start changes for Story 9791 */
	var isGroupFromDetails = $.getUrlVar('isGroupFromDetails');
	if(isGroupFromDetails == 'true'){
		idetifyFlowsToEnableFormSubmit = false;
		callFromGroupDetails();
	}
	
	var isGroupFromResults = $.getUrlVar('isGroupFromResults');
	if(isGroupFromResults == 'true'){
		idetifyFlowsToEnableFormSubmit = false;
		callFromGroupResults();
	}
	/* End changes for Story 9791 */
};

function cssForIE7(){
	var version = IEVersionCheck();
	if(version == 7){
		$('#findHealthCare_PubDF').css("width","122%");
		$('#findHealthCare').css("width","122%");
		$('table#preSearchHeaders').css("width","133%");	
	}
}

function hideDiv(divisionNameString){
	var divisionNamesArray = new Array();
	if(divisionNameString.indexOf(",") != -1){
		divisionNamesArray =  divisionNameString.split(",");
		
	}
	else{
		divisionNamesArray[0] = divisionNameString;
	}
	for(var i=0;i<divisionNamesArray.length;i++){
		var hideDivString = "";
		hideDivString = divisionNamesArray[i];
		$(hideDivString).hide();
	}
}

function showDiv(divisionNameString){
	var divisionNamesArray = new Array();
	if(divisionNameString.indexOf(",") != -1){
		divisionNamesArray =  divisionNameString.split(",");
	}
	else{
		divisionNamesArray[0] = divisionNameString;
	}
	for(var i=0;i<divisionNamesArray.length;i++){
		var showDivString = "";
		showDivString = divisionNamesArray[i];
		$(showDivString).show();
	}
}

function setAnnGuidedSearch(){
	if(searchQuery!=undefined && searchQuery !=null && searchQuery.length>0){
		if(searchQuery.indexOf('___')>=0 ){
			var location = searchQuery.substring(searchQuery.indexOf('___')+3);
			changeFormatGeoLocation();	
			$('#hl-autocomplete-search-location').val(location);

			if(searchQuery.indexOf('___') == 0)
				searchQuery = '*';
			else
				searchQuery = searchQuery.substring(0,searchQuery.indexOf('___'));
		}

		changeFormat();
		$('#hl-autocomplete-search').val(searchQuery);
		$('.hl-searchbar-button').click();
	}
}
function triggerSearchButtonEvent(){
	$(document).off('click','.hl-searchbar-button').on('click','.hl-searchbar-button', function(event) {},jQueryOnEventHandler);
}

function jQueryOnEventHandler(event){
	/*--- START CHANGES DEF0200873690 - Plan Stickiness Issue ---*/
	var askForPlanSelection = false;
	var valueAfterChange = trim($('#hl-autocomplete-search-location').val());
	var valueBeforeChange = $.getUrlVar('geoSearch');
	if(valueBeforeChange != null){
		if(valueBeforeChange.indexOf("%2C") > 0){
			valueBeforeChange = valueBeforeChange.replace(/%2C/g,",");
		}
		if(valueBeforeChange.indexOf("%20") > 0){
			valueBeforeChange = valueBeforeChange.replace(/%20/g," ");
		}
	}
	if(valueAfterChange != valueBeforeChange){
		askForPlanSelection = true;
	}
	/*--- END CHANGES DEF0200873690 - Plan Stickiness Issue ---*/
	/* P23695a Blue Link changes - Start - N204189 */
	if( ($('#actualSearchTerm').val() == 'undefined' || $('#actualSearchTerm').val() =="") 
			|| ( $('#hl-autocomplete-search').val() != $('#actualDisplayTerm').val() ) )
	{
		$('#searchQuery').val($('#hl-autocomplete-search').val());
		$('#actualDisplayTerm').val('');
		$('#actualSearchTerm').val('');
	}
	else
	{
		$('#searchQuery').val($('#actualSearchTerm').val());
	}
	/* P23695a Blue Link changes - End*/
	if($('#hl-autocomplete-search-location').val() != ghostTextWhereBox){
		if(urlProtocol == urlProtocolSecure){
			if((!($('#restUser').val() || $('#guestUser').val())) || ($('#restUser').val() || $('#guestUser').val()) && trim($('#hl-autocomplete-search-location').val()) != ''){
				$('#geoSearch').val(trim($('#hl-autocomplete-search-location').val()));
			}
			else if($('#restUser').val() || $('#guestUser').val() && trim($('#hl-autocomplete-search-location').val()) == ''){
				$('#geoSearch').val(trim($('#memberZipCode').val()));
			}
              /* P20488a changes start for error pop up */
                 if ($('#hl-autocomplete-search').val() == ghostTextWhatBox || $('#hl-autocomplete-search').val() ==""){
			var textFocus = '1';
			docFindShowOrHideHint(textFocus);
		    }
		}
		else{
		/* P20488 - 1231 changes start */
			var uiCategory = $('#quickSearchTypeMainTypeAhead').val();
			if (($('#hl-autocomplete-search-location').val()== null || $('#hl-autocomplete-search-location').val()== "" 
				|| $('#hl-autocomplete-search-location').val() == ghostTextWhereBox) && ((uiCategory == 'specialist' && $('#hl-autocomplete-search').val().indexOf('any location') == -1) || (uiCategory != 'specialist' && $('#hl-autocomplete-search').val().indexOf('any location') == -1)) ) {
				  
				  displayErrorLocationPopup();
				 
				 return;
			}else{
				$('#geoSearch').val(trim($('#hl-autocomplete-search-location').val()));
			}
		}
		/* P20488 - 1231 changes end */
	}
	if(urlProtocol == urlProtocolNonSecure){
		/*-- START CHANGES SR1399 DEC'14 - n596307 --*/
		var planPrefillFlowSwitch = getCookie('planPrefillFlowSwitch');
		/*-- END CHANGES SR1399 DEC'14 - n596307 --*/
		if(whyPressed != 'geo' && $('#showNoPlans').text() != 'true'){
			if((chk  || $('#searchQuery').val()) && (!($('#hl-autocomplete-search').val() == ghostTextWhatBox))){
			/* P20488 - 1231 changes start */
				var uiCategory = $('#quickSearchTypeMainTypeAhead').val();
				if (($('#hl-autocomplete-search-location').val()== null || $('#hl-autocomplete-search-location').val()== "" 
					|| $('#hl-autocomplete-search-location').val() == ghostTextWhereBox) && ((uiCategory == 'specialist' && $('#hl-autocomplete-search').val().indexOf('any location') == -1) || (uiCategory != 'specialist' && $('#hl-autocomplete-search').val().indexOf('any location') == -1)) ) {
					  
					  displayErrorLocationPopup();
					 
					 return;
				} 
				/* P20488 - 1231 changes end */
			/* Story 10253 Start*/
		            var x = document.getElementById("columnPlanSelected");
		            if ((x!=null && x.style.display != 'block') && $('#linkwithoutplan').val() != 'true') {
		            	/*-- START CHANGES P20941a August2014 - Medicare Advantage - n596307 --*/
		            	if($('#switchForStatePlanSelectionPopUp')!=null && $('#switchForStatePlanSelectionPopUp')!=undefined 
		            			&& $.trim($('#switchForStatePlanSelectionPopUp').text()) == 'ON'){
		            		showStatePlanListModal();
		            	}
		            	/*-- END CHANGES P20941a August2014 - Medicare Advantage - n596307 --*/
		            	//content 1008
		            	else if($('#site_id').val()!=null && $('#site_id').val()!=undefined && $('#site_id').val() == 'universityofrochester'){
		            		//don't show plan selection model box
		            		searchWithDefaultPlan();
		            	}
		            	//content directlink
		            	else if(directLinkSiteFound && planPrefillFlowSwitch != null && planPrefillFlowSwitch != 'true'){
		            		//don't show plan selection model box
		            		searchWithNoPlan();
		            	}
		            	/*-- START CHANGES P20751b ACO Branding - n596307 --*/
		            	/*--- START CHANGES DEF0200873690 - Plan Stickiness Issue ---*/
		            	else if($('#switchForForceHLSelection')!=null && $.trim($('#switchForForceHLSelection').text()) == 'ON'
		            			&& askForPlanSelection){
		            		searchWithHLSuggestions();
		            	}
		            	/*--- END CHANGES DEF0200873690 - Plan Stickiness Issue ---*/
		            	/*-- END CHANGES P20751b ACO Branding - n596307 --*/
		            	else{
		            		showPlanListModal();
		            	}

		            }
		            else{
		            	/*-- START CHANGES SR1399 DEC'14 - n596307 --*/
		            	if(!($('#switchForStatePlanSelectionPopUp')!=null && $('#switchForStatePlanSelectionPopUp')!=undefined 
		            			&& $.trim($('#switchForStatePlanSelectionPopUp').text()) == 'ON')  && whyPressed == 'publicPlan'
		            				&& planPrefillFlowSwitch != null && planPrefillFlowSwitch == 'true'){
		            		markPage('publicPlanSelected');
		            	}
		            	/*-- END CHANGES SR1399 DEC'14 - n596307 --*/
		            	/*-- START CHANGES P20751b ACO Branding - n596307 --*/
		            	/*--- START CHANGES DEF0200873690 - Plan Stickiness Issue ---*/
		            	else if($('#switchForForceHLSelection')!=null && $.trim($('#switchForForceHLSelection').text()) == 'ON'
		            		&& askForPlanSelection){
		            		searchWithHLSuggestions();
		            		return false;
		            	}
		            	/*--- END CHANGES DEF0200873690 - Plan Stickiness Issue ---*/
		            	/*-- END CHANGES P20751b ACO Branding - n596307 --*/
		            	searchSubmit('true');
		            	$("#docfindSearchEngineForm").submit();
		            	$('#showNoPlans').text('');                       
		            }
                / * Story 10253 End*/
               /* P20488a changes start for error pop up */
             }else if ($('#hl-autocomplete-search').val() == ghostTextWhatBox || $('#hl-autocomplete-search').val() ==""){
      			
     			var textFocus = '1';
     			docFindShowOrHideHint(textFocus);
     		}
		}else{
			/*-- START CHANGES SR1399 DEC'14 - n596307 --*/
			if(!($('#switchForStatePlanSelectionPopUp')!=null && $('#switchForStatePlanSelectionPopUp')!=undefined 
            		&& $.trim($('#switchForStatePlanSelectionPopUp').text()) == 'ON')  && whyPressed == 'publicPlan'
            		&& planPrefillFlowSwitch != null && planPrefillFlowSwitch == 'true'){
	    		 markPage('publicPlanSelected');
	    	 }
			/*-- END CHANGES SR1399 DEC'14 - n596307 --*/
			searchSubmit('true');
			$("#docfindSearchEngineForm").submit();
			$('#showNoPlans').text('');
		}
	}else{
/* P20488 - 1231 changes start */
		var uiCategory = $('#quickSearchTypeMainTypeAhead').val(); 
		if (($('#hl-autocomplete-search-location').val()== null || $('#hl-autocomplete-search-location').val()== "" 
				|| $('#hl-autocomplete-search-location').val() == ghostTextWhereBox) && (!($('#guestUser').val())) && ((uiCategory == 'specialist' && $('#hl-autocomplete-search').val().indexOf('any location') == -1) || (uiCategory != 'specialist' && $('#hl-autocomplete-search').val().indexOf('any location') == -1)) ) {
				  displayErrorLocationPopup();
				 return;
			} 
			/* P20488 - 1231 changes end */
		searchSubmit('true');
		$("#docfindSearchEngineForm").submit();
	}
	if(!($('#hl-autocomplete-search').val() == ghostTextWhatBox) && window.location.href.indexOf('#markPage') != -1 && !($('#hl-autocomplete-search').val() == '')){
		$(document).off('click','.hl-searchbar-button');
	}
}

/*function toggleFilterPleat(){
	$('#provTypeFilContent').show();
}*/

function onLoadEvents(){

	/* Fix For IE6 */
	if(ie6Check){
		if(window.location.href.indexOf('search/redirect') == -1 && !$('#detailsContentTable').is(':visible')){
			if(urlProtocol == urlProtocolNonSecure){
				$('div#content').addClass('fixForIE6');
			}else{
				$('div#content').addClass('fixForIE6Secure');
			}
		}else if($('#detailsContentTable').is(':visible')){
			$('div#content').addClass('fixForIE6Details');
		}
	}
	        
	adjustModalLayerDimentions();

	if($('#showModalStatus').val() == 'true'){
		$('#planSection').css("display","none");
		hideSpinnerForCAndFModel();
		showModal();
		$('.dialog-modal_planSelection').width($(document).width());
		$('.dialog-modal_planSelection').height($(document).height() + 140);
	}
	/* Start changes for P21861a May15 release - N204183 */
	else if(window.location.href.indexOf('site_id') < 0){
		/* P20941a August 2014 - Coventry Integration Medicare Advantage High Value  Networks - Rohit : START */
		if($('#hasOneTypeOfPlansOnly').val() == 'true' && 
				$('#site_id').val() != 'medicare' && window.location.href.indexOf('site_id=medicare') < 0){
				var mediCareIndOnePlan="";
				if($('#hasCurrentPlans').val() == 'true'){
					mediCareIndOnePlan = $('#medicareProdSessionIndCurr').val();
				}else if($('#hasFuturePlans').val() == 'true'){
					mediCareIndOnePlan = $('#medicareProdSessionIndFut').val();
				}
				if(mediCareIndOnePlan == 'true'){
					addMedicareSiteIdtoURL(null);
				}
		}
		/* P20941a August 2014 - Coventry Integration Medicare Advantage High Value  Networks - Rohit : END */	
	}
	var site_id = $.getUrlVar('site_id');
$('#loginSection').keydown(function(event){ 
	    var keyCode = (event.keyCode ? event.keyCode : event.which);   
	    if (keyCode == 13) {
	        $('#loginSection').trigger('click');
	    }
	});
	$('#startnewsearch').keydown(function(event){ 
	    var keyCode = (event.keyCode ? event.keyCode : event.which);   
	    if (keyCode == 13) {
	       // $('#startnewsearch').trigger('click');
		$("#startnewsearch").click();
	    }
	});
	/* End changes for P21861a May15 release - N204183 */
		
	/*-- START CHANGES P20941a August2014 - Medicare Advantage - n596307 --*/	
	$('#registerSection').click(function(){
		window.location = $('#regUrl').text();
	});
	/*-- END CHANGES P20941a August2014 - Medicare Advantage - n596307 --*/

	/* Start changes for P21861a May15 release - N204183 */
	if($('#site_id').val()!=null && $('#site_id').val()!=undefined && $('#site_id').val() == 'innovationhealth'){
		$('#logInTop').click(function(){
			window.location = 'https://'+getIhDseDomainName()+'/MbrLanding/RoutingServlet?createSession=true';
		});
	}else{
		$('#logInTop').click(function(){
		window.location = $('#loginBoxUrl').text();
	});
	}
	/* End changes for P21861a May15 release - N204183 */	
	$('#registerTop').click(function(){
		window.location = $('#regUrl').text();
	});

                  $('#logInTop2').click(function(){
		window.location = $('#loginBoxUrl').text();
	});
	
	$('#registerTop2').click(function(){
		window.location = $('#regUrl').text();
	});
	
	$('#showSearchTips').click(function(){
		$('#searchTips2').css("display","block");
		$('#searchTips1').css("display","none");
	});
	
	$('#hideSearchTips').click(function(){
		$('#searchTips1').css("display","block");
		$('#searchTips2').css("display","none");
	});
	
	/*P8423a Sprint17 - Story4558 Changes Start*/
	$('#openMoreLink').click(function(){
		$('#openMore').hide();
		$('#MoreContent').show(1000);
		$('#closeMore').show(1000);
		return false;
	});
	
	$('#closeMoreLink').click(function(){
		$('#closeMore').hide(1000);
		$('#MoreContent').hide(1000);
		$('#openMore').show();
		return false;
	});
	/*P8423a Sprint17 - Story4558 Changes End*/
	
	/*P8423a Sprint17 - Story5819 Changes Start*/
	$('#openMoreLinkProc').click(function(){
		$('#openMoreProc').hide();
		$('#MoreContentProc').show(1000);
		$('#closeMoreProc').show(1000);
		return false;
	});
	
	$('#closeMoreLinkProc').click(function(){
		$('#closeMoreProc').hide(1000);
		$('#MoreContentProc').hide(1000);
		$('#openMoreProc').show();
		return false;
	});
	/*P8423a Sprint17 - Story5819 Changes End*/
	
	/*P8423a Sprint17 - Story6524 Changes Start*/
	$('#openMoreProvType').click(function(){
		$('#openMorePT').hide();
		$('#MoreContentPT').show(1000);
		$('#closeMorePT').show(1000);
		return false;
	});
	
	$('#closeMoreProvType').click(function(){
		$('#closeMorePT').hide(1000);
		$('#MoreContentPT').hide(1000);
		$('#openMorePT').show();
		return false;
	});
	/*P8423a Sprint17 - Story6524 Changes End*/
	
	if(urlProtocol == urlProtocolSecure){
		
		if(document.getElementById('printAndEstimateTakeAction')!=null){
			$("#ResultsLeftSectionMenuSecure").css('display','block');
			$("#homeLeftSectionMenuSecure").css('display','none');
		}else{
			$("#ResultsLeftSectionMenuSecure").css('display','none');
			$("#homeLeftSectionMenuSecure").css('display','block');
		}
		
		$("#printAndEstimateTakeAction").css('top','335px');
		$(".mapImageSection").css('top','240px');
	}else{
		if(document.getElementById('printAndEstimateTakeAction')!=null){
			$("#ResultsLeftSectionMenu").css('display','block');
			$("#homeLeftSectionMenu").css('display','none');
		}else{
			$("#ResultsLeftSectionMenu").css('display','none');
			$("#homeLeftSectionMenu").css('display','block');
		}
	}
	
	$('#popUpPubDse').click(function(){
		/*P08-8423a Sprint20 - Story9536 Changes Start*/
		/* P20941a August 2014 - Coventry Integration Medicare Advantage High Value  Networks - Rohit : START */
		var redirectPubDseUrl = "";
		if(window.location.href.indexOf('site_id=medicare')>0){
			redirectPubDseUrl = 'http://www.aetnamedicare.com/';
		}
		else{
			redirectPubDseUrl = 'http://'+getPublicDseDomainName()+'/dse/search?site_id=dse';
		}
		if(redirectPubDseUrl!=undefined && redirectPubDseUrl!=null && trim(redirectPubDseUrl)!=''){
			popUp(redirectPubDseUrl);
		}
		/* P20941a August 2014 - Coventry Integration Medicare Advantage High Value  Networks - Rohit : END */
		return false;
		/*P08-8423a Sprint20 - Story9536 Changes end*/
	});
	
	/*P08-8423a Sprint20 - Story7106 Changes Start*/
	if(urlProtocol == urlProtocolSecure){
		$('#util-bookmarks').hide();
	}
	/*P08-8423a Sprint20 - Story7106 Changes End*/
	
	/* P08-8423a Sprint23 - Story9249/9257/9258 Changes Start */
	$('.dialog-close-button_preSearchDialogBox').click(function(){
		$('#quickSearchTypeThrCol').val('');
		/*-----START CHANGES A9991-1034 A615A-1094 Nov 2013-----*/
		$('#ioeqSelectionInd').val('');
		$('#ioe_qType').val('');
		return false;
	});
	/* P08-8423a Sprint23 - Story9249/9257/9258 Changes End */
	
	/*-- START CHANGES P20751b ACO Branding - n596307 --*/
	$('.dialog-close-button_preSearchHLDialogBox').click(function(){
		$('#quickSearchTypeThrCol').val('');
		$('#ioeqSelectionInd').val('');
		$('#ioe_qType').val('');
		return false;
	});
	/*-- END CHANGES P20751b ACO Branding - n596307 --*/
	
	/* P08-8423a Sprint24 - Story9458 Changes Start */
	thrdColumnProvTypeHideAllTable();
	if ($('#productCodeProvType').text() == "medical" || $('#productCodeProvType').text() == "medical;dental"){
		if($('#productCodeProvType').text() == "medical"){
			showDiv("#medicalThdColProvTypeContent,#hospitalThdColProvTypeContent,#otherProvTypeContent");			
		}
		else if($('#productCodeProvType').text() == "medical;dental"){
			showDiv("#medDenThdColProvTypeContent,#hospitalThdColProvTypeContent,#otherProvTypeContent");
		}		
	}
	else if($('#productCodeProvType').text() == "dental"){
		showDiv("#dentalThdColProvTypeContent");
		
	}	
	/*-----START CHANGES A9991-1034 A615A-1094 Nov 2013-----*/
	else if($('#productCodeProvType').text() == "vision" || $('#productCodeProvType').text() == "hearing"){
			showDiv("#medicalThdColProvTypeContent,#hospitalThdColProvTypeContent,#otherProvTypeContentWithoutNetworkPrograms");
	}
	/*-----END CHANGES A9991-1034 A615A-1094 Nov 2013-----*/
	if($('#productCodeProvType').text() == "dental"){
		displayBhEapDental();
	}
	else{
		displayBhEapMedicalAndMedDenAndStdAlone();
	}
	
	cssForIE7();
	/* P08-8423a Sprint24 - Story9458 Changes End */
	
	showFilterDialogBox();
	
	if($('#narrowNetworkModal').length >0){
		$('#narrowNetworkModal').doDialogDefault({width: 700, modal:true, draggable:true, closeOnEscape:true},[]);
	}
	
	// $('#quickSearchTypeThrCol').val('');
	
	if($('#napWarningDialog').length >0){
		$('#napWarningDialog').doDialogDefault({width:350, modal:true, draggable:true, closeOnEscape:true},
				 [{id:"nap_OK", value:"OK",url:"", arrow:false}]);
		
		$('#nap_OK').bind('click',function(){
			$('#napWarningDialog').trigger('hide');
			$('#columnPlanSelected').css('display','block');
			whyPressed = 'publicPlan';
			markPage('publicPlanSelected');
			searchSubmit('true');
			$("#docfindSearchEngineForm").submit();
			if((chk  || $('#searchQuery').val()) && (!($('#hl-autocomplete-search').val() == ghostTextWhatBox))){
				$(document).off('click','.hl-searchbar-button');
			}
			return false;
		});
		
		$('#napWarningDialog.dialog-content').parents('div.dialog-main-wrapper').children('div.dialog-close-button').click(function(){
			triggerSearchButtonEvent();
		});
	}
	/* P8423a - Sprint0 - Story9466  Changes Start */
	showDirectionsModal();
	/* P8423a - Sprint0 - Story9466  Changes End */

	/* P8423a - Sprint0 - Story9106  Changes Start */
	$('.act_url_secure').click(function(){
		window.location.href="/dse/search/hct";		
	});
	/* P8423a - Sprint0 - Story9106  Changes Start */
	/* P8423a - Sprint1 - Story9702  Changes Start */
	$("#GAELink").click(function(){
		var domainurl = getCnNameUrl();
		var x = domainurl.indexOf("www1.aetna.com");
		if($('#site_id').val() == 'innovationhealth'){
			window.location = 'https://' + getIhDseDomainName() + '/memberSecure/featureRouter/costcare/costcareLanding';
		}else{
			var domain = domainurl.substring(0,x);
			window.location = 'https://' + domain + 'member.aetna.com/memberSecure/featureRouter/costcare/costcareLanding';
		}
	});
	/* P8423a - Sprint1 - Story9702  Changes End */

	$('#openOtherMoreProvType').click(function(){
		$('#secOtherSection').show(1000);
		$('#openSecOtherSection').hide();
		return false;
	});
	
	$('#closeOtherMoreProvType').click(function(){
		$('#secOtherSection').hide(1000);
		$('#openSecOtherSection').show();
		return false;
	});

	/*-----START CHANGES A9991-1034 A615A-1094 Nov 2013-----*/
	$('#openOtherMoreProvTypeWithoutNP').click(function(){
		$('#secOtherSectionWithoutNP').show(1000);
		$('#openSecOtherSectionWithoutNP').hide();
		return false;
	});
	
	$('#closeOtherMoreProvTypeWithoutNP').click(function(){
		$('#secOtherSectionWithoutNP').hide(1000);
		$('#openSecOtherSectionWithoutNP').show();
		return false;
	});	
	/*-----END CHANGES A9991-1034 A615A-1094 Nov 2013-----*/

	/*P08-8423a DEF0200665066 Changes Start*/
	$('#costOfCareLink').click(function(){
          window.location.href= $('#memberSecureDomainName').val()+$('#costCareUrl').val();       
        });
/*P08-8423a DEF0200665066 Changes end*/

	if(urlProtocol == urlProtocolSecure){
		/* P08-8423a Sprint2 - Story9769 Changes Start */
		if($('#lhrPharmacyProvType').text() == 'true'){
			$('#pharmacyProvTypeSecure').show();
			$('#pharmacyProvTypePublic').show();
		}else{
			$('#pharmacyProvTypeSecure').hide();
			$('#pharmacyProvTypePublic').hide();
		}
		/* P08-8423a Sprint2 - Story9769 Changes End */
		
		/* P08-8423a Sprint2 - Story9768 Changes Start */
		if($('#lhrVisionProvType').text() == 'true'){
			$('#visionProvTypeSecure').show();
			$('#visionProvTypePublic').show();
		}else{
			$('#visionProvTypeSecure').hide();
			$('#visionProvTypePublic').hide();
		}
		/* P08-8423a Sprint2 - Story9768 Changes End */
		
		/* P08-8423a Sprint2 - Story9770 Changes Start */
		if($('#lhrHearingProvType').text() == 'true'){
			$('#hearingProvTypeSecure').show();
			$('#hearingProvTypePublic').show();
		}else{
			$('#hearingProvTypeSecure').hide();
			$('#hearingProvTypePublic').hide();
		}
		/* P08-8423a Sprint2 - Story9770 Changes End */
	}

	$('#suppressFASTCall').val('');
	$('#suppressHLCall').val('');

	/* P08-8423a Sprint3 - Story9837 Changes Start */
	/*-- START CHANGES P23695 Medicare Spanish Translation - n709197 --%>*/
	var cancelButtonLocationModal = $('#cancelButtonLocationModalDiv').html();
	var searchButtonLocationModal = $('#searchButtonLocationModalDiv').html();
	if($('#locationDialogBox').length >0 && !($('#locationDialogBox').attr('class') == 'dialog-content')){
		$('#locationDialogBox').doDialogDefault({width:300, modal:true, draggable:true, closeOnEscape:true},
				 [{id:"cancelWHLocCriteria", value:cancelButtonLocationModal, url:"", arrow:false},
				  {id:"searchWHLocCriteria", value:searchButtonLocationModal,url:"", arrow:false}
		]);
	}
	/*-- END CHANGES P23695 Medicare Spanish Translation - n709197 */
	/* P08-8423a Sprint3 - Story9837 Changes End */
	
	/*-- START CHANGES P20751b ACO Branding - n596307 --*/
	if($('#locationHLDialogBox').length >0 && !($('#locationHLDialogBox').attr('class') == 'dialog-content')){
		$('#locationHLDialogBox').doDialogDefault({width:300, modal:true, draggable:true, closeOnEscape:true},
				 [{id:"cancelWHLocHLCriteria", value:"Cancel", url:"", arrow:false},
				  {id:"searchWHLocHLCriteria", value:"Continue",url:"", arrow:false}
		]);
	}
	/*-- END CHANGES P20751b ACO Branding - n596307 --*/
	
  /* Start Changes P20448a(A9991-1225) - Mar 14 release */	
	if($('#printDirectoryDialogBox').length >0 && !($('#printDirectoryDialogBox').attr('class') == 'dialog-content')){		
		$('#printDirectoryDialogBox').doDialogDefault({modal:true, draggable:true, closeOnEscape:true},
				 [{id:"cancelPDButton", value:"Cancel", url:"", arrow:false},
				  {id:"printPDButton", value:"&nbsp;&nbsp;Print&nbsp;Directory&nbsp;&nbsp;",url:"", arrow:false}
		]);
	}
	/* End Changes P20448a(A9991-1225) - Mar 14 release */

	/* P08-8423a Sprint3 - Story9839 Changes Start */
	createElementsForHLDisplayNames();
	/* P08-8423a Sprint3 - Story9839 Changes End */

	if($('#allFlagsDialogbox').length >0){
	    $('#allFlagsDialogbox').attr('title', 'More Information <br/><br/>');
	    $('#allFlagsDialogbox').attr('subtitle', '');
	    
		$('#allFlagsDialogbox').doDialogDefault({width: 400, modal:true, draggable:true, closeOnEscape:true},
		[{id:'btnCloseAllFlags',value:'CLOSE', "url":"javascript:closeModalBoxWithId('#allFlagsDialogbox')"}],'allFlagsDialogbox');
	}
	if(urlProtocol == urlProtocolNonSecure){
		$('#lastPageTravVal').val('');
	}
	/*-----START CHANGES P19791a Exchange August 2013-----*/
	if($('#site_id').val() == 'QualifiedHealthPlanDoctors' && window.location.href.indexOf('search/detail') < 0 && window.location.href.indexOf('markPage') < 0){
			$('#homeLeftSectionExchange').css('display','block');
	} 
	/*-----END CHANGES P19791a Exchange August 2013-----*/

	/*-----START CHANGES P8551c QHP_IVL PCR - n204189-----*/
	if($('#site_id').val() == 'ivl' && window.location.href.indexOf('search/detail') < 0 && window.location.href.indexOf('markPage') < 0){
			$('#homeLeftSectionExchange').css('display','block');
	} 
	/*-----END CHANGES P8551c QHP_IVL PCR - n204189-----*/
	/*-- START CHANGES P20941a August2014 - Medicare Advantage - n596307 --*/
	if(urlProtocol == urlProtocolNonSecure){
		statePlanPopUpDecider();
	}
	$('#logInStatePopup').click(function(){
		window.location = $('#loginBoxUrl').text();
	});
	/*-- END CHANGES P20941a August2014 - Medicare Advantage - n596307 --*/
	
	/* P20941a August 2014 - Coventry Integration Medicare Advantage High Value  Networks - Rohit : START */
	var site_id = $.getUrlVar('site_id');
	if(urlProtocol == urlProtocolSecure 
			&& (($('#site_id').val()!=null && $('#site_id').val()!=undefined && $('#site_id').val() == 'medicare') 
			|| (site_id!=null && site_id!=undefined && site_id== 'medicare'))){
		$("#homeLeftSectionMenuSecure").css('display','block');
		$("#sideNav_secure_ft").css('display','none');
		
	}
	/* P20941a August 2014 - Coventry Integration Medicare Advantage High Value  Networks - Rohit : END */
	/*-- START CHANGES SR1399 DEC'14 - n596307 --*/
	if(checkPlanPrefillFlow()){
		setCookie("planPrefillFlowSwitch", true, 5);
		if(!($('#planFamilySwitch')!=null && $('#planFamilySwitch')!=undefined && $.trim($('#planFamilySwitch').text()) == 'ON')){
			if($('#planDisplayName').html()!='' && $('#externalPlanCode').html()!=''){
				//content 0420
				var planDisplayName = $('#planDisplayName').html().replace(/&amp;/gi, "&");
				$('#modal_aetna_plans :selected').text(planDisplayName);
				$('#modal_aetna_plans :selected').val($('#externalPlanCode').html());
				continueButtonSelected();
			}
		}
	}
	/*-- END CHANGES SR1399 DEC'14 - n596307 --*/
	/*-- START CHANGES P20751b ACO Branding - n596307 --*/
	hidePrintAProvDirectoryOption();
	/*-- END CHANGES P20751b ACO Branding - n596307 --*/
	/* START CHANGES P20009 UI UPDATES - n709197 */
	var detailsUrl = window.location.href;
	var isDetailsPage = (detailsUrl != null && detailsUrl.indexOf('search/detail') != -1); 
	if(isDetailsPage){
		var selectedPlanDisplayName = getDisplayNameForSelectedPlan(replaceSpecialCharCodes($.getUrlVar('productPlanName')));
		if(urlProtocol == urlProtocolNonSecure){
			var selectedPlanText = $('#selectedPlanDiv').html();
			$("#selectedPlanDiv").html(selectedPlanText + "<b>" + selectedPlanDisplayName + "</b>");
		}
	}
	 /* END CHANGES P20009 UI UPDATES - n709197 */
	//508-Compliance
	setDSEDialogFocus('');
	if (isDetailsPage) { 
        	$('.act_url_secure').css('background-image','none');
	}else{
		$('.act_url_secure').css('background-image','url("/dse/assets/images/BTN_blue_center_fill.gif") ');
	}
}

/*-- START CHANGES P20941a August2014 - Medicare Advantage - n596307 --*/
function statePlanPopUpDecider(){
	var hideStatePlanPopUp = ($.getUrlVar('isHospitalFromDetails') || $.getUrlVar('officesLinkIsTrueDetails') 
			|| $.getUrlVar('isIpaFromResults') || $.getUrlVar('isIpaFromDetails')
			|| $.getUrlVar('isGroupFromDetails') || $.getUrlVar('isGroupFromResults'));
	var pageUrl = window.location.href;
	if(!hideStatePlanPopUp && $('#switchForStatePlanSelectionPopUp')!=null && $('#switchForStatePlanSelectionPopUp')!=undefined
			&& $.trim($('#switchForStatePlanSelectionPopUp').text()) == 'ON' 
				&& pageUrl != null && pageUrl.indexOf('markPage') == -1){
		showStatePlanListModal();
		if($('#noPlanAlertDialogBox').length >0){
			/*--- START CHANGES P23695 Medicare Spanish Translation - n596307 ---*/
			var iUnderstandText = $('#iUnderstandTextDiv').html();
			$('#noPlanAlertDialogBox').doDialogDefault({width:290, modal:true, draggable:true, closeOnEscape:true},
					[{id:"iUnderstand", value:iUnderstandText, url:"", arrow:false}]);
			/*--- END CHANGES P23695 Medicare Spanish Translation - n596307 ---*/

			$('#iUnderstand').bind('click',function(){
				var planSelected = $('#modal_aetna_plans :selected').text();
				if(planSelected == "" || planSelected == "Select"){
					planSelected = noneText;
					searchWithOutStatePlan(planSelected);
				}
				$('#noPlanAlertDialogBox').trigger('hide');
				//508 changes
				defaultFocusToSearchFor();
				if($('#hl-autocomplete-search-location').val()!= undefined && $('#hl-autocomplete-search-location').val() != ghostTextWhereBox 
					&& $('#hl-autocomplete-search-location').val()!='' && $('#hl-autocomplete-search').val()!= undefined 
					&& $('#hl-autocomplete-search').val() != ghostTextWhatBox && $('#hl-autocomplete-search').val()!='')
				{
					markPage('freeText');
					searchSubmit('true');
					$("#docfindSearchEngineForm").submit();
				}
				/*-- Start changes SR1347 Sep2014 - N204183 --*/
				var externalSearchType = document.getElementById("externalSearchType");
				var stateToBePrefilled=$('#stateToBePrefilled').html();
				if(externalSearchType != undefined && externalSearchType.innerHTML != null && externalSearchType.innerHTML != '' && (stateToBePrefilled==null || trim(stateToBePrefilled) == "")){
					 showLocationDialogBox(trim(externalSearchType.innerHTML));
				}
				/*-- End changes SR1347 Sep2014 - N204183 --*/
				return false;
			});

			$('#noPlanAlertDialogBox.dialog-content').parents('div.dialog-main-wrapper').children('div.dialog-close-button').click(function(){
				var planSelected = $('#modal_aetna_plans :selected').text();
				if(planSelected == "" || planSelected == "Select"){
					planSelected = noneText;
					searchWithOutStatePlan(planSelected);
				}
				return false;
			});
		}
	}
}
/*-- END CHANGES P20941a August2014 - Medicare Advantage - n596307 --*/

/************************************************************************************************************
										LEFT SECTION SCRIPTS START FROM HERE
************************************************************************************************************/
function hideLeftSection(){
	$('#showPlan').hide();
	$('#hidePlan').hide();
	$('#planSection').hide();
	$('#currentMedical').hide();
	$('#currentDental').hide();
	$('#futureMedical').hide();
	$('#futureDental').hide();
	$('#futurePlanLink').hide();
	$('#currentPlanLink').hide();
	$('#dentalSpacing').hide();
	$('#planTable').show();
	$('#searchTips2').hide();
	$('#searchTips1').show();
}

function renderLeftSection(){
	var positionDecided = 'false';
	var showFuturePlans = $('#showFuturePlans').val();
	if($('#hasFuturePlans').val() == 'true' && $('#hasCurrentPlans').val() == 'false' && showFuturePlans == 'true'){
		$('#currentPlanLink').hide();
		$('#futurePlanLink').hide();	
		if($('#showPlan').is(':visible')){
			$('#planTable').hide();
		}
		$('#futureMedical').show();
		if($('#futureMedical').length <2){
			$('#dentalSpacing').show();
		}
		$('#currentMedical').hide();
		$('#currentDental').hide();		
		$('#hidePlanLink').hide();	
		$('#showPlanLink').hide();
		$('#planSection').show();
		$('#futureDental').show();
		$('#subDispPlanType').val('FUTURE');
		positionDecided = 'true';
	}else if($('#hasFuturePlans').val() == 'false' && $('#hasCurrentPlans').val() == 'true'){
		$('#futurePlanLink').hide();
		$('#currentPlanLink').hide();
		if($('#showPlan').is(':visible')){
			$('#planTable').hide();
		}		
		$('#futureMedical').hide();
		$('#futureDental').hide();
		$('#showPlan').hide();
		$('#hidePlan').hide();
		$('#hidePlanLink').hide();
		$('#currentMedical').show();
		$('#currentDental').show();		
		$('#planSection').show();
		$('#planTable').show();
		$('#subDispPlanType').val('CURRENT');
		positionDecided = 'true';
	}else if($('#hasFuturePlans').val() == 'true' && $('#hasCurrentPlans').val() == 'true' 
		&& showFuturePlans == 'false'){
		$('#futurePlanLink').hide();
		$('#currentPlanLink').hide();
		if($('#showPlan').is(':visible')){
			$('#planTable').hide();
		}		
		$('#futureMedical').hide();
		$('#futureDental').hide();
		$('#showPlan').hide();
		$('#hidePlan').hide();
		$('#hidePlanLink').hide();
		$('#currentMedical').show();
		$('#currentDental').show();		
		$('#planSection').show();
		$('#planTable').show();
		positionDecided = 'true';
	}
	
	var planSelected = $('#planStatusSelected').val();
	if(planSelected !=null && planSelected!="" && positionDecided == 'false'){
		if(planSelected == 'CURRENT'){
			$('#showPlanLink').hide();
			$('#showPlan').hide();
			$('#hidePlanLink').hide();
			$('#hidePlan').hide();
			$('#planTable').show();
			$('#currentMedical').show();
			$('#currentDental').show();
			$('#futurePlanLink').show();
			$('#futureMedical').hide();
			$('#futureDental').hide();
			$('#currentPlanLink').hide();
			$('#subDispPlanType').val('CURRENT');
		}else if(planSelected == 'FUTURE' && showFuturePlans == 'true'){
			$('#showPlanLink').hide();
			$('#showPlan').hide();
			$('#hidePlanLink').hide();
			$('#hidePlan').hide();
			$('#futureMedical').show();
			$('#futureDental').show();
			$('#currentPlanLink').show();
			$('#currentMedical').hide();
			$('#currentDental').hide();
			$('#futurePlanLink').hide();
			$('#subDispPlanType').val('FUTURE');
		}
		$('#planSection').show();
	}else{
		if($('#hasFuturePlans').val() == 'true' && $('#hasCurrentPlans').val() == 'false' && showFuturePlans == 'true'){
			$('#subDispPlanType').val('FUTURE');
		}else if($('#hasFuturePlans').val() == 'false' && $('#hasCurrentPlans').val() == 'true'){
			$('#subDispPlanType').val('CURRENT');
		}else if($('#hasFuturePlans').val() == 'true' && $('#hasCurrentPlans').val() == 'true' && showFuturePlans == 'false'){
			$('#subDispPlanType').val('CURRENT');
		}
	}
	
	$('#showPlan').click(function(){
	/* SR 1468 changes Start N702925*/
		var planStatusSelectedDiv = $('#planStatusSelectedDiv').html();
		$('#planSection').show(1000);
		if(planStatusSelectedDiv !=null && planStatusSelectedDiv!=""){
			$('#planTable').show();
			if(planStatusSelectedDiv == 'CURRENT'){
				$('#showPlan').hide();						
				$('#futureMedical').hide();
				$('#futureDental').hide();
				$('#currentPlanLink').hide();
				$('#futurePlanLink').show();				
				$('#currentMedical').show();
				$('#currentDental').show();
				$('#hidePlan').show(1000);				
			}else if(planStatusSelectedDiv == 'FUTURE' && showFuturePlans == 'true'){
				$('#futurePlanLink').hide();				
				$('#currentMedical').hide();
				$('#currentDental').hide();
				$('#showPlan').hide();
				$('#futureMedical').show();
				$('#futureDental').show();
				$('#currentPlanLink').show();				
				$('#hidePlan').show(1000);										
			}
		}
		/* SR 1468 changes End N702925*/
			
		if($('#hasFuturePlans').val() == 'true' && $('#hasCurrentPlans').val() == 'false' 
			&& showFuturePlans == 'true'){
			$('#futurePlanLink').hide();
			$('#currentPlanLink').hide();
			$('#currentMedical').hide();
			$('#currentDental').hide();
			$('#showPlan').hide();
			$('#futureMedical').show();
			$('#futureDental').show();
			$('#planTable').show();
			$('#hidePlan').show(1000);			
		}else if($('#hasFuturePlans').val() == 'false' && $('#hasCurrentPlans').val() == 'true'){
			$('#futureMedical').hide();
			$('#futureDental').hide();
			$('#futurePlanLink').hide();
			$('#currentPlanLink').hide();
			$('#showPlan').hide();
			$('#currentMedical').show();
			$('#currentDental').show();
			$('#planTable').show();
			$('#hidePlan').show(1000);
		}else if($('#hasFuturePlans').val() == 'true' && $('#hasCurrentPlans').val() == 'true' 
			&& showFuturePlans == 'false'){
			$('#futureMedical').hide();
			$('#futureDental').hide();
			$('#futurePlanLink').hide();
			$('#currentPlanLink').hide();
			$('#showPlan').hide();
			$('#currentMedical').show();
			$('#currentDental').show();
			$('#planTable').show();
			$('#hidePlan').show(1000);
		}					

		$('#showPlanLink').hide();
		$('#hidePlanLink').show();
	});
	
	$('#hidePlan').click(function(){
		$('#planSection').hide(1000);
		$('#hidePlanLink').hide();
		$('#showPlanLink').show();
		$('#showPlan').show();
		$('#hidePlan').hide();
	});
	
	if($('#hasCurrentMedPlans').val() == 'true'){
		$('.planTitleDental').css("padding-top","18px");
	}else{
		$('.planTitleDental').css("padding-top","0px");
	}
	
	populateUrlParameters();
	var params = $.getUrlVars();
	var byName = $.getUrlVar('frmpage');
	
	if($('#hasCurrentPlans').val() == 'true' || $('#hasFuturePlans').val() == 'true'){
		if(byName == 'fromFtSummary' || byName == 'fromFtDetail'){
			$('#showPlanLink').html('<br/>');
			$('#hidePlanLink').html('<br/>');
			$('#showPlanLink').show();
			$('#showPlan').show();
			$('#planSection').hide();
			$('#currentMedical').hide();
			$('#currentDental').hide();
			$('#futureMedical').hide();
			$('#futureDental').hide();
			$('#fromFtSummary').remove();
		}
	}
	
	$('#cmidx_prim li').bind('mousedown', function(evt) {				
		currentValue = $("#cmidx").parent().attr("value");				
	});
	
	$('#cmidx_prim li').bind('mouseup', function(evt) {
		if(prevSelection != $('.cmidx_select').val()){
			prevSelection = $('.cmidx_select').val();
			$('#selMbrName').val($('#cmidx :selected').val());
			
			/* Below 'if' condition is added to specify different url in the ajax call for details page */
			if($('#detailsPageIndicator').length > 0){
				$.ajax({beforeSend:function(){showSpinner()},					 
					data: $(this).serialize(),
				    type: "GET",
				    url: "updateLeftPlanSection",
				    data: 'cmidx=' + $('.cmidx_select').val() +
				    	'&planStatusSelected=' + $('#planStatusSelected').val() + '&subDispPlanType=' + $('#subDispPlanType').val(),
				    success: function(response){
						$("#planSection").html(response);
						$('#zipCode').val($('#zipCodeFromReq').text());
						$('#thrdCol').show();
						thrdColumnProvTypeDisplayLeft();
						decidePlanPositionAfterClick('true');
						hideSpinner();
						if($('#searchQuery').val()){
							isRenderLeftSection = false;
							$('.hl-searchbar-button').click();
						}
				     }
				});
			}else if(window.location.href.indexOf('search/redirect') != -1){
				$.ajax({beforeSend:function(){showSpinner()},					 
					data: $(this).serialize(),
				    type: "GET",
				    url: "updateLeftPlanSection",
				    data: 'cmidx=' + $('.cmidx_select').val() +
				    	'&planStatusSelected=' + $('#planStatusSelected').val() + '&subDispPlanType=' + $('#subDispPlanType').val(),
				    success: function(response){
						$("#planSection").html(response);
						$('#zipCode').val($('#zipCodeFromReq').text());
						$('#thrdCol').show();
						thrdColumnProvTypeDisplayLeft();
						decidePlanPositionAfterClick('true');
						hideSpinner();
						if($('#searchQuery').val()){
							isRenderLeftSection = false;
							$('.hl-searchbar-button').click();
						}
				     }
				});
			}else{
				$.ajax({beforeSend:function(){showSpinner()},					 
					data: $(this).serialize(),
				    type: "GET",
				    url: "search/updateLeftPlanSection",
				    data: 'cmidx=' + $('.cmidx_select').val() +
				    	'&planStatusSelected=' + $('#planStatusSelected').val() + '&subDispPlanType=' + $('#subDispPlanType').val(),
				    success: function(response){
						$("#planSection").html(response);
						$('#zipCode').val($('#zipCodeFromReq').text());
						$('#thrdCol').show();
						thrdColumnProvTypeDisplayLeft();
						decidePlanPositionAfterClick('true');
						hideSpinner();
						if($('#searchQuery').val()){
							isRenderLeftSection = false;
							$('.hl-searchbar-button').click();
						}
				     }
				});
			}
		}
	});			
	/* P8423a - Story 4172 Changes End */
	$('#cmidx :selected').text($('#selMbrName').val());
	populateUrlParameters();
	var params = $.getUrlVars();
	var byName = $.getUrlVar('frmpage');
	if(byName == 'fromFtSummary'){
		renderLeftSectionForResultsPage();
	}
}


/* P08-8423a Sprint24 - Story9458 Changes Start */

function thrdColumnProvTypeHideAllTable(){
	
	hideDiv("#medicalThdColProvTypeContent" + "," 
			+ "#dentalThdColProvTypeContent" + ","  
			+ "#medDenThdColProvTypeContent" + "," 
			+ "#hospitalThdColProvTypeContent" + "," 
			+ "#bhThdColProvTypeContent" + "," 
			+ "#eapThdColProvTypeContent" + "," 
			+ "#bhEapThdColProvTypeContent" + ","
			+ "#otherProvTypeContent" + ","
			/*-----CHANGES A9991-1034 A615A-1094 Nov 2013-----*/
			+ "#otherProvTypeContentWithoutNetworkPrograms");  
}

function displayBhEapMedicalAndMedDenAndStdAlone(){
	if(($('#bhProvTypeContentValue').text() == "true" || $('#thrdLhrBhProvTypeContentValue').text() == "true")&& $('#eapProvTypeContentValue').text() == "true"){
		showDiv("#bhEapThdColProvTypeContent");
	}
	else if($('#bhProvTypeContentValue').text() == "true" || $('#thrdLhrBhProvTypeContentValue').text() == "true"){
		showDiv("#bhThdColProvTypeContent");
	}
	else if ($('#eapProvTypeContentValue').text() == "true"){
		showDiv("#eapThdColProvTypeContent");
	}
}

function displayBhEapDental(){
	if($('#bhProvTypeContentValue').text() == "true" && $('#eapProvTypeContentValue').text() == "true"){
		showDiv("#bhEapThdColProvTypeContent");
	}
	else if($('#bhProvTypeContentValue').text() == "true"){
		showDiv("#bhThdColProvTypeContent");
	}
	else if ($('#eapProvTypeContentValue').text() == "true"){
		showDiv("#eapThdColProvTypeContent");
	}
}

function thrdColumnProvTypeDisplayLeft(){	
	thrdColumnProvTypeHideAllTable();
	if ($('#productCodeProvTypeLeft').text() == "medical" || $('#productCodeProvTypeLeft').text() == "medical;dental"){
		if($('#productCodeProvTypeLeft').text() == "medical"){
			showDiv("#medicalThdColProvTypeContent,#hospitalThdColProvTypeContent,#otherProvTypeContent");
		}
		else if($('#productCodeProvTypeLeft').text() == "medical;dental"){
			showDiv("#medDenThdColProvTypeContent,#hospitalThdColProvTypeContent,#otherProvTypeContent");
		}
	}
	else if($('#productCodeProvTypeLeft').text() == "dental"){
		showDiv("#dentalThdColProvTypeContent");
	}
	/*-----START CHANGES A9991-1034 A615A-1094 Nov 2013-----*/
	else if($('#productCodeProvTypeLeft').text() == "vision" || $('#productCodeProvTypeLeft').text() == "hearing"){
			showDiv("#medicalThdColProvTypeContent,#hospitalThdColProvTypeContent,#otherProvTypeContentWithoutNetworkPrograms");
	}
	/*-----END CHANGES A9991-1034 A615A-1094 Nov 2013-----*/
	
	if($('#productCodeProvTypeLeft').text() == "dental"){
		displayBhEapDental();
	}
	else{
		displayBhEapMedicalAndMedDenAndStdAlone();
	}
}

function thrdColumnProvTypeDisplayLeftCurr(){
	thrdColumnProvTypeHideAllTable();
	if ($('#productCodeProvTypeLeftCurr').text() == "medical" || $('#productCodeProvTypeLeftCurr').text() == "medical;dental"){
		if($('#productCodeProvTypeLeftCurr').text() == "medical"){
			showDiv("#medicalThdColProvTypeContent,#hospitalThdColProvTypeContent,#otherProvTypeContent");
		}
		else if($('#productCodeProvTypeLeftCurr').text() == "medical;dental"){
			showDiv("#medDenThdColProvTypeContent,#hospitalThdColProvTypeContent,#otherProvTypeContent");
		}
	}
	else if($('#productCodeProvTypeLeftCurr').text() == "dental"){
		showDiv("#dentalThdColProvTypeContent");
	}
	/*-----START CHANGES A9991-1034 A615A-1094 Nov 2013-----*/
	else if($('#productCodeProvTypeLeftCurr').text() == "vision" || $('#productCodeProvTypeLeftCurr').text() == "hearing"){
			showDiv("#medicalThdColProvTypeContent,#hospitalThdColProvTypeContent,#otherProvTypeContentWithoutNetworkPrograms");
	}
	/*-----END CHANGES A9991-1034 A615A-1094 Nov 2013-----*/
	if($('#productCodeProvTypeLeftCurr').text() == "dental"){
		displayBhEapDental();
	}
	else{
		displayBhEapMedicalAndMedDenAndStdAlone();
	}
}

/* P08-8423a Sprint24 - Story9458 Changes End */


function decidePlanPositionAfterClick(isClicked){
	var positionDecided = 'false';
	var currentPlanSpecing = 'false';
	populateUrlParameters();
	var params = $.getUrlVars();
	var byName = $.getUrlVar('frmpage');
	var showPlanLinkSpaceAdded = "";
	var showFuturePlans = $('#showFuturePlans').val();
	
	$('#navigators').remove();
	
	if($('#hasFuturePlans').val() == 'true' && $('#hasCurrentPlans').val() == 'false'  
		&& showFuturePlans == 'true'){
		$('#currentPlanLink').hide();
		$('#futurePlanLink').hide();	
		
		$('#futureMedical').show();
		if($('#futureMedical').length <2){
			$('#dentalSpacing').show();
		}
		$('#futureDental').show();
		$('#currentMedical').hide();
		$('#currentDental').hide();
		$('#planSection').show();
		$('#hidePlanLink').hide();	
		$('#showPlanLink').hide();
		if($('#showPlan').is(':visible')){
			$('#hidePlanLink').show();
			$('#hidePlan').show();
			$('#showPlan').hide();
		}else if($('#hidePlan').is(':visible')){
			$('#hidePlanLink').show();
			$('#hidePlan').show();
		}else{
			$('#showPlan').hide();
			$('#hidePlan').hide();
			$('#hidePlanLink').hide();
		}
		positionDecided = 'true';
	}else if($('#hasFuturePlans').val() == 'false' && $('#hasCurrentPlans').val() == 'true'){		
		if($('#currentPg').val()== 'details'){
			if($('#showPlan').is(':visible') || $('#showPlanLink').length<2){
				$('#hidePlanLink').show();
				$('#hidePlan').show();
				$('#showPlan').hide();
				currentPlanSpecing = 'true';
			}else if($('#hidePlan').is(':visible')){
				$('#hidePlanLink').show();
				$('#hidePlan').show();
			}else{
				$('#showPlan').hide();
				$('#hidePlan').hide();
				$('#hidePlanLink').hide();
			}
		}else{
			if($('#openImage').is(':visible')){
				$('#hidePlanLink').show();
				$('#hidePlan').show();
				$('#showPlan').hide();
				$('#planTable').show();
				currentPlanSpecing = 'true';
			}else if($('#hidePlan').is(':visible')){
				$('#hidePlanLink').show();
				$('#hidePlan').show();
			}else{
				$('#showPlan').hide();
				$('#hidePlan').hide();
				$('#hidePlanLink').hide();
			}
		}
		
		$('#planSection').show();
		positionDecided = 'true';		
		
		if($('#showPlan').is(':visible') && ($('#showPlanLink').length>1 || $('#showPlanLink').is(':visible') 
				|| $('#currentMedical').is(':visible') || $('#currentDental').is(':visible'))){
			$('#planTable').hide();
		}else if(ieVersion >5 && currentPlanSpecing == 'false'){
			$('#showPlanLink').hide();
		}else{
			$('#showPlanLink').hide();			
		}		
		$('#futurePlanLink').hide();
		$('#currentPlanLink').hide();
		$('#currentMedical').show();
		$('#currentDental').show();
		$('#futureMedical').hide();
		$('#futureDental').hide();		
	}else if($('#hasFuturePlans').val() == 'true' && $('#hasCurrentPlans').val() == 'true' 
		&& showFuturePlans == 'false'){
		if($('#openImage').is(':visible')){
			$('#hidePlanLink').show();
			$('#hidePlan').show();
			$('#showPlan').hide();
			$('#planTable').show();
			currentPlanSpecing = 'true';
		}else if($('#hidePlan').is(':visible')){
			$('#hidePlanLink').show();
			$('#hidePlan').show();
		}else{
			$('#showPlan').hide();
			$('#hidePlan').hide();
			$('#hidePlanLink').hide();
		}
		
		$('#planSection').show();
		positionDecided = 'true';		
		
		if($('#showPlan').is(':visible') && ($('#showPlanLink').length>1 || $('#showPlanLink').is(':visible') 
				|| $('#currentMedical').is(':visible') || $('#currentDental').is(':visible'))){
			$('#planTable').hide();
		}else if(ieVersion >5 && currentPlanSpecing == 'false'){
			$('#showPlanLink').hide();
		}else{
			$('#showPlanLink').hide();			
		}
		
		$('#futureMedical').hide();
		$('#futureDental').hide();
		$('#futurePlanLink').hide();
		$('#currentPlanLink').hide();
		$('#currentMedical').show();
		$('#currentDental').show();
	}
	
	var planSelected = $('#planStatusSelected').val();
	if(planSelected !=null && planSelected!="" && positionDecided == 'false'){
		if($('#hasCurrentPlans').val() == 'true' || $('#hasFuturePlans').val() == 'true'){		
			if(planSelected == 'CURRENT'){
				$('#futureMedical').hide();
				$('#futureDental').hide();
				$('#currentPlanLink').hide();
				$('#currentMedical').show();
				$('#currentDental').show();
				$('#futurePlanLink').show();			
			}else if(planSelected == 'FUTURE'  && showFuturePlans == 'true'){
				$('#currentMedical').hide();
				$('#currentDental').hide();
				$('#futurePlanLink').hide();
				$('#futureMedical').show();
				$('#futureDental').show();
				$('#currentPlanLink').show();
				$('#showPlanLink').hide();
			}
			if($('#showPlan').is(':visible') || $('#showPlanLink').length<2){
				$('#planTable').hide();
				$('#dentalSpacing').hide();
			}
			
			if($('#planTable').is(':visible')){
				$('#showPlanLink').hide();
			}
			$('#planSection').show();
			if($('#openImage').is(':visible')){
				$('#showPlan').hide();			
				$('#planTable').hide();
				if(planSelected == 'CURRENT'){
					$('#showPlanLink').show();
				}else{
					$('#showPlanLink').hide();
				}
				$('#hidePlanLink').show();
				$('#hidePlan').show();
				showPlanLinkSpaceAdded = 'true';
			}else{
				$('#planTable').show();
			}
		}else{
			$('#showPlanLink').hide();
			$('#showPlan').hide();
			$('#hidePlanLink').hide();
			$('#hidePlan').hide();
		}
	}
	
	$('#showPlan').click(function(){
		$('#planSection').show(1000);
		if(planSelected !=null && planSelected!=""){
			$('#planTable').show();
			if(planSelected == 'CURRENT'){
				$('#futureMedical').hide();
				$('#futureDental').hide();
				$('#currentPlanLink').hide();
				$('#showPlan').hide();
				$('#futurePlanLink').show();				
				$('#currentMedical').show();
				$('#currentDental').show();
				$('#hidePlan').show(1000);
			}else if(planSelected == 'FUTURE'  && showFuturePlans == 'true'){
				$('#showPlan').hide();
				$('#futurePlanLink').hide();				
				$('#currentMedical').hide();
				$('#currentDental').hide();
				$('#futureMedical').show();
				$('#futureDental').show();
				$('#currentPlanLink').show();				
				$('#hidePlan').show(1000);										
			}
		}
			
		if($('#hasFuturePlans').val() == 'true' && $('#hasCurrentPlans').val() == 'false'
			 && showFuturePlans == 'true'){
			$('#showPlan').hide();
			$('#futurePlanLink').hide();
			$('#currentPlanLink').hide();
			$('#currentMedical').hide();
			$('#currentDental').hide();
			$('#futureMedical').show();
			$('#futureDental').show();			
			$('#planTable').show();
			$('#hidePlan').show(1000);			
		}else if($('#hasFuturePlans').val() == 'false' && $('#hasCurrentPlans').val() == 'true'){
			$('#currentMedical').show();
			$('#currentDental').show();
			$('#futureMedical').hide();
			$('#futureDental').hide();
			$('#futurePlanLink').hide();
			$('#currentPlanLink').hide();
			$('#planTable').show();
			$('#hidePlan').show(1000);
			$('#showPlan').hide();
		}else if($('#hasFuturePlans').val() == 'true' && $('#hasCurrentPlans').val() == 'true' 
			&& showFuturePlans == 'false'){
			$('#futureMedical').hide();
			$('#futureDental').hide();
			$('#futurePlanLink').hide();
			$('#currentPlanLink').hide();
			$('#showPlan').hide();
			$('#currentMedical').show();
			$('#currentDental').show();
			$('#planTable').show();
			$('#hidePlan').show(1000);
		}					

		$('#showPlanLink').hide();
		$('#hidePlanLink').show();
	});
	
	$('#hidePlan').click(function(){
		$('#planSection').hide(1000);
		$('#hidePlanLink').hide();
		$('#hidePlan').hide();
		$('#showPlan').show();
		$('#showPlanLink').show();		
	});
	
	if($('#hasCurrentMedPlans').val() == 'true'){
		$('.planTitleDental').css("padding-top","18px");
	}else{
		$('.planTitleDental').css("padding-top","0px");
	}
	
	if($('#hasCurrentPlans').val() == 'true' || $('#hasFuturePlans').val() == 'true'){
		if(isClicked!= 'true' && (byName == 'fromFtSummary' || byName == 'fromFtDetail')){
			$('#showPlanLink').html('<br/>');
			$('#hidePlanLink').html('<br/>');
			$('#showPlanLink').show();
			$('#showPlan').show();
			$('#planSection').hide();
			$('#fromFtSummary').remove();
		}else if(showPlanLinkSpaceAdded != 'true'){
			if(positionDecided == 'false'){
				$('#showPlanLink').hide();
			}
		}
	}else{
		$('#showPlanLink').hide();
		$('#showPlan').hide();
		$('#hidePlanLink').hide();
		$('#hidePlan').hide();
	}
	if($('#searchQuery').val()){
		isRenderLeftSection = false;
		$('.hl-searchbar-button').click();
	}
}

function showFuturePlans(plans){
	$('#planTable').show();
	
	if($('#hasCurrentPlans').val() == 'false'){
		$('#currentPlanLink').hide();
		$('#currentPlanLink').css("display","none");
	}else{
		$('#currentPlanLink').show();
	}
	
	thrdColumnProvTypeHideAllTable();
	if(plans == 'med'){
		$('#futureMedical').show();
		showDiv("#medicalThdColProvTypeContent,#hospitalThdColProvTypeContent,#otherProvTypeContent");
		displayBhEapMedicalAndMedDenAndStdAlone();
	}else if(plans == 'den'){
		$('#futureDental').show();
		showDiv("#dentalThdColProvTypeContent");
		displayBhEapDental();	
	}else if(plans == 'both'){
		$('#futureMedical').show();
		$('#futureDental').show();
		showDiv("#medDenThdColProvTypeContent,#hospitalThdColProvTypeContent,#otherProvTypeContent");
		displayBhEapMedicalAndMedDenAndStdAlone();
	}
	else if(plans != 'both' && plans != 'den' && plans != 'med'){
		displayBhEapMedicalAndMedDenAndStdAlone();
	}
	
	if(document.getElementById("currentMedical") !=null){
		$('#currentMedical').hide();
	}
	
	if(document.getElementById("currentDental") !=null){
		$('#currentDental').hide();
	}
	
	$('#futurePlanLink').hide();
	
	/* P20941a August 2014 - Coventry Integration Medicare Advantage High Value  Networks - Rohit : START */
	if($('#medicareProdSessionIndFut').val() == 'true'){
		redirectToStaticPage('/dse/search?site_id=medicare&planStatusSelected=FUTURE');
	}
	else if($('#medicareProdSessionIndFut').val() != 'true' && $('#medicareProdSessionIndCurr').val() == 'true'){
		redirectToStaticPage('/dse/search?site_id=dse&planStatusSelected=FUTURE');
	}
	else if($('#searchQuery').val()){
		isRenderLeftSection = false;
		$('.hl-searchbar-button').click();
	}
	/* P20941a August 2014 - Coventry Integration Medicare Advantage High Value  Networks - Rohit : END */
}

function showCurrentPlans(){
	$('#futureMedical').hide();
	$('#futureDental').hide();
	$('#currentPlanLink').hide();
	$('#planTable').show();
	$('#currentMedical').show();
	$('#currentDental').show();
	$('#futurePlanLink').show();
	thrdColumnProvTypeDisplayLeftCurr();

	/* P20941a August 2014 - Coventry Integration Medicare Advantage High Value  Networks - Rohit : START */
	if($('#medicareProdSessionIndCurr').val() == 'true'){
		redirectToStaticPage('/dse/search?site_id=medicare&planStatusSelected=CURRENT');
	}
	else if($('#medicareProdSessionIndCurr').val() != 'true' && $('#medicareProdSessionIndFut').val() == 'true'){
		redirectToStaticPage('/dse/search?site_id=dse&planStatusSelected=CURRENT');
		/*SR A615-1455 Changes Start- Feb2016-N702925*/
	}else if($('#futureMedical').html() != '' || $('#futureDental').html() != ''){
		if($('#searchQuery').val()){
		isRenderLeftSection = false;
		$('.hl-searchbar-button').click();
		}else{
			redirectToStaticPage('/dse/search?site_id=dse&planStatusSelected=CURRENT');
		}
	/*SR A615-1455 Changes Start- Feb2016-N702925*/	
	}
	/* P20941a August 2014 - Coventry Integration Medicare Advantage High Value  Networks - Rohit : END */
}

function renderLeftSectionForResultsPage(){
	populateUrlParameters();
	var params = $.getUrlVars();
	var byName = $.getUrlVar('frmpage');
	$('#showPlanLink').html('<br/>');
	$('#hidePlanLink').html('<br/>');
	if($('#hasCurrentPlans').val() == 'true' || $('#hasFuturePlans').val() == 'true'){
		if((!$('#hidePlan').is(":visible")) || (byName == 'fromFtSummary'|| byName == 'fromFtDetail')){
			$('#planSection').hide();
			$('#planTable').hide();
			$('#hidePlanLink').hide();
			$('#hidePlan').hide();
			$('#currentMedical').hide();
			$('#currentDental').hide();
			$('#futureMedical').hide();
			$('#futureDental').hide();
			$('#showPlan').show();
			$('#showPlanLink').show();		
		}else if(($('#hidePlan').is(":visible")) || (byName == 'fromFtSummary' || byName == 'fromFtDetail')){
			$('#planSection').hide();
			$('#planTable').hide();
			$('#hidePlanLink').hide();
			$('#hidePlan').hide();
			$('#currentMedical').hide();
			$('#currentDental').hide();
			$('#futureMedical').hide();
			$('#futureDental').hide();
			$('#showPlan').show();
			$('#showPlanLink').show();		
		}else{
			$('#planTable').show();
		}
	}else{
		$('#showPlanLink').hide();
		$('#showPlan').hide();
		$('#hidePlanLink').hide();
		$('#hidePlan').hide();
	}
       leftDistanceSearch();
       /* Start changes for P19134a November release 2013 */
       rendersortDropdown();
       /* End changes for P19134a November release 2013 */
       /*DEF0200742109 fix*/
       if(urlProtocol == urlProtocolNonSecure){
    	   var height = ($(window).height()-317)/2;
    	   $('.dialog-main-wrapper_planModal').css("top", height + "px");
    	   }
       /*DEF0200742109 fix*/
       $(document).scrollTop(0);
}
/************************************************************************************************************
											LEFT SECTION SCRIPTS END HERE
************************************************************************************************************/

/************************************************************************************************************
										CENTER SECTION SCRIPTS START FROM HERE
************************************************************************************************************/
var isErrorParamSet = false;
function searchSubmit(triggerSubmit){
	//project P25230a change
	var planVal = $('#modal_aetna_plans :selected').val();
	if($('#site_id').val()==null || $('#site_id').val()=='' || $('#site_id').val()=='dse'){
		if(planVal == "B2PPO|PPO" || planVal == "BNHNO|HMOHealth Network Only" || planVal == "ACPMC|Managed ChoiceChoice POS II" || planVal == "BNHMO|Banner HMO"  || planVal == "B1PPO|Banner Managed ChoiceChoice POS II" || planVal == "BN1AS|Aetna Select Open AccessAetna Select"  || planVal == "BNOAS|Banner Open Access Aetna Select" || planVal == "OAAS|Elect Choice Open AccessElect Choice" ){
			 var currentPage=window.location.href;
			if(currentPage.indexOf('site_id=dse')!=-1){
				currentPage=currentPage.replace(/site_id=dse/gi, "site_id=banneraetna");
			}
			else{
				currentPage=currentPage.replace(/search#markPage/gi, "search?site_id=banneraetna#markPage");
			}
			location.href=currentPage;
		}
	}
	//content change - 0420
	if($('#searchQuery').val() !=""){
		redirectLogic(trimSpace($('#searchQuery').val()));
	}
var stateCode = $('#stateDD').val();
		 if(stateCode != null && stateCode != ''){
			 setCookie("stateCode", stateCode, 5);	 
		 }
		 var selectedPlan = $('#modal_aetna_plans :selected').val();
		 if(selectedPlan != null && selectedPlan != ''){
			 setCookie("selectedPlan", selectedPlan, 5);
		 }
		 /*-- START CHANGES SR1399 DEC'14 - n596307 --*/
		 var planPrefillFlowSwitch = getCookie('planPrefillFlowSwitch');
		 if(planPrefillFlowSwitch != null && planPrefillFlowSwitch == 'true'){
			 var planDisplayName = $('#modal_aetna_plans :selected').text();
			 if(planDisplayName != null && planDisplayName != ''){
				 setCookie("planDisplayName", planDisplayName, 5);
			 }
			 var externalPlanCode = $('#modal_aetna_plans :selected').val();
			 if(externalPlanCode != null && externalPlanCode != ''){
				 setCookie("externalPlanCode", externalPlanCode, 5);
			 }
		 }
		 /*-- END CHANGES SR1399 DEC'14 - n596307 --*/
	$("#docfindSearchEngineForm").submit(function(){
/*if($('#hl-autocomplete-search').val()!= undefined && $('#hl-autocomplete-search').val() != ghostTextWhatBox 
			 && $('#hl-autocomplete-search').val()!= $('#searchQuery').val()){
			$('#searchQuery').val($('#hl-autocomplete-search').val());
		}*/
		// Content 0616 start
		if($('#switchDefaultSortOrderToDistance')!=null && $('#switchDefaultSortOrderToDistance')!=undefined && $.trim($('#switchDefaultSortOrderToDistance').text()) == 'ON'){
			if($('#sortOrder').val() == null || $('#sortOrder').val() == undefined || $('#sortOrder').val() == "" ){
				 $('#sortOrder').val("distance");
				 $('#QuickZipcode').val("lmcSiteDefaultSortingToDistance");
			 }
		}
		// Content 0616 end
		if($('#searchQuery').val() !=""){
			chk=false;
			$('#hospitalFromDetails').val('false');
			$('#officesLinkIsTrueDetails').val('false');
			if($('#hl-autocomplete-search-location').val()!= undefined && $('#hl-autocomplete-search-location').val() != ghostTextWhereBox && $('#hl-autocomplete-search-location').val()!=''){
				$('#geoSearch').val(trim($('#hl-autocomplete-search-location').val()));
			}
			/* if(!$('#zipCodeEntryField').val()){
		    		$('#zipCodeEntryField').val($('#zipCodeEntryFieldStore').text());
			} */
		}
		if($('#hospitalFromDetails').val()=='true'){
			$('#zipCode').val('');
		}
		geoZipVerificationForInZipFun();
		searchQueryZipValFun();
		mainTypeAheadThrdColValSelectionDecider();
		if((!chk && !$('#searchQuery').val()) || ($('#hl-autocomplete-search').val() == ghostTextWhatBox)){
			return false;
		}else if(triggerSubmit == 'true'){
				var start = new Date().getTime();
				// If we got here because user did a regular search, mark it //as such
				// otherwise, we got here by a different method and it was //already marked
				planTypeForPublic = '';
				if (whyPressed == null || whyPressed == '') {
					markPage('freeText');
				}
				/*-- START CHANGES P20941a August2014 - Medicare Advantage - n596307 --*/
				else if ($('#switchForStatePlanSelectionPopUp')!=null && $('#switchForStatePlanSelectionPopUp')!=undefined
						&& $.trim($('#switchForStatePlanSelectionPopUp').text()) == 'ON' 
							&& whyPressed == 'publicPlan') {
					markPage('publicPlanSelected');
				}
				/*-- END CHANGES P20941a August2014 - Medicare Advantage - n596307 --*/
			
				if($('#currentMedical').is(':visible') || $('#currentDental').is(':visible')){
					$('#currentSelectedPlan').val('CURRENT');
				}else if($('#futureMedical').is(':visible') || $('#futureDental').is(':visible')){
					$('#currentSelectedPlan').val('FUTURE');
				}
				
				/*P8423a Sprint13 - Story6565 Start*/
				$('#navigators').remove();
				if(urlProtocol == urlProtocolSecure){
					$('#selectedMemberForZip').val($('#cmidx :selected').val());
				}
				/*P8423a Sprint13 - Story6565 End*/
				/*if(!chk){
					checkZipcodeInQuery();
				}*/
				
				// clear filter values if a new search
				if (whyPressed !== 'geo') {
					$("#filterValues").val('');
					$("#pagination").val('');
				}

                $(".ui-autocomplete").hide();
				$('#hl-autocomplete-search-location').blur();
				/* SR 1385 Changes start*/
				if($('#geoSearch').val()!= undefined && $('#geoSearch').val()!= null && $('#geoSearch').val() != ghostTextWhereBox && trim($('#geoSearch').val())!=''){
					preValOfGeoBox = $('#geoSearch').val();
				}
				/* SR 1385 Changes End*/
				var mile = $('#withinMilesVal').val();
				if(mile != undefined && mile != null && mile != ""){
					$('#distance').val($('#withinMilesVal').val());
				}
				$.ajax({
					
					beforeSend:function(){loadSpinner()},
				        data: $(this).serialize().replace(/'/g, "~APOS"),
				        type: "GET",
				        url: "search/results",
				        success: function(response)
				        {
						var start = new Date().getTime();
				    		var urlProtocol = window.location.protocol;
						//var urlProtocol = "https:";
				    		/*P8423a Sprint22 - Story7515 Start*/
				    		var errorPageInd =  $(response).find('#errorPageInd').length;   		
				    		if(errorPageInd > 0){				    			
				    			isErrorParamSet = true;
				    			if(isErrorParamSet){
									if($('#container').length < 1){
										$('body').append('<div id=container></div>');
									}
									$('#container').load('search/sysError',{errorCode:'001',errorMsg:'System Error'}, function() {
										isErrorParamSet = false;
										hideSpinner();
									});
									
								}
							triggerSearchButtonEvent();
				    		}else{
				    		/*P8423a Sprint22 - Story7515 End*/	
				            $("#searchResults").html(response);
				            	
				            		
				            $("#searchBoxTitle").css("display","none");
				            $("#searchBoxTitleAfter").css("display","block");
				            /*P8423a Sprint13 - Story6032 Start*/
				            $("#leftStaticSectionFt").css('display','block');					
				            /*P8423a Sprint13 - Story6032 End*/
				            /*P8423a Sprint13 - Story6565 Start*/
							if(urlProtocol == urlProtocolSecure){
								/*P8423a Sprint1 - Story7902 Start*/
								$("#showGANlink").css('display','block');
								/*P8423a Sprint1 - Story7902 End*/
								 /*P8423a Sprint22 - Story7549 Start*/
								 /* Filter Ui Design Changes  Start*/
								 $('#navigators').insertAfter($('#ResultsLeftSectionMenuSecure'));
								 /* Filter Ui Design Changes  End*/
								 $('.filterSection').css("margin-top","10px");
								 /*P8423a Sprint22 - Story7549 End*/
								 /* P20941a August 2014 - Coventry Integration Medicare Advantage High Value  Networks - Rohit : START */
								 $("#ResultsLeftSectionMenuSecure").css('display','block');
								 if($('#site_id').val()!=null && $('#site_id').val()!=undefined && $('#site_id').val() == 'medicare'){
									 $("#sideNav_secure_ft").css('display','none');
								 }
								 else{
									 $("#homeLeftSectionMenuSecure").css('display','none');
								 }
								 /* P20941a August 2014 - Coventry Integration Medicare Advantage High Value  Networks - Rohit : END */
					         	 $(".left_section_public_ft").css('background-color','#E9ECBF');
						         $(".filterPubDF ul").css('background-color','#E9ECBF');
						         $(".filterPubDF ul li a").hover(function(){
						        	    this.style.backgroundColor = "#979e03";
						        	}, function() {
						        	    this.style.backgroundColor = "#E9ECBF";
						        });
							}
							else{
								 /*P8423a Sprint22 - Story7549 Start*/
								 /* Filter Ui Design Changes  Start*/
								 $('#navigators').insertAfter($('#ResultsLeftSectionMenu'));
								 /* Filter Ui Design Changes  End*/
								 $('.filterSection').css("margin-top","10px");
								 /*P8423a Sprint22 - Story7549 End*/
								 $("#ResultsLeftSectionMenu").css('display','block');
						         $("#homeLeftSectionMenu").css('display','none');			         
							}
							/*P8423a Sprint19 - Story8131 Start*/
							if($("#noResultsSection").length != 0){
								$(".mapTable").css('display','none');
								$(".mapTableSecure").css('display','none');
								$("#providers").css('display','none');
							}
							else{
if(urlProtocol == urlProtocolNonSecure && $('#nwTransitionMessage') != null && $('#nwTransitionMessage') != undefined && $('#nwTransitionMessage').html()!=null && $('#nwTransitionMessage').html().length >0 ){
				            	//$('#nwTransitionMessage').html($('#nwTransition').html());
				    			$('#nwTransitionMessage').doDialogDefault({width:350, modal:true, draggable:true, closeOnEscape:true},
				    					 [{id:"nwt_OK", value:"OK",url:"javascript:hideTransitionModal();",onClick:"javascript:hideTransitionModal();", arrow:false}]);
				    			
				    			
				    			triggerTransitionModal();
				    		}
								$(".mapTable").css('display','block');
								$(".mapTableSecure").css('display','block');
								$("#providers").css('display','block');
								$( "#showmapimage" ).parent().prev().css("width","19%");
							}
							/*P8423a Sprint19 - Story8131 End*/
							$('#content #navigators').remove();
							$('.SearchMainTable').css("width","123%");
							/*P8423a Sprint13 - Story6565 End*/
							/*-- START CHANGES P20751b ACO Branding - n596307 --*/
							if($('#sortByDropDownDiv').html() != null && $('#sortByDropDownDiv').html() != ''){
    					    	$('#displaydropdownContent').html($('#sortByDropDownDiv').html());
    					    }
							/*-- END CHANGES P20751b ACO Branding - n596307 --*/
							//ui enhancement
							if($('#sortByDropDownToLeftSideDiv').html() != null && $('#sortByDropDownToLeftSideDiv').html() != ''){
    					    	$('#displaydropdownContent').html($('#sortByDropDownToLeftSideDiv').html());
    					    }
							/*P8423a Sprint14 - Story5225 Changes Start*/
							/*P8423a Sprint14 - Story5225 Changes Start*/
							var withinMileValue = $('#withinMilesValue').text();
							var mile = $('#withinMilesVal').val();
							if(mile != undefined && mile != null && mile != ""){
								withinMileValue = mile;
							}
							var dd = document.getElementById('narrowSearchResultsSelect');
							setSelectedForDropdown(dd, withinMileValue);

							/*P8423a Sprint14 - Story5225 Changes End*/

							/* Start changes for P19134a November release 2013 */
						                       var sortOrderValue = $('#sortOrder').val();

							var ddsortBest = document.getElementById('bestResultsSelect');

							setSelectedForDropdown(ddsortBest,sortOrderValue);

							var ddsortOther = document.getElementById('otherResultsSelect');

							setSelectedForDropdown(ddsortOther,sortOrderValue);

							/* End changes for P19134a November release 2013 */
							/*P8423a Sprint14 - Story5225 Changes End*/
							
							if($('#narrowSearchResultsSelect_prim').length <1){
								convertFormsToDynamicForms('narrowSearchResultsSelect');
							}
                                         /*if($("#isTab1Clicked").val()=='true' || $("#isTab1Clicked").val()=='')
							{
							  convertFormsToDynamicForms('bestResultsSelect');
							}
							else if ($("#isTab2Clicked").val()=='true')
						    {
							  convertFormsToDynamicForms('otherResultsSelect');
						    }else{
							   convertFormsToDynamicForms('otherResultsSelect');
						    }*/

							 convertFormsToDynamicForms('bestResultsSelect');
							 convertFormsToDynamicForms('otherResultsSelect');

							/* End changes for P19134a November release 2013 */
				            // only show the map image if there are search results to map
				            $('#mapContainerOverall').empty(); // clear out old map
				            var names = $('.poi_information');
				            if (names.length > 0)
				            {
				            	//any search results
				            	$('#pretendMap').show('slow');
				            }
                                    if($("#modalSelectedPlan").val() != '' && $("#modalSelectedPlan").val()!= null){
				            	$('#plandisplay').show();
				            	//content 0713
				            	if($("#modalSelectedPlan").val() == "NAPDS"){
				            		$("#NAPtext").css('display','none');
				            	}else{
				            		$("#NAPtext").css('display','none');
				            	}
				            }
				            hideSpinner();
				            /*--- START CHANGES P23695 Medicare Spanish Translation - n596307 ---*/
							$('#textBelowSearchBoxes').css('display','none');
							/*--- END CHANGES P23695 Medicare Spanish Translation - n596307 ---*/
							/*--- START CHANGES for PCR-20564 UI UPDATES - n709197 ---*/
							$('#textBelowSearchBoxesOnResultsPage').css('display','block');
                                                        $('#textBelowSearchBoxesOnResultsPageSecure').css('display','block');
							/*--- END CHANGES for PCR-20564 UI UPDATES - n709197 ---*/
                           	/* Story 10255 Start*/
				           var didyou = null;
				            didyou = $('#didmeans').html();				            
				            if(didyou != undefined && didyou != null && didyou.length > 50){
				            	$('#didyou').show();
					            $('#newLocDidyouMean').html(didyou);
                                          $('#newLocDidyouMean').show();
				            }
				            /* Story 10255 end */
				            if(isRenderLeftSection == true){
				            	renderLeftSectionForResultsPage();
				            }
				            /*P8423a Sprint15 - Story4454 Changes Start*/
				            //Fix incase of external provider coming within list
				            positionExternalProvider(); 
				            
				            // build the filter menu
				    		addFilterValues();
						    whyPressed = "";
						    
						    /* P08-8423a Sprint22 - Story9241 Changes Start */
						
						    var searchBoxValueModified = false;
						    $(document).ready(function(){
						    	if($('#hl-autocomplete-search').val() != undefined){
						    		if($('#hl-autocomplete-search').val().length >0){
								    	$('#isMultiSpecSelected').val('');
								    }
						    		else{
								    	$('#hl-autocomplete-search').val('');
								    	searchBoxValueModified = true;
								    }
						    	}
								if(!searchBoxValueModified){
									if($('#hl-autocomplete-search').val() != undefined){
									/* P23695a Blue Link changes - Start - N204189  */
										if( $('#actualDisplayTerm').val() == 'undefined' || $('#actualDisplayTerm').val() == '' )
										{
											$('#hl-autocomplete-search').val($('#searchQuery').val());
										}
										else
										{
											$('#hl-autocomplete-search').val($('#actualDisplayTerm').val());
											//$('#actualDisplayTerm').val('');
										}
										/* P23695a Blue Link changes - End*/
								    }
								}
								/* P08-8423a Sprint22 - Story9241 Changes End */
								    
								$('.hl-autocomplete .hl-search-box .hl-searchbar .hl-searchbar-input').css('color','#000000');
								$('.hl-autocomplete .hl-search-box .hl-searchbar .hl-searchbar-input').css('font-style','normal');

							    /*Changes for back button geo box start*/
									
								if(urlProtocol == urlProtocolNonSecure){
									if($('#geoSearch').val()!=null && $('#geoSearch').val()!='' && $('#geoSearch').val()){
										changeFormatGeoLocation();
										$('#hl-autocomplete-search-location').val($('#geoSearch').val());
									}
								}
								else if(urlProtocol == urlProtocolSecure){
									if((!($('#restUser').val() || $('#guestUser').val())) || (($('#restUser').val() || $('#guestUser').val()) && trim($('#geoSearch').val())!=trim($('#memberZipCode').val()))){
										if($('#geoSearch').val()!=null && $('#geoSearch').val()!='' && $('#geoSearch').val()){
											changeFormatGeoLocation();
											$('#hl-autocomplete-search-location').val($('#geoSearch').val());
										}
									}
								}
								/*Changes for back button geo box end*/
						    });
						    triggerSearchButtonEvent();
						    }

						    if(ie6Check){
						    	if(urlProtocol == urlProtocolNonSecure){
									$('div#content').removeClass('fixForIE6');
								}else{
									$('div#content').addClass('fixForIE6SecureResults');
								}
						    }
						    //$('#quickSearchTypeThrCol').val('');
						    $('#filterLeftZipSearch').val('');
						    
						/* Start changes for SR1317 - Aug 2013 */
						var state = $('#stateDiv').text();
						if(state != null && state == "CA"){ 
							showCalHmoPopUp();
						}
						/* End changes for SR1317 - Aug 2013 */
                                    $(".ui-autocomplete").hide();
                                     /*--Start Changes SR1398 Dec14 release--*/
				     var lastUpdatedDatabaseFastDate = $('#lastUpdatedDatabaseFastDate').text();
                    				if(lastUpdatedDatabaseFastDate != null && lastUpdatedDatabaseFastDate != ""){
                    					$('#lastUpdatedDatabaseDate').text(lastUpdatedDatabaseFastDate);
                    				}
				     /*--End Changes SR1398 Dec14 release--*/
				    var PageLastUpdatedText = $('#PageLastUpdated').text();
            					    if(PageLastUpdatedText != null && PageLastUpdatedText != ''){
            					    	if($('#PageLastUpdatedFooter') != undefined){
            					    		$('#PageLastUpdatedFooter').text(PageLastUpdatedText);
            					    		if($('#site_id').val() == 'medicare'){
            				    				$('#PageLastUpdatedFooter').prepend("");
            				    			}
            					    	}
            						}
            					    /*-- START CHANGES P20751b ACO Branding - n596307 --*/
            					    handleACOFunctionality();
            					    /*-- END CHANGES P20751b ACO Branding - n596307 --*/
            					    //content 0504
            						$('#homePageInfoText').css('display','none');
            						//CONTENT 0922
							var secureProd = $('#secureMedPlan').text();
            						if( secureProd == "NAPDS"){
            							$("#napTextInSecureDiv").css('display','block');
            						}else{
            							$("#napTextInSecureDiv").css('display','none');
            						} 
				        }
				    });
		    triggerSubmit = 'false';
		    if($('#hospitalFromDetails').val()=='true'){
			$('#zipCode').val('');
		    }
			return false;
		}
	});
}

/*P8423a Sprint17 - Story6190 Changes Start */
function checkValidZipCode(){
	var zipVal = $('#zipCode').val();
	if(($('#zipCode').val().length > 0 && $('#zipCode').val().length < 5 && whyPressed == 'geo') || isNaN(zipVal)){
		return false;
	}else{
		return true;
	}
}	
/*P8423a Sprint17 - Story6190 Changes End */

function validateZipCode(zipCode){
	if((zipCode.length > 0 && zipCode.length < 5) || isNaN(zipCode)){
		return false;
	}else{
		return true;
	}
}

function validateZipVal(zipCode){
	if((zipCode.length < 0 || zipCode.length > 5) || isNaN(zipCode)){
		return false;
	}else{
		return true;
	}
}

function checkZipcodeInQuery(){
	var query = $('#searchQuery').val();
	var regex = /\d{5}(-\d{4})?/;
	var zipCodeEntry = $('#zipCode').val();

	/* 8423a Sprint16 - Story7396 Changes Start Secure Changes */
	if(urlProtocol == urlProtocolSecure){
		if(whyPressed != null && whyPressed == 'geo'){
			$('#loggedInZip').val("false");
		}else{
			$('#loggedInZip').val("true");
		}
	}
	/*P8423a Sprint16 - Story5225 Changes End */
	
	if (query != null && query.length > 0){
		var zip = query.match(regex);
		// Checks for zip code in user query
		if(zip != null && zip.length > 0){
			if(urlProtocol == urlProtocolSecure){
				$('#loggedInZip').val("false"); // Set logged in zip to false, if zip is present in query anytime
			}
			// Checks for zip code in filter section
			if(whyPressed != null && whyPressed == 'geo'){
				$("#zipCode").val($('#zipCode').val());
			}
			else{
				$("#zipCode").val(zip[0]);
				$("#distance").val('0'); //Make distance empty on click of Search button with no zip in searchQuery
			}
		}
		else if(zipCodeEntry != null && zipCodeEntry.length > 0 && whyPressed != null && whyPressed == 'geo'){
			$("#zipCode").val(zipCodeEntry);
			if(whyPressed != null && whyPressed != 'geo'){
				$("#distance").val('0'); //Make distance empty on click of Search button with no zip in searchQuery
			}
		}
		else{
			//Removed since currentGeolocationZip is not used or set anywhere
			/*if(currentGeolocationZip != null){
				$("#zipCode").val(currentGeolocationZip);
			}else{
				$("#zipCode").val("");*/
				if(whyPressed != null && whyPressed != 'geo'){
					if(urlProtocol == urlProtocolSecure){
						$('#loggedInZip').val("true");
					}
					$("#distance").val('0'); //Make distance empty on click of Search button with no zip in searchQuery
				}
			//}
		}
	}
}

function getGeolocation(){
	if(navigator.geolocation){
		navigator.geolocation.getCurrentPosition(function(position){
			$.getJSON('http://www.mapquestapi.com/geocoding/v1/reverse?key=Gmjtd%7Clu612lubnd%2Cb5%3Do5-lw8w0&lat=' + position.coords.latitude + '&lng=' + position.coords.longitude, function(data) {
				currentGeolocationZip = data.results[0].locations[0].postalCode;
			});
		},
		function(){
			console.log("No geolocation available.");
		});
	}
}

function loadSpinner(){
	showSpinner();
}

function clickedPagination(page){
	whyPressed = 'geo';
	$("#pagination").val(page);
	/* if(urlProtocol == urlProtocolSecure){
		var filterZip = $("#zipCodeEntryField").val();
		$('#zipCode').val(filterZip)
	} */
	$('#suppressFASTDocCall').val('true');
	goClick();
	markPage('clickedPagination');
	//$("#pagination").val("");
	
}

function clickedPaginationPcpSpec(page,preVal){
	whyPressed = 'geo';
	$("#pagination").val(page);
	/* if(urlProtocol == urlProtocolSecure){
		var filterZip = $("#zipCodeEntryField").val();
		$('#zipCode').val(filterZip)
	} */
	$('#lastPageTravVal').val(preVal);
	$('#suppressFASTDocCall').val('true');
	goClick();
	markPage('clickedPagination');
	//$("#pagination").val("");
	
}

function clickedFilter(filterValues){
	$("#filterValues").val(filterValues);
	$("#pagination").val("");
	whyPressed = 'geo';
	$('#suppressFASTDocCall').val('true');
	/*-----START CHANGES P19791a Exchange August 2013-----*/
	if($('#site_id').val() == 'QualifiedHealthPlanDoctors'){
		searchByPlanQHP();
	}
	/*-----END CHANGES P19791a Exchange August 2013-----*/
	goClick();
	markPage('clickedFilter');
}

function showSearchTips(){
	$("#searchTipsLink").css("display","none");
	$("#searchTips").css("display","block");
}

function hideSearchTips(){
	$("#searchTipsLink").css("display","block");
	$("#searchTips").css("display","none");
}

function copyright(){
	year = (new Date()).getFullYear();
	var copRightInfo = 'Copyright &copy; 2001-' + year + '&nbsp;Aetna Inc.'
	$('#footerCopyRight').html(copRightInfo);
}

//map information outside of map function
var latt,longg,dirs;

function showDetailsPageMap(){
	if ($('#mapContainer div').length <= 0) {
		/*Apply the 'show mappable' class to the table layout.*/
		$('#details_content_FT #provDetailsAndRightSideBar td.third_FT table').addClass('showMapInLayoutTable');
		/*--- START CHANGES P23695 Medicare Spanish Translation - n596307 ---*/
		var closeText = $('#mapCloseButtonTextDiv').html();
		var directionText;
		if($.getUrlVar('site_id') == 'medicare' && $.getUrlVar('langPref') == 'sp'){
			directionText = 'indicaciones';
		}
		else{
			directionText = 'directions';
		}
		/*Set up the map: */
		$('#mapContainer').append($('<div id="map" class="map"></div>'));
		$('#mapContainer').append($('<div id="mapCloseButton" tabindex="0"><table><tr><td style="display: block;" id="mapClose"><label style="cursor: pointer" onclick="return closeDetailsPageMap();">&nbsp;'+closeText+'&nbsp;</label></td></tr></table></div>'));
		/*--- END CHANGES P23695 Medicare Spanish Translation - n596307 ---*/
		var info = $('#mapQuestInformation #information').html();
		if (undefined == info || null == info) {
			info = "";
		}
		var rolloverHTML = info + 
		"<hr><a href='javascript:directions(-1);'>"+directionText+"</a>";
			
		latt = $('#mapQuestInformation #latitude').html();
		latt = parseFloat(latt);
		longg = $('#mapQuestInformation #longitude').html();
		longg= parseFloat(longg);
		dirs = $('#mapQuestInformation #directions').html();

		/*Create an object for options*/
		var options={
				elt:document.getElementById('map'),        /*ID of element on the page where you want the map added*/
				zoom:16,                                   /*initial zoom level of map*/
				latLng:{lat:latt, lng:longg},   /*center of map in latitude/longitude*/
				mtype:'map',                               /*map type (map)*/
				bestFitMargin:0,                           /*margin offset from the map viewport when applying a bestfit on shapes*/
				zoomOnDoubleClick:true                     /*zoom in when double-clicking on map*/
		};

		/*Construct an instance of MQA.TileMap with the options object*/
		try {
			window.map = new MQA.TileMap(options);
			var basicPointer =  new MQA.Poi( {lat:latt, lng:longg} );
			var icon=new MQA.Icon("/dse/assets/images/pins/pin.png",26,34);
			basicPointer.setIcon(icon);
			basicPointer.setRolloverContent(rolloverHTML);

			/*This will add the POI to the map in the map's default shape collection.*/
			map.addShape(basicPointer);
			MQA.withModule('largezoom', function() {
				map.addControl(
					new MQA.LargeZoom(),
					new MQA.MapCornerPlacement(MQA.MapCorner.TOP_LEFT, new MQA.Size(5,5))
				);
			});
		} catch (e) {alert(e);}
	}
	
	/*n767258 508 Requirements*/
	$('#mapCloseButton').keydown(function(event){ 
	    var keyCode = (event.keyCode ? event.keyCode : event.which);   
	    if (keyCode == 13) {
	    	closeDetailsPageMap();
	    }
	});
	
	/*Apply the 'show mappable' class to the table layout.*/
	$('#details_content_FT #provDetailsAndRightSideBar td.third_FT table').addClass('showMapInLayoutTable');
	$('#mapContainer').show('slow');
	return false;
}

function closeDetailsPageMap() {
	$('#details_content_FT #provDetailsAndRightSideBar td.third_FT table').removeClass('showMapInLayoutTable');
	$('#mapContainer').hide('slow');
}

// map information outside of map function
var names,numbers,lats,longs,addr,urls;
	
function showResultsPageMap(pinNumber){
	// this is the pin that should be centered
	if (pinNumber === undefined) {
		pinNumber = -1;
           $('#mapContainerOverall div').remove();
	}
	if (pinNumber >= 0) {
		closeResultsPageMap();
		$('#mapContainerOverall div').remove();
	}
	
	if ($('#mapContainerOverall div').length <= 0) {
		//Set up the map:
		/*--- START CHANGES P23695 Medicare Spanish Translation - n596307 ---*/
		var closeText = $('#mapCloseButtonTextDiv').html();
		var directionText;
		if(site_id == 'medicare' && langPref == 'sp'){
			directionText = 'indicaciones';
		}
		else{
			directionText = 'directions';
		}
		$('#mapContainerOverall').append($('<div id="mapOverall" class="mapOverall"></div>'));
		$('#mapContainerOverall').append($('<div id="mapCloseButton" tabindex="0"><table><tr><td style="display: block;" id="mapClose"><label style="cursor: pointer" onclick="return closeResultsPageMap();">&nbsp;'+closeText+'&nbsp;</label></td></tr></table></div>'));
		/*--- END CHANGES P23695 Medicare Spanish Translation - n596307 ---*/
		
		// get all of the provider locations for the POIs
		names = $('.poi_information');
		numbers = $('.poi_itemNumber');
		lats = $('.poi_latitude');
		longs = $('.poi_longitude');
		addr = $('.poi_directions');  // for route directions
		urls = $('.poi_detailsPage');
		
		var declutters = [];
		
		// set lats to be real numbers
		for (var i=0; i<names.length; i++){
			try {
				lats[i] = parseFloat(lats[i].innerHTML);
			} catch (e) {
				lats[i] = "";
			}
			try {
				longs[i] = parseFloat(longs[i].innerHTML);
			} catch (e) {
				longs[i] = "";
			}
			declutters[i] = false;
		}
		
		// only declutter locations where the coordinates are the same
		for (var i=0; i<names.length-1; i++){
			for (var j=i+1; j<names.length; j++) {
				try {
					var latDiff = Math.abs(lats[i]-lats[j]);
					var lonDiff = Math.abs(longs[i]-longs[j]);
					if (latDiff < .001 && lonDiff < .001) {
						declutters[i] = true;
						declutters[j] = true;
						break;
					}
				} catch (e){}
			}
		}

		// make a collection of all the points of interest
		var pois=new MQA.ShapeCollection();
		pois.collectionName='search_results_pois';
//		pois.minZoomLevel=7;

		for (var i=0; i<names.length; i++) {
			try {
				var info = names[i].innerHTML;
				var rolloverHTML = info + 
					"<a href='javascript:directions(" + i + ")'>"+directionText+"</a>";
				var row = numbers[i].innerHTML;
				if (row > 999) row = ""; 
				var url = urls[i].innerHTML;
				var basicPointer = new MQA.Poi({
					lat: lats[i],
					lng: longs[i]
				});
				basicPointer.setDeclutterMode(declutters[i]);
				var icon=new MQA.Icon("assets/images/pins/pin" + row + ".png",26,34);
				basicPointer.setIcon(icon);
				basicPointer.setRolloverContent(rolloverHTML);
				basicPointer.detailsPage = url;
				MQA.EventManager.addListener(basicPointer, 'click', pinClick);
				pois.add(basicPointer);
//				alert('#' + row + ': ' + lats[i] + ',' + longs[i]);
			} catch (e) {alert(e);}
		} // for
		
		//Create an object for options
		var options = { elt: document.getElementById('mapOverall'),  mtype: 'map'};
             
		//Construct an instance of MQA.TileMap with the options object
		try {
			window.map = new MQA.TileMap(options);
			map.addShapeCollection(pois);
			MQA.withModule('largezoom', function() {
			    map.addControl(
			      new MQA.LargeZoom(),
			      new MQA.MapCornerPlacement(MQA.MapCorner.TOP_LEFT, new MQA.Size(5,5))
			    );
			  });

			map.bestFit();
			
			// center the map if a center pin number was specified
			if (pinNumber >= 0) {  // a center pin
				var lat = lats[pinNumber];
				var lon = longs[pinNumber];
				var latLng = new MQA.LatLng(lat,lon);
				map.setZoomLevel(15);
				map.setCenter(latLng);
			}

		} catch (e) {
			alert(e);
		}
	} // if no map showing
	
	/* n767258 508 Requirements*/
	$('#mapCloseButton').keydown(function(event){ 
	    var keyCode = (event.keyCode ? event.keyCode : event.which);   
	    if (keyCode == 13) {
	    	closeResultsPageMap();
	    }
	});

	//Apply the 'show mappable' class to the table layout.
	$('#pretendMap').addClass('pretendMap');
	$('#pretendMap').hide('slow');
	$('#mapPadding').show('slow');
	$('#mapContainerOverall').show('slow');
	$('#mapContainerOverall')[0].scrollIntoView(true)
    return false;
}

/* P8423a - Sprint0 - Story9466  Changes Start */
function closeProvLocMap(){
	$('#provMap').hide();
	adjustMapModalHeight();
	$('#provLocMapButton').css("width","98px");
	$('#provLocMapButton').css("padding-left","0px");
	$('#provLocMapButton').css("background-color","#FFFFFF");
	$('#provLocMapButton').html('<a id="provLocMapLink" href="javascript:void(0);" onclick="javascript:openProvLocMap();"><img id="openMapImage" class="collapseImage" src="/dse/assets/images/buttons_open2.gif" /><font style="padding-top:5px;">SHOW MAP</font></a>');
	
}

function openProvLocMap(){
	$('#provMap').show();
	adjustMapModalHeight();
	$('#provLocMapButton').css("width","88px");
	$('#provLocMapButton').css("background-color","#D7D7D7");
	$('#provLocMapButton').html('<a id="provLocMapLink" href="javascript:void(0);" onclick="javascript:closeProvLocMap();"><img id="closeMapImage" class="collapseImage" src="/dse/assets/images/buttons_close2.gif" /><font style="padding-top:5px;">HIDE MAP</font></a>');
}

function showProvLocMap(provLattitude,provLongitude,info){
	$('#providerLocationMap').append('<div id="provMap" style="width: 602px;height: 300px;background-color: rgb(229, 227, 223);"></div>');
	$('#providerLocationMap').append('<div id="provLocMapButton"><a id="provLocMapLink" href="javascript:void(0);" onclick="javascript:closeProvLocMap();"><img id="closeMapImage" class="collapseImage" src="/dse/assets/images/buttons_close2.gif" /><font style="padding-top:5px;">HIDE MAP</font></a></div>');
			
	var rolloverHTML = info;
	var lattitude = parseFloat(provLattitude);
	var longitude = parseFloat(provLongitude);

	var options={
					elt:document.getElementById('provMap'),        /*ID of element on the page where you want the map added*/
					zoom:16,                                   /*initial zoom level of map*/
					latLng:{lat:lattitude, lng:longitude},    /*center of map in latitude longitude*/
					mtype:'map',                               /*map type (map)*/
					bestFitMargin:0,                           /*margin offset from the map viewport when applying a bestfit on shapes*/
					zoomOnDoubleClick:true                     /*zoom in when double-clicking on map*/
			};

	try {
				window.map = new MQA.TileMap(options);
				var basicPointer =  new MQA.Poi( {lat:lattitude, lng:longitude} );
				var icon=new MQA.Icon("/dse/assets/images/pins/pin.png",26,34);
				basicPointer.setIcon(icon);
				basicPointer.setRolloverContent(rolloverHTML);

				/*This will add the POI to the map in the map's default shape collection.*/
				map.addShape(basicPointer);
				map.addControl(
						new MQA.LargeZoom(),
						new MQA.MapCornerPlacement(MQA.MapCorner.TOP_LEFT, new MQA.Size(5,5))
				);
			} catch (e) {alert(e);}


	$('#providerLocationMap').css("display","block");
	return false;
}

function adjustMapModalHeight(){
	var mapTransHeight = $('#mapDialogBox.dialog-content').parents('div.dialog-main-wrapper').children('div.dialog-content-wrap').height();
	$('#mapDialogBox.dialog-content').parents('div.dialog-main-wrapper').children('div.dialog-transparent-border').css("height",mapTransHeight+29);
}
/* P8423a - Sprint0 - Story9466  Changes End */

// open up the map directions.  If itemNumber is >= 0, the address comes from the
// search results.  If it is -1, the address comes from a details page
var apiToAddress;
function directions(itemNumber) {
	// load the directions HTML onto the page.  When it is loaded, process it.
	var directionsHTML;
	if (itemNumber >= 0) {
		directionsHTML = $('#mapDirectionsOverall');
		directionsHTML.load('/dse/assets/html/map_directions.html', function() {
			$('#directions-item-number').html(itemNumber);  // save it for next function call
			/* P8423a - Sprint0 - Story9466  Changes Start */
			var provNameForMap;
			if(ieVersion == 8){
				provNameForMap = names[itemNumber].innerText;
				apiToAddress = addr[itemNumber].innerText;
			}else{
				provNameForMap = names[itemNumber].textContent;
				apiToAddress = addr[itemNumber].textContent;
			}
			
			var addrArray = [];
			var addrAfterUpdate = [];
			if(provNameForMap!=null){
				addrArray = provNameForMap.split('\n');
				var updatedCount = 0;
				for(count=0;count<addrArray.length;count++){
					if($.trim(addrArray[count]).length>0){
						addrAfterUpdate[updatedCount]= $.trim(addrArray[count]);
						updatedCount ++;
					}
				}
			}
			
			var provInfoToDisplay = '';
			for(count=0;count<addrAfterUpdate.length;count++){
				if(count<addrAfterUpdate.length-3){
					provInfoToDisplay += addrAfterUpdate[count] + '<br/>';
				}else{
					if(count<addrAfterUpdate.length-2){
						provInfoToDisplay += addrAfterUpdate[count] + ', ';
					}else{
						provInfoToDisplay += addrAfterUpdate[count] + ' ';
					}
				}
			}
			
			if(ieVersion == 8){
				var toAddress = document.getElementById("to-address");
				toAddress.innerHTML = provInfoToDisplay;
			}else{
				$('#to-address').html(provInfoToDisplay);
			}

			$('#mapDirectionsOverall').hide();
			$('#mapDialogBox').html('');
			$('#mapDialogBox').html($('#mapDirectionsOverall').html());
			$('#mapDialogBox').append('<br/>');
			if($('#providerLocationMap').length>0){
				$('#providerLocationMap').remove();
			}
			$('#mapDialogBox').append('<div id="providerLocationMap"></div>');
			showProvLocMap(lats[itemNumber],longs[itemNumber],names[itemNumber].innerHTML);
			$('#mapDirectionsOverall').html('');
			$('#mapDialogBox.dialog-content').parents('div.dialog-main-wrapper').children('div.dialog-content-wrap').children('div.dialog-title').html('Directions');
			$('#mapDialogBox').trigger('show');
			$('#mapDialogBox.dialog-content').parents('div.dialog-main-wrapper').css("top","100px");
			
			if(urlProtocol == urlProtocolNonSecure){
				$('#mapDialogBox.dialog-content').parents('div.dialog-main-wrapper').children('div.dialog-content-wrap').css("background-color","#ffffff");
				$('#mapDialogBox.dialog-content').parents('div.dialog-main-wrapper').children('div.dialog-content-wrap').css("border-color","#D1D1D1");
				$('#getDirMapButton').removeClass('mapgetDirSec');
				$('#getDirMapButton').addClass('mapgetDir');
				$('#from-address').css("height","17px");
			}
			adjustMapModalHeight();
			/* P8423a - Sprint0 - Story9466  Changes End */

		});  // load HTML
	} else {
		apiToAddress = dirs;
		directionsHTML = $('#mapDirectionsOverall');
		directionsHTML.load('/dse/assets/html/map_directions.html', function() {
		$('#directions-item-number').html(itemNumber); // save it for next function call
		//$('#to-address').val(dirs); // display it on page
		// open the directions div
		//$('#mapDirections').show('slow');
		//$('#mapDirections')[0].scrollIntoView(true)
		var info = $('#mapQuestInformation #information').html();
		if (undefined == info || null == info) {
		info = "";
		}
		
		var addrArray = [];
		var addrAfterUpdate = [];
		if(dirs!=null){
			addrArray = dirs.split('\n');
			var updatedCount = 0;
			for(count=0;count<addrArray.length;count++){
				if($.trim(addrArray[count]).length>0){
					addrAfterUpdate[updatedCount]= $.trim(addrArray[count]);
					updatedCount ++;
				}
			}
		}
		
		
		var provInfoToDisplay = '';
		provInfoToDisplay += info + '<br/>';
		
		for(count=0;count<addrAfterUpdate.length;count++){
			if(count<addrAfterUpdate.length-2){
				provInfoToDisplay += addrAfterUpdate[count] + '<br/>';
			}else{
				if(count<addrAfterUpdate.length-1){
					provInfoToDisplay += addrAfterUpdate[count] + ', ';
				}else{
					provInfoToDisplay += addrAfterUpdate[count] + ' ';
				}
			}
		}
		
		if(ieVersion == 8){
		var toAddress = document.getElementById("to-address");
		toAddress.innerHTML = provInfoToDisplay;
		}else{
		$('#to-address').html(provInfoToDisplay);
		}
		$('#mapDirectionsOverall').hide();
		$('#mapDialogBox').html('');
		$('#mapDialogBox').html($('#mapDirectionsOverall').html());
		$('#mapDialogBox').append('<br/>');
		if($('#providerLocationMap').length>0){
		$('#providerLocationMap').remove();
		}
		$('#mapDialogBox').append('<div id="providerLocationMap"></div>');
		latt = $('#mapQuestInformation #latitude').html();
		latt = parseFloat(latt);
		longg = $('#mapQuestInformation #longitude').html();
		longg= parseFloat(longg);
		showProvLocMap(latt,longg,info);
		$('#mapDirectionsOverall').html('');
		$('#mapDialogBox.dialog-content').parents('div.dialog-main-wrapper').children('div.dialog-content-wrap').children('div.dialog-title').html('Directions');
		$('#mapDialogBox').trigger('show');
		$('#mapDialogBox.dialog-content').parents('div.dialog-main-wrapper').css("top","100px");
		if(urlProtocol == urlProtocolNonSecure){
		$('#mapDialogBox.dialog-content').parents('div.dialog-main-wrapper').children('div.dialog-content-wrap').css("background-color","#ffffff");
		$('#mapDialogBox.dialog-content').parents('div.dialog-main-wrapper').children('div.dialog-content-wrap').css("border-color","#D1D1D1");
		$('#getDirMapButton').removeClass('mapgetDirSec');
		$('#getDirMapButton').addClass('mapgetDir');
		$('#from-address').css("height","17px");
		}
		adjustMapModalHeight();
		}); // load HTML
	}
}

function printMapModalContent(){
if(ieVersion == 8){
//$('head').append('<meta http-equiv="X-UA-Compatible" content="IE=7"/>');
//document.createStyleSheet().addRule(".rvml", "behavior:url(#default#VML)");
//$('body').prepend('<v:shape></v:shape>');	
$('#mapDialogBox.dialog-content').parents('div.dialog-main-wrapper').addClass('mapDialogBoxPrintCSS');
		$('#directions-results').addClass('dirResultsPrint');
		//$('.mqa_gs').children('svg').children('polyline').addClass('polylinePrint');
		//$('.mqa_gs').children('svg').removeAttr('opacity');
		$('#provMap').addClass('mapPrint');		
		$('#mapDialogBox.dialog-content').parents('div.dialog-main-wrapper').children('div.dialog-transparent-border').addClass('mapTransBroderPrint');
		$('head').append('<style> @media print{body{visibility:hidden;} v\:* {behavior: url(#default#VML);} .mapPrint{width: 602px;height: 300px;overflow: hidden;} .mapDialogBoxPrintCSS{visibility:visible;top:10px!important;position:absolute;left:0px!important;display: block;right:0px!important;} .mapTransBroderPrint{display:none;} .dirResultsPrint{height:auto;} #getDirMapButton{background-image: url("/dse/assets/images/BTN_gold_center_fill.gif"); color: white; font-size: 12px; font-weight: bold; height: 20px;} #mapDialogBox{width:600px;}}</style>');
		$('#mapDialogBox.dialog-content').addClass('mapDialogBoxWidth');
		$('head').append('<style> @media screen{.mapDialogBoxWidth{display: block;width: 600px;} @media print{.mapDialogBoxWidth{display: block;width: 600px!important;}}</style>');
		$('#mapDialogBox.dialog-content').removeAttr('style');
		$('.mqa_gs').children('svg').children('polyline').css("z-index","10");
		window.print();
}	
else{	$('#mapDialogBox.dialog-content').parents('div.dialog-main-wrapper').children('div.dialog-transparent-border').addClass('mapTransBroderPrint');
	var transHeight = $('#mapDialogBox.dialog-content').parents('div.dialog-main-wrapper').children('div.dialog-transparent-border').height();
	var transWidth = $('#mapDialogBox.dialog-content').parents('div.dialog-main-wrapper').children('div.dialog-transparent-border').width();
	$('head').append('<style> @media screen{.mapTransBroderPrint{height:' + transHeight + 'px; width:' + transWidth + 'px; position:absolute;z-index:10001;}}</style>')
	$('#mapDialogBox.dialog-content').parents('div.dialog-main-wrapper').children('div.dialog-transparent-border').removeAttr('style');
	$('#mapDialogBox.dialog-content').addClass('mapDialogBoxWidth');
	$('head').append('<style> @media screen{.mapDialogBoxWidth{display: block;width: 600px;} @media print{.mapDialogBoxWidth{display: block;width: 700px!important;}}</style>');
	$('#mapDialogBox.dialog-content').removeAttr('style');
	if($('#detailsContentTable').length>0){
		$('#mapDialogBox.dialog-content').parents('div.dialog-main-wrapper').addClass('mapModalStyleDetailsPage');
	}else{
		$('#mapDialogBox.dialog-content').parents('div.dialog-main-wrapper').addClass('mapModalStyle');
	}
	$('#mapDialogBox.dialog-content').parents('div.dialog-main-wrapper').addClass('mapDialogBoxPrintCSS');
	//$('#mapDialogBox.dialog-content').parents('div.dialog-main-wrapper').removeAttr('style');
	$('head').append('<style> @media print{.mapTransBroderPrint{display:none;width:0px!important;} .mapDialogBoxPrintCSS{top:10px!important;position:absolute;left:10px;z-index: 10000; display: block;right:0px!important;} #directions-results{height:auto!important;} .mapgetDir{url(/dse/assets/images/go_btn_center.jpg) !important; height: auto !important; padding-left: 10px !important;padding-right: 10px!important;width: auto!important;}}</style>');
	$('#mapDialogBox.dialog-content').parents('div.dialog-main-wrapper').printElement({
			printBodyOptions:
	        {
	           styleToAdd:'color:#FFFFFF;'
	        }}
	);
}
}

function directionsSearch() {
	/* P8423a - Sprint0 - Story9466  Changes Start */
	//$('head').append('<meta http-equiv="X-UA-Compatible" content="IE=EmulateIE7"/>');
	var iefix=document.createElement('meta');
	iefix.setAttribute("http-equiv", "X-UA-Compatible");
	iefix.setAttribute("content", "IE=EmulateIE7");
	document.getElementsByTagName('head')[0].appendChild(iefix);
	$('#provLocMapButton').show();
	$('#mapModalSpinner').remove();
	$('#mapDialogBox').append('<div id="mapModalSpinner"></div>');
	showAndPlaceBusyModalPopupBox($('#mapModalSpinner'),170,410);
	$('.TransparentBorder').css("background-color","#333333");
	$('#mapModalSpinner').show();
	$('#printProvLocMapDiv').remove();
	$('#mapDialogBox').append('<div id="printProvLocMapDiv"><br/><table width="100%">'+
			'<tr>'+
				'<td width="10%" id="distMapLabel"><b>Distance:</b></td>'+
				'<td id="distMapValue"></td>'+
				'<td></td>'+
			'</tr>'+
			'</table>'+
			'<table width="100%">'+
			'<tr>'+
				'<td width="21%" id="timeMapLabel"><b>Estimate Travel time:<b></td>'+
				'<td id="timeMapValue"></td>'+
				'<td id="printProvLocMap"><a href="javascript:void(0);"'+
					' onclick="javascript:printMapModalContent();"><img '+
					'src="/dse/assets/images/printIcon.jpg" /></a></td>'+
			'</tr>'+
		'</table><br/></div>');
	adjustMapModalHeight();
	/* P8423a - Sprint0 - Story9466  Changes End */
	// clear any old route data
	$('#directions-results').html('');
	MQA.withModule('directions', function() {
		map.removeRoute()
	});
	
	var itemNumber = $('#directions-item-number').html();
	var toLat;
	var toLon;
	var fromAddress = $('#from-address').val();
	/* P8423a - Sprint0 - Story9466  Changes Start */
	// remove linebreaks in to address
	var toAddress = apiToAddress;
	// remove all the junk introduced by the JSP
	toAddress = toAddress.replace(/(\r\n|\n|\r|\t)/gm," ");
	while(toAddress.indexOf('  ')!=-1) { 
		toAddress = toAddress.replace('  ',' ');
	}	

	/* P8423a - Sprint0 - Story9466  Changes End */
	
	if (itemNumber >= 0) {  // from results page
		toLat = lats[itemNumber];
		toLon = longs[itemNumber];
		MQA.withModule('directions', function() {
			map.addRoute([
			  fromAddress,toAddress],
	
			  // Add route options options 
			  {ribbonOptions:{draggable:true}},
	
		      // Add the callback function to display the route information  
			  displayNarrative
			);
		});
	} else {  // from details page
		toLat = latt;
		toLon = longg;
		MQA.withModule('directions', function() {
			map.addRoute([
			  fromAddress,toAddress],
	
			  // Add route options options 
			  {ribbonOptions:{draggable:true}},
	
		      // Add the callback function to display the route information  
			  displayNarrative
			);
		});
	}
}

function displayNarrative(data) {
	// adapted from AmpQuest API example
//	console.log(JSON.stringify(data));
	if(data.route){
		var legs = data.route.legs, html = '', i = 0, j = 0, trek, maneuver;
		html += '<table><tbody>';

		for (; i < legs.length; i++) {
			for (j = 0; j < legs[i].maneuvers.length; j++) {
				maneuver = legs[i].maneuvers[j];
				html += '<tr>';
				html += '<td>';

				if (maneuver.iconUrl) {
					html += '<img src="' + maneuver.iconUrl + '">  ';
				}

				for (k = 0; k < maneuver.signs.length; k++) {
					var sign = maneuver.signs[k];
					if (sign && sign.url) {
						//html += '<img src="' + sign.url + '">  ';
                                 if (sign.url.indexOf("httpss:") != 1){
							//sign.url.replace("httpss:" , "https:");
							 html += '<img src="' + sign.url.replace("httpss:" , "https:"); + '">  ';
							}else{
							html += '<img src="' + sign.url + '">  ';
							}
					}
				}

				if(j!=0 && j!=(legs[i].maneuvers.length-1)){
					html += '</td><td>' + maneuver.narrative + '<font style="color:grey;"> - ' + maneuver.distance + ' miles</font></td>';
				}else{
					html += '</td><td>' + maneuver.narrative + '</td>';
				}
				html += '</tr>';
			}
		}

		html += '</tbody></table>';
		$('#directions-results').html(html);
		/* P8423a - Sprint0 - Story9466  Changes Start */
		var distance = data.route.distance;
		var estimatedTime = data.route.formattedTime;
		
		// Limit the value to two decimal points
		distance = parseFloat(distance).toFixed(2);
		var estimatedTimeArray = []; 
		estimatedTimeArray = estimatedTime.split(':');
		var hours = estimatedTimeArray[0];
		var minutes = estimatedTimeArray[1];
		var seconds = estimatedTimeArray[2];
		$('#distMapValue').html(distance + ' miles');
		$('#timeMapValue').html(hours + " hours " + minutes + " minutes");
		$('#mapModalSpinner').hide();
		$('#directions-results').addClass('directionsResultsHeight');
		$('#directions-results').css("overflow","auto");
		$('#mapDialogBox').append('<br/>');
		$('#mapDialogBox').append($('#directions-results'));
		adjustMapModalHeight();
		$('#directions-results').focus();
		/* P8423a - Sprint0 - Story9466  Changes End */
	}
}

/*function closeDirections() {
	MQA.withModule('directions', function() {
		map.removeRoute()
		var itemNumber = $('#directions-item-number').html();
		if (itemNumber >= 0) {  // results page map
			$('#mapDirectionsOverall').hide('slow');
		} else { // details page map
			$('#mapDirections').hide('slow');
		}
	});
}*/

function closeResultsPageMap(){
	$('#mapPadding').hide('slow'); 
	$('#mapContainerOverall').hide('slow'); 
	$('#pretendMap').show('slow');
}

function pinClick(evt){  // called when a user clicks a map pin
	var url = $.trim(evt.srcObject.detailsPage);
	if(url != ""){	
		url = unescape(url);
		url = url.replace(/\&amp;/g,'&');
		window.location = url;
	}
}

/* P8423a Sprint13 - Story6032 Start */
function toggleFT(showHideDiv, switchImgTag, name){
	var ele = document.getElementById(showHideDiv);
    var imageEle = document.getElementById(switchImgTag);
    if(ele.style.display == "block") {
        $('#'+showHideDiv).toggle('slow');
        imageEle.innerHTML = '<div class="blockImageBorderDiv"><img class="blockImageBorder" src="/dse/assets/images/buttons_open2.gif"></div>'+'<span class="accordionText">'+name+'</span>';
    }else{
        $('#'+showHideDiv).toggle('slow');
        $('.ftDetail').css('padding','10px');
        imageEle.innerHTML = '<div class="blockImageBorderDiv"><img class="blockImageBorder" src="/dse/assets/images/buttons_close2.gif"></div>'+'<span class="accordionText">'+name+'</span>';
        ele.style.display = 'block';
	}
}

function toggleFTWithAlt(showHideDiv, switchImgTag, name, alt, alt2){
	var ele = document.getElementById(showHideDiv);
    var imageEle = document.getElementById(switchImgTag);
    if(ele.style.display == "block") {
        $('#'+showHideDiv).toggle('slow');
        imageEle.innerHTML = '<div class="blockImageBorderDiv"><img class="blockImageBorder" src="/dse/cms/codeAssets/images/accordion-open.png" alt="'+alt+'"></div>'+'<span class="accordionText">'+name+'</span>';
    }else{
        $('#'+showHideDiv).toggle('slow');
        $('.ftDetail').css('padding','10px');
        imageEle.innerHTML = '<div class="blockImageBorderDiv"><img class="blockImageBorder" src="/dse/cms/codeAssets/images/accordion-close.png" alt="'+alt2+'"></div>'+'<span class="accordionText">'+name+'</span>';
        ele.style.display = 'block';
	}
}
function toggleFTWithAltLeft(showHideDiv, switchImgTag, name, alt, alt2){
	var ele = document.getElementById(showHideDiv);
    var imageEle = document.getElementById(switchImgTag);
    if(ele.style.display == "block") {
        $('#'+showHideDiv).toggle('slow');
        imageEle.innerHTML = '<div class="blockImageBorderDiv"><img class="blockImageBorder" src="/dse/assets/images/buttons_open2.gif" alt="'+alt+'"></div>'+'<span class="accordionText">'+name+'</span>';
    }else{
        $('#'+showHideDiv).toggle('slow');
        $('.ftDetail').css('padding','10px');
        imageEle.innerHTML = '<div class="blockImageBorderDiv"><img class="blockImageBorder" src="/dse/assets/images/buttons_close2.gif" alt="'+alt2+'"></div>'+'<span class="accordionText">'+name+'</span>';
        ele.style.display = 'block';
	}
}

function openFacility(showHideDiv, switchImgTag){
	var ele = document.getElementById(showHideDiv);
    var imageEle = document.getElementById(switchImgTag);
    if(ele.style.display != "block") {
        $('#'+showHideDiv).show('slow');
        imageEle.innerHTML = '<img class="blockImageBorder" src="/dse/assets/images/buttons_close2.gif">';
    }
}

var CONTEXT_ROOT = "/dse/assets/html/";
function datacorrectionrd(){
	var domRegistration = document.domain;
	var domDemographics = "";
	if (domRegistration.substr(0,3)=="dev"){
		domDemographics = "devwww.aetna.com";
	}
	else if(domRegistration.substr(0,2)=="qa"){
		domDemographics = "qawww.aetna.com";
	}
	else if(domRegistration.substr(0,3)=="str"){
		domDemographics = "str2wwwr5.aetna.com";
	}
	else{
		domDemographics = "www.aetna.com";
	}
	
	var windowName='popup';
	var url=CONTEXT_ROOT + "data_correction.html";
	var winOpts = 'width=700,height=525,scrollbars=yes,resizable=yes,toolbar=yes';
	window.name='INDEX';
	aWindow=window.open(url,windowName,winOpts);
}
/* P8423a Sprint13 - Story6032 End */

/*P8423a Sprint13 - Story6565 Changes Start*/
function redirectToStaticPage(url){
      var currentPage = window.location.href;
      if(urlProtocol == urlProtocolSecure){
            var selectedMbr = $('.cmidx_select span').text();
            if(url.indexOf('?') != -1){
                  url = url + '&selectedMbr=' + selectedMbr + '&frmPage=fromFtSummary';
            }else{
                  url = url + '?selectedMbr=' + selectedMbr + '&frmPage=fromFtSummary';
            }
            $('#zipCode').val($('#memberZipCode').val());
      }

      if(currentPage.indexOf('markPage=clickedPagination')> 0){
    	  markPage('clickedPagination');
      }else if(currentPage.indexOf('markPage=clickedFilter')> 0){
    	  markPage('clickedFilter');
      }else if(currentPage.indexOf('search/detail')== -1){
    	  markPage('freeText');
      }
     
      if($('#medicareProdSessionIndCurr').val() != 'true' && $('#medicareProdSessionIndFut').val() != 'true'){
	      if($('#preSearchHeaders').is(':visible')){
	    	  url = url + '&searchResultsInd=yes'; 
	      }
      }
      
      if(ieVersion <= 8 && url.indexOf('redirect?link')> 0){
    	  if(currentPage.indexOf('search/redirect')> 0){
    		  url = url + '&showBackButton=no';
    	  }else if(currentPage.indexOf('search/detail')> 0){
    		  url = url + '&showBackButton=no';
    	  }    	  
      }

      window.location.href = url;
	if(ie6Check){
    	  window.event.returnValue=false;
    	  $('div#content').removeClass('fixForIE6');
      }
}

function help(){
	var url= CONTEXT_ROOT + 'docfind_additional_information.html';

	if(window.name == "popup"){
		location.href = url;
	}
	else{
		var windowName = "popup";
		var winOpts = 'width=600,height=525,scrollbars=yes,resizable=yes,toolbar=yes';
		
		aWindow = window.open(url, windowName, winOpts);
		aWindow.focus();
	}
}

var chkSecureModal = true;
function showModal(){
	if(chkSecureModal){
		buildSecureAlertBox();
		$('#planDialogBox').trigger('show');	
		chkSecureModal = false;
	}else{
		$('#planDialogBox').trigger('show');	
	}
	//508-Compliance
	setDSEDialogFocus('planSelection');
}

function buildSecureAlertBox(){
	$('#planDialogBox').attr('title_planSelection', '<span class="rddialogPlantitle">Select a Plan</span><br />');
	$('#planDialogBox').attr('subtitle_planSelection', '');
	$('#planDialogBox').attr('dialogText_planSelection', '');	
	
	$('#planDialogBox').doDialogDse({width: 300, modal:true, draggable:true, closeOnEscape:true},
			[{id:'btnCancel2',value:'CANCEL', "url":"javascript:goDSENavHome();"},
			 {id:'btnContinue2',value:'CONTINUE', "url":"javascript:selectedPlan();"}],'planSelection');

	$("#btnCancel2").click(function(){
		//Chrome issue for future/current plan view - n596307
		if(browserName != null && browserName == 'Chrome'){
			goDSENavHomeForChrome();
		}
		else{
			goDSENavHome();
		}
	  });
	
	$("#btnContinue2").click(function(){			 
		 selectedPlan();
	  });
	
	$(".continueGoldButton_rd").click(function(){
		//Chrome issue for future/current plan view - n596307
		if(browserName != null && browserName != 'Chrome'){
			selectedPlan();
		}
	});
	
	if ($('.dialog-close-button_planSelection').length > 0) {
		$('.dialog-close-button_planSelection').click(function() {
			//Chrome issue for future/current plan view - n596307
			if(browserName != null && browserName != 'Chrome'){
				goNavHome();
			}
		});
	}
}

//Chrome issue for future/current plan view - n596307
function goDSENavHomeForChrome() {
             	window.history.go(-1);
	return false;
}

function goNavHome(){
	history.back();
	if($('#planDialogBox').length > 0) {
		// $('#planDialogBox').css('display', 'none');
		}
	return false;
}

function goDSENavHome(){
      if(ieVersion == 10 && ieVersion != null){
		//$('#planDialogBox').trigger('hide');
           //$('#planDialogBox').hide();
             window.history.forward();
             window.history.go(-2);
            //return false;          
	}else{
      history.back();
      if($('#planDialogBox').length > 0) {
		// $('#planDialogBox').css('display', 'none');
		}
	return false;
	}
}

function selectedPlan(){	
	var  cplanStatus = document.getElementById("cplanStatus");
	var  fplanStatus = document.getElementById("fplanStatus");
	var selPlanValue="";
	var mediCareInd="";
	if(cplanStatus != null && fplanStatus != null){
		if(cplanStatus.checked ==  true){			
			selPlanValue = cplanStatus.value
			/* P20941a August 2014 - Coventry Integration Medicare Advantage High Value  Networks - Rohit : START */
			mediCareInd = $('#medicareProdSessionIndCurr').val();
			/* P20941a August 2014 - Coventry Integration Medicare Advantage High Value  Networks - Rohit : END */
		}	
		else if(fplanStatus.checked ==  true){
			selPlanValue = fplanStatus.value
			/* P20941a August 2014 - Coventry Integration Medicare Advantage High Value  Networks - Rohit : START */
			mediCareInd = $('#medicareProdSessionIndFut').val();
			/* P20941a August 2014 - Coventry Integration Medicare Advantage High Value  Networks - Rohit : END */
		}	
		
		if(selPlanValue != ""){
			/*P8423a Sprint18 - Story6904 Changes Start*/
			$('#planDialogBox').trigger('hide');
			showSpinner();
			/*P8423a Sprint18 - Story6904 Changes End*/
			/* Start changes for P21861a May15 release - N204183 */
			if(window.location.href.indexOf('site_id') < 0){
				/* P20941a August 2014 - Coventry Integration Medicare Advantage High Value  Networks - Rohit : START */
				if(mediCareInd == 'true'){
					addMedicareSiteIdtoURL(selPlanValue);
				}
				else{
					location.href = location.href+"&planStatusSelected="+selPlanValue;
				}
				/* P20941a August 2014 - Coventry Integration Medicare Advantage High Value  Networks - Rohit : END */
			}
			else{
				location.href = location.href+"&planStatusSelected="+selPlanValue;
			}
			/* Start changes for P21861a May15 release - N204183 */
		}
	}	
}
/*P8423a Sprint13 - Story6565 Changes End*/

/*P8423a Sprint14 - Story6396 Changes Start*/
function expandLinks(){
	$('.ftDetail').show('slow');
  	$('.ftDetail').css('padding','10px');
  	$('.blockImageBorderDiv').html('<img class="blockImageBorder" src="/dse/cms/codeAssets/images/accordion-close.png">');
}

function collapseLinks(){
	$('.ftDetail').hide('slow');  	
  	$('.blockImageBorderDiv').html('<img class="blockImageBorder" src="/dse/cms/codeAssets/images/accordion-open.png">');
}
/*P8423a Sprint14 - Story6396 Changes End*/

/*P8423a Sprint14 - Story6474 Changes Start*/
/*P8423a Sprint18 - Story7105 Changes Start*/
function openPrintPD(url){
	
	/* Stress url needs to be changed*/
	var docDomain = document.domain;
	domDemographics = "";
	if ( docDomain.substr(0,3)=="dev"){
		domDemographics = "devwww.aetna.com"
	}
	else if(docDomain.substr(0,2) =="qa"){
		domDemographics = "qa3www.aetna.com"
	}
	else if(docDomain.substr(0,3) =="str"){	
		domDemographics = "qawww.aetna.com"	
	}	
	else{
		domDemographics = "www.aetna.com"	
	}
	
	var urlForDirectory="http://"+domDemographics+url;
	var windowName='Print a Provider Directory';
	var winOpts = 'width=800,height=600,scrollbars=yes,resizable=yes,toolbar=yes,overflow=scroll,location=yes,left=10,top=10';
	window.name='INDEX';	
	aWindow=window.open(urlForDirectory,'',winOpts);
	aWindow.focus();
}
/*P8423a Sprint18 - Story7105 Changes End*/

function showSpecialities(type){
	var specId = '#input_' +type + '_div';
	var selectSpecId = '#select_' + type;
	$('#default_additional_div').empty();
	$('#default_additional_div').html($(specId).html());
	
	if(type != 'spec' && type != 'phys_bhp' && type != 'hospitals' 
			&& type != 'labs' && type != 'dpcp' && type != 'dspec' 
			&& type != 'bhp' && type != 'eap' && type != 'opp'
			&& type != 'pharmacy' && type != 'pcp' && type!='moreSpec' && type!='morePhys_Bhp'){
		$('#type_row').hide();
		$('#search_for_label').addClass('padding_bottom');
		$('#search_for_section').addClass('padding_bottom');
	}else{
		$('#search_for_label').removeClass('padding_bottom');
		$('#search_for_section').removeClass('padding_bottom');
		$('#type_row').show();
	}
	$('#default_additional_div select').css("width","280px");
}

function showPlans(type){
	$('#input_default_plans').empty();
	$('#geo_attr_div_pharmHear').hide();
	$('#geo_attr_div').show();
	$('#findGeo').show();
	$('#disState_row').show();
	$('#plan_row').show();
	
	var selectPlanId = '#select_' + type + '_plans';
	if(type == 'ntp' || type == 'eyewear' || type == 'flushot'){
		$('#input_default_plans').hide();
		$('#geo_attr_div').hide();
		$('#geo_attr_div_pharmHear').hide();
		$('#findGeo').hide();
		$('#disState_row').hide();
		$('#plan_row').hide();
	}else if(type == 'hearing'){
		$('#input_default_plans').html($('#input_hearing_plans').html());
		$('#input_default_plans').show();
		$('#geo_attr_div_pharmHear').show();
		$('#input_default_plans select').css("width","280px");
		$('#geo_attr_div').hide();
	}else if(type == 'pharmacy'){
		$('#input_default_plans').html($('#input_pharmacy_plans').html());
		$('#input_default_plans').show();
		$('#geo_attr_div_pharmHear').show();
		$('#geo_attr_div').hide();
	}else if(type == 'dpcp' || type == 'dspec'){
		$('#input_default_plans').html($('#input_dental_plans').html());
		$('#input_default_plans').show();
	}else if(type == 'eap'){
		$('#input_default_plans').html($('#input_eap_plans').html());
		$('#input_default_plans').show();
		$('#input_default_plans select').css("width","280px");
	}else if(type == 'ipacal'){
		$('#input_default_plans').html($('#input_ipacal_plans').html());
		$('#input_default_plans').show();
	}else{
		$('#input_default_plans').html($('#input_medical_plans').html());
		$('#input_default_plans').show();
	}
}

function limitSpecialties(select){
	var selected = 0;
	for(var i=0; i < select.options.length; i++){
		if(select.options[i].selected){
			selected++;
		}
		if(selected > 2){
			select.options[i].selected = false;
		}
	}
}

function checkForMoreSpec(spec){
	if(spec == 'moreSpec'){
		showSpecialities(spec);
	}
	if(spec == 'morePhys_Bhp'){
		showSpecialities(spec);
	}
}

function changeGeo(geoType){
	if(geoType == 'zip'){
		$('#text_city_div').hide();
		$('#text_state_div').hide();
		$('#input_city_div').hide();
		$('#input_state_div').hide();
		$('#text_county_div').hide();
		$('#input_county_div').hide();
		$('#text_zip_div').show();
		$('#text_distance_div').show();
		$('#input_zip_div').show();
		$('#input_distance_div').show();
	}else if(geoType == 'city'){
		$('#text_zip_div').hide();
		$('#text_county_div').hide();
		$('#text_distance_div').hide();
		$('#input_zip_div').hide();
		$('#input_county_div').hide();
		$('#input_distance_div').hide();
		$('#text_city_div').show();
		$('#text_state_div').show();
		$('#input_city_div').show();
		$('#input_state_div').show();
	}else if(geoType == 'county'){
		$('#text_zip_div').hide();
		$('#text_distance_div').hide();
		$('#input_zip_div').hide();
		$('#input_city_div').hide();
		$('#text_city_div').hide();
		$('#input_distance_div').hide();
		$('#input_county_div').show();
		$('#text_county_div').show();
		$('#text_state_div').show();
		$('#input_state_div').show();
	}
}

function checkforVitalidadPlans(planValue){
	$('#vitalidad_plan_add_section1').hide();
	$('#vitalidad_plan_add_section2').hide();
	$('#eap_plan_add_section').hide();
	if(planValue.indexOf('VPHMO')!=-1 || planValue.indexOf('Mexico')!=-1){
		$('#vitalidad_plan_add_section1').show();
		$('#vitalidad_plan_add_section2').show();
	}else if (planValue == 'EAP|Employee Assistance Program'){
		$('#eap_plan_add_section').show();
	}
}
/*P8423a Sprint14 - Story6474 Changes End*/

var chkBuild = true;
function showPlanListModal(){
	var urlProtocol = window.location.protocol;
	/*-- START CHANGES P20751b ACO Branding - n596307 --*/
	var planDiv;
	if($('#switchForForceHLSelection')!=null && $.trim($('#switchForForceHLSelection').text()) == 'ON' && trim($("#hl-autocomplete-search-location").val()) != '' 
		&& trim($("#geoMainTypeAheadLastQuickSelectedVal").val())!= null && trim($("#geoMainTypeAheadLastQuickSelectedVal").val()) != '' ){
		if(isHLDown){
			planDiv = getPlanListDiv(planTypeForPublic);
			isHLDown = false;
		}
		else{
			var hlValueToBePassed;
			if($("#QuickGeoType").val()=='state'){
				hlValueToBePassed = $('#stateCode').val();
			}
			else if($("#QuickGeoType").val()=='detectedValue'){
				if($('#QuickZipcode').val() != null && $('#QuickZipcode').val() != ''){
					hlValueToBePassed = $('#QuickZipcode').val();
				}
				else if($('#stateCode').val() != null && $('#stateCode').val() != ''){
					hlValueToBePassed = $('#stateCode').val();
				}
			}
			else{
				hlValueToBePassed = $('#QuickZipcode').val();
			}
			if(hlValueToBePassed != null && hlValueToBePassed != ''){
				planDiv = fetchPlanListAsPerGeoInput(hlValueToBePassed);
			}
			else{
				planDiv = getPlanListDiv(planTypeForPublic)
			}
		}
	}
	else{
		planDiv = getPlanListDiv(planTypeForPublic)
	}
	/*-- END CHANGES P20751b ACO Branding - n596307 --*/
	if(chkBuild){
		buildPlanListAlertBox(planDiv,planTypeForPublic);
		$('#modal_aetna_plans_prim').remove();
		$('#attachedDiv').remove();
		$('#planListDialogBox').trigger('show');
		$('#planListDialogBox').css('display','none');
		
		$('.dialog-transparent-border_planModal').css("background-color","#333333");
		$('.dialog-dialogText_planModal').css("padding","0px 20px 20px");
		$('.dialog-subtitle_planModal').css("padding","20px");
		$('.dialog-subtitle_planModal').css("margin","0px");
		$('.dialog-title_planModal').css("margin","0px");
		if(urlProtocol == urlProtocolSecure){
			$('.dialog-content-wrap_planModal').css("background-color","#e9ecbf");
			//$('.dialog-transparent-border_planModal').css('height','306px');
			autoAdjustTransparentBorder();
			$('.dialog-transparent-border_planModal').css('width','744px');
		}
		else{
			$('.dialog-content-wrap_planModal').css("background-color","#ffffff");
			//$('.dialog-content-wrap_planModal').css("border","5px solid #D1D1D1");
			//$('.dialog-transparent-border_planModal').css('height','317px');
			autoAdjustTransparentBorder();
			$('.dialog-transparent-border_planModal').css('width','752px');
		}
		chkBuild = false;
	}
	else{
		var planList = $(planDiv).html()
		$('#planListDialogBox').attr('dialogText_planModal', planList);
		
		var medSubTitle=$('#modalSubtitle').html();
		var dentakSubTitle=$('#modalDentalSubtitle').html();
		var subTitile = "";
		
		if($('#ChangeTextOnPlanModalForDental')!=null && $.trim($('#ChangeTextOnPlanModalForDental').text()) == 'ON'){
			if(planTypeForPublic == "dental_plans"){
				subTitile = dentakSubTitle;
			}else{
				subTitile = medSubTitle;
			}
			/* Start changes for P21861a May15 release - N204183 */
			if($('#site_id').val()!=null && $('#site_id').val()!=undefined && $('#site_id').val() == 'innovationhealth'){
				$('.dialog-subtitle_planModal').html("<div class='dialog-title_planModal' id='diaTitle_planModal' style='cursor: move; margin: 0px;'><span class='rddialogPlantitle'>Find health care professionals that accept your plan</span><br></div>");
			}else
				$('.dialog-subtitle_planModal').html("<div class='dialog-title_planModal' id='diaTitle_planModal' style='cursor: move; margin: 0px;'><span class='rddialogPlantitle'>First, choose an Aetna plan to find providers that accept it</span><br></div>");
			/* End changes for P21861a May15 release - N204183 */
			$('.dialog-subtitle_planModal').append(subTitile);
		}else{
			if($('#site_id').val()!=null && $('#site_id').val()!=undefined && $('#site_id').val() == 'innovationhealth'){
				$('.dialog-subtitle_planModal').html("<div class='dialog-title_planModal' id='diaTitle_planModal' style='cursor: move; margin: 0px;'><span class='rddialogPlantitle'>Find health care professionals that accept your plan</span><br></div>");
			}else
				$('.dialog-subtitle_planModal').html("<div class='dialog-title_planModal' id='diaTitle_planModal' style='cursor: move; margin: 0px;'><span class='rddialogPlantitle'>First, choose an Aetna plan to find providers that accept it</span><br></div>");
			/* End changes for P21861a May15 release - N204183 */
			$('.dialog-subtitle_planModal').append(medSubTitle);
		}
		
		$('.dialog-dialogText_planModal').html(planList);
		$('.dialog-main-wrapper_planModal').css("display","block");
		$('#dialog_modal_id_planModal').css("display","block");
		$('#planListDialogBox_planModal').trigger('show');
		$('#planListDialogBox_planModal').css('display','none');
		$('.dialog-transparent-border_planModal').css("background-color","#333333");
		
		$('.dialog-dialogText_planModal').css("padding","0px 20px 20px");
		$('.dialog-subtitle_planModal').css("padding","20px");
		$('.dialog-subtitle_planModal').css("margin","0px");
		$('.dialog-title_planModal').css("margin","0px");
		if(urlProtocol == urlProtocolSecure){
			$('.dialog-content-wrap_planModal').css("background-color","#e9ecbf");
			//$('.dialog-transparent-border_planModal').css('height','306px');
			autoAdjustTransparentBorder();
			$('.dialog-transparent-border_planModal').css('width','744px');
		}
		else{
			$('.dialog-content-wrap_planModal').css("background-color","#ffffff");
			//$('.dialog-content-wrap_planModal').css("border","5px solid #D1D1D1");
			//$('.dialog-transparent-border_planModal').css('height','317px');
			autoAdjustTransparentBorder();
			$('.dialog-transparent-border_planModal').css('width','752px');
		}
	}
	setDSEDialogFocus('planModal');
	return false;
}

/* content release 07302014 */
function autoAdjustTransparentBorder(){
	var planModalHeight = $('#planListDialogBox.dialog-content_planModal').parents('div.dialog-main-wrapper_planModal').children('div.dialog-content-wrap_planModal').height();
	$('#planListDialogBox.dialog-content_planModal').parents('div.dialog-main-wrapper_planModal').children('div.dialog-transparent-border_planModal').css("height",planModalHeight+40);
}


function objectAreEqual(p1, p2){
	return p1.id === p2.id;
}

function showNAPWarningBox(){
	$('#napWarningDialog').html($('#napWarningDialogContent').html());
	$('#napWarningDialog').trigger('show');
	$('#napWarningDialog.dialog-content').parents('div.dialog-main-wrapper').children('div.dialog-content-wrap').children('div.dialog-title').html('<b>National Advantage&trade; Program (NAP)</b>');
	renderModelButtonForNonSecure();
	var napHeight = $('#napWarningDialog.dialog-content').parents('div.dialog-main-wrapper').children('div.dialog-transparent-border').height();
	$('#napWarningDialog.dialog-content').parents('div.dialog-main-wrapper').children('div.dialog-transparent-border').css("height",napHeight + 2);
}

function buildPlanListAlertBox(planDiv,planTypeForPublic){
	var pselList=$(planDiv).html();
	var title=$('#modalTitle').html();
	var subTitle=$('#modalSubtitle').html();
	$('#planListDialogBox').attr('title_planModal', title);
	if($('#ChangeTextOnPlanModalForDental')!=null && $.trim($('#ChangeTextOnPlanModalForDental').text()) == 'ON')
	{
		var dentakSubTitle=$('#modalDentalSubtitle').html();
		if(planTypeForPublic == "dental_plans"){
			$('#planListDialogBox').attr('subtitle_planModal', dentakSubTitle);
		}else{
			$('#planListDialogBox').attr('subtitle_planModal', subTitle);
		}
	}else{
		$('#planListDialogBox').attr('subtitle_planModal', subTitle);
	}
	$('#planListDialogBox').attr('dialogText_planModal', pselList);
	
	$('#planListDialogBox').doDialogDse({width: 425, modal:true, draggable:true, closeOnEscape:false},
			[{id:'btnChoosePlan',value:'CHOOSE PLAN',url:"javascript:closeGenericModalBox()"}],'planModal');
	
	$(".choosePlanGoldButton").bind('click',function(){  		 
		 var planSelected = $('#modal_aetna_plans :selected').text();
		 var planVal = $('#modal_aetna_plans :selected').val();
		 if (planVal != null){
			 //508-Compliance
			 handlePlanRedirection(planVal);
			 /*--- START CHANGES P23695a Docfind Future View - n596307 ---*/
			 $('#productPlanPipeName').val(trimSpace(planVal));
			 /*--- END CHANGES P23695a Docfind Future View - n596307 ---*/
			 var pipe = planVal.indexOf('|');
			 if (pipe > -1){
				 planVal = trim(planVal.substring(0, pipe));
			 }
		 }
		 if(planSelected == "Select" || planVal == "DINDE"){
			 return false;
		 }
		 $('.dialog-main-wrapper_planModal').css("display","none");
		 $('#dialog_modal_id_planModal').css("display","none");
		 if(ieVersion == 8 && ieVersion != null){
			 $('#planListDialogBox').css("display","none");
		 }
		 if(planSelected != null){
			 searchWithPlan(planSelected,planVal);
			 $('#modalSelectedPlan').val(planVal);
			 if(planVal == 'NAPDS'){
				 showNAPWarningBox();
			 }else if(planVal == 'Mexico'){
				popUpResize('http://www.aetna.com/docfind/cms/html/mexico_medical_providers.html');
	  		 }
			 else{
				 $('#columnPlanSelected').css('display','block');
				 whyPressed = 'publicPlan';
				 markPage('publicPlanSelected');
				 searchSubmit('true');
				 $("#docfindSearchEngineForm").submit();
				 if((chk  || $('#searchQuery').val()) && (!($('#hl-autocomplete-search').val() == ghostTextWhatBox))){
					$(document).off('click','.hl-searchbar-button');
				 }
			 }			
		 }
		 
		 return false;
	  });
	
	$("#contWOPlan_ft").bind('click',function(){
		
		$('#modalSelectedPlan').val('');
            /*Story 10253 Start*/
		$('#linkwithoutplan').val('true');
		/*Story 10253 End*/
		$('.dialog-main-wrapper_planModal').css("display","none");
		$('#dialog_modal_id_planModal').css("display","none");
		if(ieVersion == 8 && ieVersion != null){
			$('#planListDialogBox').css("display","none");
		}
		/*-- START CHANGES SR1399 DEC'14 - n596307 --*/
		var planDisplayName = getCookie('planDisplayName');
		var externalPlanCode = getCookie('externalPlanCode');
		if(checkPlanPrefillFlow() || (planDisplayName != null && planDisplayName != '' && externalPlanCode != null && externalPlanCode != ''))
		{
			searchWithOutPlanPrefillFlow(noneText);
			eraseCookie('planDisplayName');
			eraseCookie('externalPlanCode');
		}
		else{
			searchWithOutPlan();
		}
		/*-- END CHANGES SR1399 DEC'14 - n596307 --*/
		searchSubmit('true');
		$("#docfindSearchEngineForm").submit();
		if((chk  || $('#searchQuery').val()) && (!($('#hl-autocomplete-search').val() == ghostTextWhatBox))){
			$(document).off('click','.hl-searchbar-button');
		}
		return false;
	});
	
	$('.dialog-close-button_planModal').bind('click',function(){
		planTypeForPublic = '';
		triggerSearchButtonEvent();
		$('#quickSearchTypeThrCol').val('');
		/*-----START CHANGES A9991-1034 A615A-1094 Nov 2013-----*/
		$('#ioeqSelectionInd').val('');
		$('#ioe_qType').val('');
		return false;
	});
	
	return false;
}

if(ieVersion != null){
	Array.prototype.indexOf = function(elt){
	  var len = this.length >>> 0;
	  var from = Number(arguments[1]) || 0;
	  from = (from < 0)
	       ? Math.ceil(from)
	       : Math.floor(from);
	  if (from < 0)
	    from += len;
	
	  for (; from < len; from++){
	    if (from in this &&
	        this[from] === elt)
	      return from;
	  }
	  return -1;
	};
}

function searchWithOutPlan(){
	$('#columnPlanSelected').css('display','none');
                   $('#plandisplay').hide();
}

/* Function to trim Spaces 
 * Used for trimming plan Name */
function trim(s){
	var l=0; 
	var r=s.length -1;
	while(l < s.length && s[l] == ' '){	
		l++; 
	}
	while(r > l && s[r] == ' '){	
		r-=1;
	}
	return s.substring(l, r+1);
}

function searchWithPlan(planSelected,planVal){
	/*-----START CHANGES P8551c QHP_IVL PCR - n204189-----*/
	/** Added new function trimSpaces and used the same. Existing function was not working in firefox **/
	var filteredPlan = escape(trimSpace(planSelected));
	$('#listPlanSelected').text(trimSpace(planSelected));
	$('#productPlanName').val(trimSpace(planSelected));
	/*-----END CHANGES P8551c QHP_IVL PCR - n204189-----*/
	$('#listPlanSelected').css('font-weight','bold');
	$('#listPlanSelectedPipeName').text(trim(planVal));
	
	$('#planChange').click(function(event){
		
		// chkBuild=false;
		$('#planCodeFromDetails').val('');
		$('#productPlanName').val('');
		/*-- START CHANGES SR1399 DEC'14 - n596307 --*/
		var planDisplayName = getCookie('planDisplayName');
		var externalPlanCode = getCookie('externalPlanCode');
		if(checkPlanPrefillFlow() || (planDisplayName != null && planDisplayName != '' && externalPlanCode != null && externalPlanCode != ''))
		{
			if(!($('#planFamilySwitch')!=null && $('#planFamilySwitch')!=undefined && $.trim($('#planFamilySwitch').text()) == 'ON')){
				if($("#modal_aetna_plans") != undefined){
					$('#modal_aetna_plans :selected').text('Select');
					$('#modal_aetna_plans :selected').val('');
				}
			}
		}
		/*-- END CHANGES SR1399 DEC'14 - n596307 --*/
		/*-- START CHANGES P20941a August2014 - Medicare Advantage - n596307 --*/
		if($('#switchForStatePlanSelectionPopUp')!=null && $('#switchForStatePlanSelectionPopUp')!=undefined 
	    		&& $.trim($('#switchForStatePlanSelectionPopUp').text()) == 'ON'){
				showStatePlanListModal();
	    }
		/*-- END CHANGES P20941a August2014 - Medicare Advantage - n596307 --*/
		//content 1008
    	else if($('#site_id').val()!=null && $('#site_id').val()!=undefined && $('#site_id').val() == 'universityofrochester'){
    		//don't show plan selection model box
    		searchWithDefaultPlan();
    	}
    	else if(directLinkSiteFound && planPrefillFlowSwitch != null && planPrefillFlowSwitch != 'true'){

        //don't show plan selection model box

        searchWithNoPlan();

}
		else{
			showPlanListModal();
		}
		
		return false;
	});
}
/*-----START CHANGES P8551c QHP_IVL PCR - n204189-----*/
function trimSpace(str) {
	if(str!=undefined){
		return str.replace(/^\s\s*/, '').replace(/\s\s*$/, '');
	}else{
		return "";
	}

}
/*-----END CHANGES P8551c QHP_IVL PCR - n204189-----*/

function closeGenericModalBox(){
	if(ieVersion == 8 && ieVersion != null){
		$('#planListDialogBox').trigger('hide');
	}
}

/* P8423a - Sprint 16 - Story 7396 Changes Start */
function goClick(){
	var selectedDropDownValue = $('.narrowSearchResultsSelect_select').val();
	var withinMileValue = $('#withinMilesValue').text();
	var distance = $('#distance').val();

/* Start changes for P19134a November release 2013 */
	var tab1SelectedSortOrderValue = $('.bestResultsSelect_select').val();
      if(tab1SelectedSortOrderValue && ieVersion == 8){
		tab1SelectedSortOrderValue = tab1SelectedSortOrderValue.replace("\"","");
	}
	if(tab1SelectedSortOrderValue != null && tab1SelectedSortOrderValue.length >0){
		$('#sortOrder').val(tab1SelectedSortOrderValue);
	}
	var tab2SelectedSortOrderValue = $('.otherResultsSelect_select').val();
      if(tab2SelectedSortOrderValue && ieVersion == 8){
		tab2SelectedSortOrderValue = tab2SelectedSortOrderValue.replace("\"","");
	}
	if(tab2SelectedSortOrderValue != null && tab2SelectedSortOrderValue.length >0){
		$('#sortOrder').val(tab2SelectedSortOrderValue);
	}
	/* End changes for P19134a November release 2013 */
	
	if(selectedDropDownValue && ieVersion == 8){
		selectedDropDownValue = selectedDropDownValue.replace("\"","");
	}
	//If user changes value in dropdown
	if(selectedDropDownValue != null && selectedDropDownValue.length > 0){
		$('#distance').val(selectedDropDownValue);
		$('#withinMilesVal').val($('#distance').val());
	}else if(distance != '0'){
		$('#distance').val(distance); //If user changes zip value in left section
		$('#withinMilesVal').val($('#distance').val());
	}else{
		$('#distance').val(withinMileValue);
	}
	/*P8423a Sprint17 - Story6190 Changes Start */
	if(checkValidZipCode()){
		if($('#distance').val() == '1'){
			$('#sendZipLimitInd').val('true');
		}
		else{
			$('#sendZipLimitInd').val('');
		}
		markPageFilterGeoSearch();
		//$('.hl-searchbar-button').click();
		searchSubmit('true');
		$("#docfindSearchEngineForm").submit();
	}else{
		$("#invalidZipMessage").show();
	}
	/*P8423a Sprint17 - Story6190 Changes End */
}

/* P8423a - Sprint 16 - Story 7396 Changes End */

function printAllSecure(){
	var calculateWidth = $('#left').width();
	if(urlProtocol == urlProtocolSecure){
		$('#aetnaLogo').css("width","198px");
		$('#header').css("background-color","#FFFFFF");
	}
	
	if(ieVersion >= 8 ){
		if(urlProtocol == urlProtocolSecure){
			var trimmedMbrName = trim($('.cmidx_select span').text());
			var valueSelected = trimmedMbrName;
			var valueSelected2 = $('.narrowSearchResultsSelect_select span').text();
			$('#runtimeDiv').remove();
			$('#runtimeInnerDiv').remove();
			$('#runtimeDiv2').remove();
			$('#runtimeInnerDiv2').remove();
			var dynamicDiv =  '<div id="runtimeDiv" style="width: 183px;" class = "printSelect" ><div id="runtimeInnerDiv"  style="width: 178px;">'+valueSelected+'</div></div>';
			var dynamicDiv2 =  '<div id="runtimeDiv2" style="width: 80px;" class = "printSelect2" ><div id="runtimeInnerDiv2"  style="width: 78px;">'+valueSelected2+'</div></div>';
			$(dynamicDiv).insertAfter($('#claimSearchSelect'));
			$(dynamicDiv2).insertAfter($('#narrowSearchResultsSelectDiv'));
			$('#header').css("background-color","#FFFFFF");
			$('#content').css("float","none");
			$('#resultsDisclaimer').css("float","none");
			$('#content').css("padding-left",calculateWidth + 15);
			$('#searchResults').css("background-color","#FFFFFF");
			$('body').css("background-color","#FFFFFF");
			$('#searchSection').css("border-color","#FFFFFF");
			$('#searchSection').css("border","none");
		}else{
			$('#resultsDisclaimer').css("float","none");
			var valueSelected2 = $('.narrowSearchResultsSelect_select span').text();
			$('#runtimeDiv2').remove();
			$('#runtimeInnerDiv2').remove();
			var dynamicDiv2 =  '<div id="runtimeDiv2" style="width: 80px;" class = "printSelect2" ><div id="runtimeInnerDiv2"  style="width: 78px;">'+valueSelected2+'</div></div>';
			$(dynamicDiv2).insertAfter($('#narrowSearchResultsSelectDiv'));
			$('#content').css("float","none");
			//$('#headerTitle').css("float","none");
			 $('#header').css("float","none");
                  $('#content').css("padding-left",calculateWidth + 15);
                  /*$('#askAnnId').css("width","145%");
                  $('#askAnnId').css("float","none");*/
		}
	}else{
            if(urlProtocol == urlProtocolNonSecure){
			$('#askAnnId').css("width","100%");
		}
		$('#resultsDisclaimer').css("float","none");
		$('#content').css("float","none");
		$('#content').css("padding-left",calculateWidth + 15);
	}
	window.print();
      if(ieVersion >= 8 ){
       $('#askAnnId').css("width","100%");
      }
	$('#runtimeDiv').remove();
	$('#runtimeInnerDiv').remove();
	$('#runtimeDiv2').remove();
	$('#runtimeInnerDiv2').remove();
	if(urlProtocol == urlProtocolNonSecure){
		//$('#headerTitle').css("float","left");
	}
}

function positionExternalProvider(){
	if(document.getElementById('externalProvider') != null){
		if(document.getElementById('providersTable') != null){
			$('#externalProvider').insertBefore($('#providersTable tbody'));
		}
		if(document.getElementById('providersTableSec') != null){
			$('#externalProvider').insertBefore($('#providersTableSec tbody tr:first'));
		}
	}
}

function renderCssForDetailsInIE8(){
		if(ieVersion >= 8 ){
			$('#content').addClass('contentDetail');
			$('#content').css("float","none");
			$('#content').css("margin-left","195px");
			$('head').append('<script>function copyright(){}</script>');
			$('#footer').insertAfter($('#content'));
			if(urlProtocol == urlProtocolSecure){
				$('#runtimeDiv').remove();
				$('#runtimeInnerDiv').remove();
				var trimmedMbrName = trim($('.cmidx_select span').text());
				var valueSelected = trimmedMbrName;
				$('#runtimeDiv').remove();
				$('#runtimeInnerDiv').remove();
				var dynamicDiv =  '<div id="runtimeDiv" style="width: 183px;" class = "printSelect" ><div id="runtimeInnerDiv"  style="width: 178px;">'+valueSelected+'</div></div>';
				$(dynamicDiv).insertAfter($('#claimSearchSelect'));
			}
			var beforeTopValueIE = $('#printAndEstimateTakeAction').css("top");
			var beforeLeftValueIE = $('#printAndEstimateTakeAction').css("left");
			
			if(urlProtocol == urlProtocolSecure){
				//$('#printAndEstimateTakeAction').css("top","385px");
				//$('#printAndEstimateTakeAction').css("left","781px");
				//$('#printAndEstimateTakeAction').css("padding-top","1px");
				//$('#printAndEstimateTakeAction').css("padding-left","1px");
				//$('#printAndEstimateTakeAction').css("float","none");
				//$('#printAndEstimateTakeAction').css("position","fixed");
			}
			else{
				$('.mapImageSection').addClass('spacingForPublic'); 
				$('#printAndEstimateTakeAction').addClass('spacingForPublic');
				$('#printAndEstimateTakeAction').css("top","260px");
				//$('#printAndEstimateTakeAction').css("left","796px");
			}
			
			window.print();
			$('#printAndEstimateTakeAction').css("top",beforeTopValueIE);
			$('#printAndEstimateTakeAction').css("left",beforeLeftValueIE);
		}else{
			$('#content').addClass('zoomForFF');
			$('#content').css("display","inline-block");
			$('#content').css("float","right");
			$('#content').css("margin-right","170px");
			$('#content').css("padding-left","3px");
			$('#printAndEstimateTakeAction').css("float","right");
			$('#printAndEstimateTakeAction').css("position","absolute");
			
			var beforeTopValue = $('#printAndEstimateTakeAction').css("top");
			var beforeLeftValue = $('#printAndEstimateTakeAction').css("left");
			
			/* if(urlProtocol == urlProtocolSecure){
				$('#printAndEstimateTakeAction').css("top","385px");
			}
			else{
				$('#printAndEstimateTakeAction').css("top","260px");
			} */
			//$('#printAndEstimateTakeAction').css("left","781px");
			window.print();
			$('#printAndEstimateTakeAction').css("top",beforeTopValue);
			$('#printAndEstimateTakeAction').css("left",beforeLeftValue);
		}
}

function didYouMeanSuggest(suggestion){
	document.getElementById('searchQuery').value = suggestion;
	document.getElementById('hl-autocomplete-search').value = suggestion;
        /*Start story 10255 changes*/
	$('#newLocDidyouMean').html('');
	$('#newLocDidyouMean').hide();
      $('#didyou').hide();
	/*End story 10255*/
	whyPressed = 'didYouMean';
	$('.hl-searchbar-button').click();
}

function scrollPositionForTakeActionBox(){
	if(ieVersion >7 || ieVersion == null){
		var screenWidth = screen.width;
		var footerPos = 100;
		var urlProtocolTakeBox = window.location.protocol;
		window.onscroll = function(){
			var diffXPos;
			if(ieVersion != null && ieVersion >=7){
				diffXPosition = $(window).width();
			} 
			else{
				diffXPosition = window.innerWidth;
			}
			var koi = (diffXPosition/2);
			var IEversion = IEVersionCheck();
			var konn;
			var onloadPos;
			if(IEversion == 8 && IEversion != null){
				konn = koi + 303;
			}
			else{
				konn = koi + 296;
			}
			onloadPos = konn -5;
			var scrollHeight = window.pageYOffset || document.body.scrollTop || document.documentElement.scrollTop;
			
			if(scrollHeight > 300){
				if(document.getElementById('printAndEstimateTakeAction')!=null){
					document.getElementById('printAndEstimateTakeAction').style.position = 'fixed';
					/*document.getElementById('printAndEstimateTakeAction').style.display = 'block';*/
					document.getElementById('printAndEstimateTakeAction').style.left = konn + 'px';
					document.getElementById('printAndEstimateTakeAction').style.top = '-20px';
					if(window.scrollY+footerPos >= window.scrollMaxY) {
						document.getElementById('printAndEstimateTakeAction').style.position = 'fixed';
						document.getElementById('printAndEstimateTakeAction').style.left = konn + 'px';
						document.getElementById('printAndEstimateTakeAction').style.top = '-20px';
					}
				}
			} 
			else{
				if(document.getElementById('printAndEstimateTakeAction')!=null){
					document.getElementById('printAndEstimateTakeAction').style.position = 'absolute';
					if(urlProtocolTakeBox == urlProtocolSecure){
						if(ieVersion == 8){
							//document.getElementById('printAndEstimateTakeAction').style.position = 'fixed';
							document.getElementById('printAndEstimateTakeAction').style.top = '335px';
						}else{
							document.getElementById('printAndEstimateTakeAction').style.top = '335px';
						}
					}
					else{
						document.getElementById('printAndEstimateTakeAction').style.top = '260px';
					}
					document.getElementById('printAndEstimateTakeAction').style.left = onloadPos + 'px';
				}
			}
		};
	}
}

function updateHiddenVarForQuickSearch(obj){
	var quickSearchId = $(obj).parents('td:eq(1)').attr('id');
	if(quickSearchId == 'byCond'){
		$('#quickSearchTypeThrCol').val('byCond');
	}else if(quickSearchId == 'byProc'){
		$('#quickSearchTypeThrCol').val('byProc');
	}else if(quickSearchId == 'byProvType'){
		$('#quickSearchTypeThrCol').val('byProvType');
	}
}

/* P08-8423a Sprint3 - Story9837 Changes Start */
/* P23695a Blue Link changes - Start - N204189 */
function showLocationDialogBox(searchTerm , displayTerm ){
		
		if( displayTerm == undefined )
		{
			displayTerm = searchTerm;
		}
		
	/* P23695a Blue Link changes - End */
	
	$('#locationDialogBox.dialog-content').parents('div.dialog-main-wrapper').children('div.dialog-content-wrap').children('div.dialog-title').text(tellUsYourLocation).css({ 'font-weight': 'bold', 'color': '#7d3f98', 'font-size': '18pt' });;
	var $title=$('#locationDialogBox.dialog-content').parents('div.dialog-main-wrapper').children('div.dialog-content-wrap').children('div.dialog-title');
	
	$('#locationDialogBox').html('<table id=locationTable><tr><td id="">' +
			'<tr><td><br/>'+zipCityState+'</td></tr><tr><td id="locationTypeAheadBox">' + $('#includeTALocScript').html() + '<div class="hl-location-textBox"></div></td></tr></table>');
	
	$('#cancelWHLocCriteria').click(function(){
		$('#locationDialogBox').trigger('hide');
		/* start changes for MS SR 1438 Aug 2015*/
		$('#suppressFASTDocCall').val(false);
		/* end changes for MS SR 1438 Aug 2015*/
		$('#ioe_qType').val('');
		return false;
	});
	
	$('#searchWHLocCriteria').bind('click',function(event){
		/*Start changes for type ahead location*/
		/* P20488 - 1231 changes start */
		if(trim($('#hl-location-autocomplete-search').val()) == "" || trim($('#hl-location-autocomplete-search').val()) == ghostTextWhereBox){
			$('#locationDialogBox').trigger('hide');
			displayErrorLocationPopup();
		} /* P20488 - 1231 changes end */
		else if((trim($('#hl-autocomplete-search-location').val())) != (trim($('#hl-location-autocomplete-search').val()))){
			if((trim($('#hl-autocomplete-search-location').val())) != (trim($('#hl-location-autocomplete-search').val()))){
                        /* P23695a Blue Link changes  - Start*/
						$('#hl-autocomplete-search').val(displayTerm);
                        $('#actualSearchTerm').val(searchTerm);
                        $('#actualDisplayTerm').val(displayTerm);
                        /* P23695a Blue Link changes - End */
                        $('#thrdColSelectedVal').val(searchTerm);
				changeFormatGeoLocation();
				$('#hl-autocomplete-search-location').val($('#hl-location-autocomplete-search').val());
			}
			$('.hl-searchbar-button').click();
			$('#locationDialogBox').trigger('hide');
		}
		/*End changes for type ahead locations*/   
		 else{
			 /* P23695a Blue Link changes - Start - N204189 */
			$('#hl-autocomplete-search').val(displayTerm);
			$('#actualSearchTerm').val(searchTerm);
			$('#actualDisplayTerm').val(displayTerm);
			/* P23695a Blue Link changes - End*/
			$('#thrdColSelectedVal').val(searchTerm);
			$('.hl-searchbar-button').click();
			$('#locationDialogBox').trigger('hide');
		}
		return false;
	});
	
	renderFilterUIForNonSecure();
	$('#locationDialogBox').trigger('show');
      $('.dialog-modal').width($(document).width());
      $('.dialog-modal').height($(document).height() + 50);
	$('a#searchWHLocCriteria').children('table').children('tbody').children('tr').children('td.gold_button').css("position","relative");
	$('a#cancelWHLocCriteria').children('table').children('tbody').children('tr').children('td.gold_button').css("position","relative");
	var transHeight = $('#locationDialogBox.dialog-content').parents('div.dialog-main-wrapper').children('div.dialog-content-wrap').height();
	$('#locationDialogBox.dialog-content').parents('div.dialog-main-wrapper').children('div.dialog-transparent-border').css("height",transHeight+32);
	locationDialogBoxFormed = true;
}
/* P08-8423a Sprint3 - Story9837 Changes End */

/*P8423a Sprint17 - Story4558 Changes Start*/
/* Condition changes for story 7307 in the function */
/* P23695a Blue Link changes - Start - N204189  */
function quickSearch(searchTerm,obj , displayTerm )
{
	if( displayTerm == undefined )
	{
		displayTerm = searchTerm;
	}
	
/* P23695a Blue Link changes - End */
	if(searchTerm!=null &&  searchTerm=='Primary Care Dentists (PCD)'){
		$('#classificationLimit').val('DDP');
		$('#pcpSearchIndicator').val('true');
	}
	
	//content 0420
	if(searchTerm!=null && searchTerm=='Pediatrics'){
		$('#classificationLimit').val('DMP');
		$('#pcpSearchIndicator').val('true');
	}

	var idAttr = $(obj).attr('id');
	if(idAttr!='doFASTDocCall' && (idAttr=='undefined' || idAttr=='' || idAttr==null || idAttr==undefined)){
		$('#suppressFASTDocCall').val('true');
	}
	updateHiddenVarForQuickSearch(obj);
	changeFormat();
	planTypeForPublic = '';
	computeModelPlanType(searchTerm);
	if(urlProtocol == urlProtocolNonSecure){
		var location = trim($('#hl-autocomplete-search-location').val());
		if(location == undefined || location == ghostTextWhereBox || location == 'Código postal o ciudad, estado' || location ==''){
		
			/* P23695a Blue Link changes - Start - N204189  */
			showLocationDialogBox(trim(searchTerm) , trim(displayTerm));
			/* P23695a Blue Link changes - End */
		}
		else{
			$('#geoSearch').val(location);
			/* P23695a Blue Link changes - Start - N204189  */
			$('#hl-autocomplete-search').val(trim(displayTerm));
			$('#actualSearchTerm').val(searchTerm);
			$('#actualDisplayTerm').val(displayTerm);
			/* P23695a Blue Link changes - End */ 
			$('#thrdColSelectedVal').val(trim(searchTerm));
			$('.hl-searchbar-button').click();
			$('#locationDialogBox').trigger('hide');
		}		
	}else{
		/* P23695a Blue Link changes - Start - N204189 */
		$('#hl-autocomplete-search').val(displayTerm);
		$('#actualSearchTerm').val(searchTerm);
		$('#actualDisplayTerm').val(displayTerm);
		/* P23695a Blue Link changes - End */
		$('#thrdColSelectedVal').val(searchTerm);
		$('.hl-searchbar-button').click();
	}
	//$('#hl-autocomplete-search').val(searchTerm);
	//$('#thrdColSelectedVal').val(searchTerm);
	//$('.hl-searchbar-button').click();
}

function quickSearchWOSpecLimit(searchTerm,obj){
	var idAttr = $(obj).attr('id');
	if(idAttr!='doFASTDocCall' && (idAttr=='undefined' || idAttr=='' || idAttr==null || idAttr==undefined)){
		$('#suppressFASTDocCall').val('true');
	}
	changeFormat();
	planTypeForPublic = '';
	$('#showNoPlans').text('true');
	if(urlProtocol == urlProtocolNonSecure){
		var location = trim($('#hl-autocomplete-search-location').val());
		if(location == undefined || location == ghostTextWhereBox || location == 'Código postal o ciudad, estado' || location ==''){
			showLocationDialogBox(trim(searchTerm));
		}
		else{
			$('#geoSearch').val(location);
			$('#hl-autocomplete-search').val(trim(searchTerm));
			$('#thrdColSelectedVal').val(trim(searchTerm));
			$('.hl-searchbar-button').click();
			$('#locationDialogBox').trigger('hide');
		}
	}else{
		$('#hl-autocomplete-search').val(searchTerm);
		$('#thrdColSelectedVal').val(searchTerm);
		$('.hl-searchbar-button').click();
	}
}

function quickSearchWOFASTCall(searchTerm,obj, displayTerm){
	/* P23695a Blue Link changes - Start - N204189 */
	if( displayTerm == undefined )
	{
		displayTerm = searchTerm;
	}
	/*P23695a Blue Link changes - End - N204189 */
	updateHiddenVarForQuickSearch(obj);
	changeFormat();
	planTypeForPublic = '';
	$('#showNoPlans').text('true');
	$('#suppressFASTCall').val('true');	
	/* P23695a Blue Link changes - Start - N204189 */
	$('#actualSearchTerm').val(searchTerm);
	$('#actualDisplayTerm').val(displayTerm);
	$('#hl-autocomplete-search').val(displayTerm);
	/*P23695a Blue Link changes - Start - N204189 */
	$('#thrdColSelectedVal').val(searchTerm);
	$('.hl-searchbar-button').click();
	
}

function quickSearchVision(searchTerm,obj, displayTerm){
	/* P23695a Blue Link changes - Start - N204189 */
	if( displayTerm == undefined )
	{
		displayTerm = searchTerm;
	}
	/*P23695a Blue Link changes - End - N204189 */
	updateHiddenVarForQuickSearch(obj);
	changeFormat();
	planTypeForPublic = '';
	$('#showNoPlans').text('true');
	$('#suppressFASTCall').val('true');
	$('#suppressHLCall').val('true');
	/* P23695a Blue Link changes - Start - N204189 */
	$('#actualSearchTerm').val(searchTerm);
	$('#actualDisplayTerm').val(displayTerm);
	$('#hl-autocomplete-search').val(displayTerm);
	/*P23695a Blue Link changes - Start - N204189 */
	$('#thrdColSelectedVal').val(searchTerm);
	$('.hl-searchbar-button').click();
}


/* P8423a Sprint2 - Story9809 Changes Start */
function quickSearchWOPlans(searchTerm,obj , displayTerm){
	//content change - 0420
	if(searchTerm != null){
		redirectLogic(trimSpace(searchTerm));
	}
	/* P23695a Blue Link changes - Start - N204189 */
	if( displayTerm == undefined )
	{
		displayTerm = searchTerm;
	}
	/*P23695a Blue Link changes - End - N204189 */
	updateHiddenVarForQuickSearch(obj);
	changeFormat();
	planTypeForPublic = '';
	$('#showNoPlans').text('true');
	$('#suppressFASTCall').val('true');
	
	/* P23695a Blue Link changes - Start - N204189 */
	$('#actualSearchTerm').val(searchTerm);
	$('#actualDisplayTerm').val(displayTerm);
	$('#hl-autocomplete-search').val(displayTerm);
	/*P23695a Blue Link changes - Start - N204189 */
	
	$('#thrdColSelectedVal').val(searchTerm);
	$('.hl-searchbar-button').click();
	
}
/* P8423a Sprint2 - Story9809 Changes End */


var isQuickSearchClicked = true;

/* Condition changes for story 7307 in the function */
function changeFormat(){
	var text = $('#hl-autocomplete-search').val();
      $('#warning_msg').hide();
	//alert(text);
	//if($('.hl-searchbar-input').css("color") == '#BCBEC0'){
          if(text == ghostTextWhatBox){
		$('#hl-autocomplete-search').val("");
		$('.hl-autocomplete .hl-search-box .hl-searchbar .hl-searchbar-input').css('color','#000000');
		$('.hl-autocomplete .hl-search-box .hl-searchbar .hl-searchbar-input').css('font-style','normal');
	}
}

function changeFormatGeoLocation(){
     var text = $('#hl-autocomplete-search-location').val();
	//alert(text);
	//if($('.hl-searchbar-input-location').css("color") == 'rgb(188, 190, 192)'){
    if(text == ghostTextWhereBox || text == 'Código postal o ciudad, estado'){
		$('#hl-autocomplete-search-location').val("");
		$('.hl-autocomplete-location-textBox .hl-autocomplete-location-box .hl-autocomplete-locationbar .hl-searchbar-input-location').css('color','#000000');
		$('.hl-autocomplete-location-textBox .hl-autocomplete-location-box .hl-autocomplete-locationbar .hl-searchbar-input-location').css('font-style','normal');
	}
}

/*-- START CHANGES P20751b ACO Branding - n596307 --*/
function changeFormatPopUpNoLocation(){
     var text = $('#hl-no-location-autocomplete-search').val();
	//alert(text);
	if(text == ghostTextWhereBox || text == 'Código postal o ciudad, estado'){
		$('#hl-no-location-autocomplete-search').val("");
		$('.hl-no-location-textBox .hl-no-location-box .hl-no-locationbar .hl-no-location-searchbar-input').css('color','#000000');
		$('.hl-no-location-textBox .hl-no-location-box .hl-no-locationbar .hl-no-location-searchbar-input').css('font-style','normal');
	}
}
/*-- END CHANGES P20751b ACO Branding - n596307 --*/

function changeFormatPopUpLocation(){
     var text = $('#hl-location-autocomplete-search').val();
	//alert(text);
	if(text == ghostTextWhereBox || text == 'Código postal o ciudad, estado'){
		$('#hl-location-autocomplete-search').val("");
		$('.hl-location-textBox .hl-location-box .hl-locationbar .hl-location-searchbar-input').css('color','#000000');
		$('.hl-location-textBox .hl-location-box .hl-locationbar .hl-location-searchbar-input').css('font-style','normal');
	}
}

function quickSearchModal(searchTerm,obj){
	var selectedPlanVal = $('#modal_aetna_plans :selected').val();
	var stateCode = $('#stateDD').val();
	if(searchTerm == 'PROV_MHF' || searchTerm == 'PROV_SAF' || searchTerm == 'PROV_RTF'){
		if(stateCode == "FL" && (selectedPlanVal == "MEHMO|Aetna Medicare(SM) Plan (HMO)" || selectedPlanVal == "MEHMO|Aetna Medicare Connect Plus (HMO)" 
			|| selectedPlanVal == "MEHMO|Aetna Medicare Value Plan (HMO)" || selectedPlanVal =="MEHMO|Aetna Medicare Premier Plan (HMO)")){
			location.href = "javascript:popUp('/dse/search/disclaimer?continueUrl=http://providersearch.mhnet.com/Members/CoventryHealthCareProviderSearch/tabid/397/Default.aspx')";
			return;		
		}
	}
	
	updateHiddenVarForQuickSearch(obj);
		
	if(searchTerm=='PROV_MEDSPEC'){
		$('#specSearchIndicator').val('true');
		$('#classificationLimit').val('DMS');
		$('#axcelSpecialtyAddCatTierTrueInd').val('true');
	}
	
	if(searchTerm=='PROV_DENSPEC'){
		$('#specSearchIndicator').val('true');
		$('#classificationLimit').val('DDS');
	}
	/*Start changes for P23046-GDS Dental - n709197*/	
	var queryParameters = "site_id="+site_id+"&langPref="+langPref+"&contentId=" + searchTerm;
	/*END changes for P23046-GDS Dental - n709197*/
	planTypeForPublic = '';
	/*if(searchTerm == 'PROV_MHF' || searchTerm == 'PROV_SAF' || searchTerm == 'PROV_RTF')
      {
        $('#quickSearchTerm').val(searchTerm);
      }*/
	/*-----START CHANGES A9991-1034 A615A-1094 Nov 2013-----*/
	if(searchTerm=='PROV_IOE'||searchTerm=='PROV_IOQ'){
		$('#ioeqSelectionInd').val('true');
	}
	computeModelPlanType(searchTerm);
	$('#preSearchModalContent').load('search/preSearchContentAjax?' + queryParameters, function(response, status){
		if(isQuickSearchClicked){
				changeFormat();
				buildPreSearchListBox(response);
				$('#preSearchDialogBox').css("display","none");
				if(urlProtocol == urlProtocolNonSecure){
					$('.dialog-content-wrap_preSearchDialogBox').css("background-color","#ffffff");
					//$('.dialog-content-wrap_preSearchDialogBox').css("border","5px solid #D1D1D1");
				}
				isQuickSearchClicked = false;
			}else{
				$('#preSearchModalContentTable').html('<tr><td>'+response+'</td></tr>');
				$('#preSearchDialogBox').trigger('show');
				$('#preSearchDialogBox').css("display","none");
				if(urlProtocol == urlProtocolNonSecure){
					$('.dialog-content-wrap_preSearchDialogBox').css("background-color","#ffffff");
					//$('.dialog-content-wrap_preSearchDialogBox').css("border","5px solid #D1D1D1");
				}
			}
         /* IE 10 fix for select dialog box*/
		renderQuickSearchModal();
		/* IE 10 fix for select dialog box*/
	});
//var popuptab = new AetnaCom_popuptab();
}

function buildPreSearchListBox(response){
	/*-- START CHANGES P23695 Medicare Spanish Translation - n709197 --%>*/
	var preSearchModal = $('#preSearchModalDiv').html();
	$('#preSearchDialogBox').attr('title_preSearchDialogBox', '<span class="rddialogPlantitle">'+preSearchModal+'</span><br />');
	$('#preSearchDialogBox').attr('subtitle_preSearchDialogBox', '<br/><table id="preSearchModalContentTable" width=100%><tr><td>'+response+'</td></tr></table>');
	$('#preSearchDialogBox').attr('dialogText_preSearchDialogBox', '');
	
	var buttonCancelPreSearch = $('#buttonCancelPreSearchDiv').html();
	var buttonChoosePreSearch = $('#buttonChoosePreSearchDiv').html();
	if(urlProtocol == urlProtocolSecure){
		$('#preSearchDialogBox').doDialogDse({width: 400, modal:true, draggable:true, closeOnEscape:true},
				[{id:'btnCancelPreSearchSec',value:buttonCancelPreSearch, "url":"javascript:closeModalBoxWithId('#preSearchDialogBox');"},
				 {id:'btnChoosePreSearchSec',value:buttonChoosePreSearch,url:"javascript:triggerSearch('#preSearchDialogBox');"}],'preSearchDialogBox');
	}else{
		$('#preSearchDialogBox').doDialogDse({width: 400, modal:true, draggable:true, closeOnEscape:true},
				[{id:'btnCancelPreSearch',value:buttonCancelPreSearch, "url":"javascript:closeModalBoxWithId('#preSearchDialogBox');"},
				{id:'btnChoosePreSearch',value:buttonChoosePreSearch,url:"javascript:triggerSearch('#preSearchDialogBox');"}],'preSearchDialogBox');
	}
	/*-- END CHANGES P23695 Medicare Spanish Translation - n709197 --%>*/
	$('#btnCancelPreSearch').click(function(){
		$('#preSearchDialogBox').trigger('hide');
		$('#quickSearchTypeThrCol').val('');
           /* start changes for MS SR 1438 Aug 2015*/
		$('#suppressFASTDocCall').val(false);
           /* end changes for MS SR 1438 Aug 2015*/
		/*-----START CHANGES A9991-1034 A615A-1094 Nov 2013-----*/
		$('#ioeqSelectionInd').val('');
		planTypeForPublic = '';
		return false;
	});
	
	$('#btnCancelPreSearchSec').click(function(){
		$('#preSearchDialogBox').trigger('hide');
		$('#quickSearchTypeThrCol').val('');
		/* start changes for MS SR 1438 Aug 2015*/
		$('#suppressFASTDocCall').val(false);
           /* end changes for MS SR 1438 Aug 2015*/

		/*-----START CHANGES A9991-1034 A615A-1094 Nov 2013-----*/
		$('#ioeqSelectionInd').val('');
		$('#ioe_qType').val('');
		planTypeForPublic = '';
		return false;
	});

	$('#btnChoosePreSearch').click(function(){
		triggerSearch('#preSearchDialogBox');
		return false;
	});
	
	$('#btnChoosePreSearchSec').click(function(){
		triggerSearch('#preSearchDialogBox');
		return false;
	});
	
	$('.dialog-close-button_preSearchDialogBox').hide();
	
	/*if(urlProtocol == 'https:'){
		renderQuickSearchModal();
	}*/
	
	$('#preSearchDialogBox').trigger('show');	
}

/*function renderQuickSearchModal(){
	if(ieVersion == null){
		var heightFF = $('.dialog-transparent-border_preSearchDialogBox').css("height") - 3;
		$('.dialog-transparent-border_preSearchDialogBox').css("height",heightFF);
	}else{
		var heightIE8 = $('.dialog-transparent-border_preSearchDialogBox').css("height") - 177;
		$('.dialog-transparent-border_preSearchDialogBox').css("height",heightIE8);
	}		
}*/

/* IE 10 fix for select dialog box*/
function renderQuickSearchModal(){	
	if(ieVersion == 10){		
		var ddquickSearchSelection = document.getElementById('quickSearchSelection');
		var quickSearchMultipleSelection = document.getElementById('quickSearchMultipleSelection');
		//var increaseHieght = true;
		if (ddquickSearchSelection != null && ddquickSearchSelection.options.length > 4 ){			
			var heightIE10 = $('.dialog-transparent-border_preSearchDialogBox').height() + 50;
			$('.dialog-transparent-border_preSearchDialogBox').css("height", heightIE10+"px");
			$('.quickSearch_dropdown').css("height","100px");
		}
		
		if (quickSearchMultipleSelection != null && quickSearchMultipleSelection.options.length >4){
            var heightIE10 = $('.dialog-transparent-border_preSearchDialogBox').height() + 50;
			$('.dialog-transparent-border_preSearchDialogBox').css("height",heightIE10+"px");
			$('.quickSearchMultiple_dropdown').css("height","100px");
		}
		
	}
}
/* IE 10 fix for select dialog box*/

function triggerSearch(id){
	/* P08-8423a Sprint22 - Story6841 Changes Start */
	var noOfSpec = $('#quickSearchMultipleSelection').find(':selected').length;
	if($('#quickSearchSelection').find(':selected').length < 1){
		if(noOfSpec >0){
			var mulSpec = '';
			$('.dialog-main-wrapper_preSearchDialogBox').css('display','none');
			$('#dialog_modal_id_preSearchDialogBox').css('display','none');
			
			/* P08-8423a Sprint22 - Story9241 Changes Start */
			var mulSpecArray = Array();
			$('#quickSearchMultipleSelection').find(':selected').each(function(count){
				mulSpecArray[count] = trim($(this).val());
				var idAttr = $(this).attr('id');
				if(idAttr!='doFASTDocCall' && (idAttr=='undefined' || idAttr=='' || idAttr==null || idAttr==undefined)){
					$('#suppressFASTDocCall').val('true');
				}
			});
			if(noOfSpec >1){
				$('#isMultiSpecSelected').val(mulSpecArray);
			}
			$('#hl-autocomplete-search').attr('value',mulSpecArray);
			$('#thrdColSelectedVal').val(mulSpecArray);
			triggerSearchButtonEvent();
			if(urlProtocol == urlProtocolNonSecure){
				var location = trim($('#hl-autocomplete-search-location').val());
				if(location == undefined || location == ghostTextWhereBox || location == 'Código postal o ciudad, estado' || location ==''){
					showLocationDialogBox(mulSpecArray);
				}
				else{
					$('#geoSearch').val(location);
					$('#hl-autocomplete-search').val(mulSpecArray);
					$('#thrdColSelectedVal').val(mulSpecArray);
					$('.hl-searchbar-button').click();
					$('#locationDialogBox').trigger('hide');
				}
			}else{
				$('.hl-searchbar-button').click();
			}
			if(noOfSpec >1){
				$('#hl-autocomplete-search').attr('value','');
				$('#thrdColSelectedVal').val('');
			}
			/* P08-8423a Sprint22 - Story6841 Changes End */
		}
	}else{
		var ioeSelected = trim($('#quickSearchSelection').find(':selected').val());
		$('.dialog-main-wrapper_preSearchDialogBox').css('display','none');
		$('#dialog_modal_id_preSearchDialogBox').css('display','none');
		if(ioeSelected == 'Pediatric Congenital Heart Surgery' || ioeSelected == 'Transplant'){
			quickSearchWOPlans(ioeSelected, this);
		}
		else{
		var idAttr = $('#quickSearchSelection :selected').attr('id');
		if(idAttr!='doFASTDocCall' && (idAttr=='undefined' || idAttr=='' || idAttr==null || idAttr==undefined)){
			$('#suppressFASTDocCall').val('true');
		}

		if(ioeSelected!='' && ioeSelected !=null && ioeSelected =='Routine Eye Exam'){
			quickSearchVision('Routine Eye Exam',$('#quickSearchSelection').find(':selected'));
		} else{

		/*Start changes for Story 9704*/
		var valueSelectedWithPipe = trim($('#quickSearchSelection :selected').val());
		var valueSelected = valueSelectedWithPipe;
		if(valueSelectedWithPipe.indexOf("|") != -1){
			var divisionNamesArray =  valueSelectedWithPipe.split("|");
			$('#quickSearchTerm').val(divisionNamesArray[0]);
			valueSelected = divisionNamesArray[1];
		}
		/* P23695a Blue Link changes - Start - N204189 */
		var valueToDisplay = trim($('#quickSearchSelection :selected').text());
		$('#hl-autocomplete-search').attr('value', valueToDisplay );
		
		$('#actualSearchTerm').val(valueSelected);
		$('#actualDisplayTerm').val(valueToDisplay);
		
		/* P23695a Blue Link changes - End - N204189 */
		$('#thrdColSelectedVal').val(valueSelected);
			//SR1034 changes
			var type = $('#quickSearchSelection').children(":selected").attr("type")
			if(type!=null && type!=undefined)
				{
					$('#ioe_qType').val(type);
				}
		triggerSearchButtonEvent();
		if(urlProtocol == urlProtocolNonSecure){
			var location = trim($('#hl-autocomplete-search-location').val());
			/*-- START CHANGES P23695 Medicare Spanish Translation - n709197 --*/
			if(location == undefined || location == ghostTextWhereBox || location == 'Código postal o ciudad, estado' || location ==''){
			/*-- END CHANGES P23695 Medicare Spanish Translation - n709197 --*/
				/* P23695a Blue Link changes - Start - N204189 */
				showLocationDialogBox( valueSelected, valueToDisplay);
				/* P23695a Blue Link changes - End - N204189 */
			}
			else{
				$('#geoSearch').val(location);
				/* P23695a Blue Link changes - Start - N204189 */
				$('#hl-autocomplete-search').val(trim($('#quickSearchSelection :selected').text()));
				
				$('#actualSearchTerm').val(valueSelected);
				$('#actualDisplayTerm').val(valueToDisplay);
				
				/* P23695a Blue Link changes - End - N204189 */
				$('#thrdColSelectedVal').val(valueSelected);
				$('.hl-searchbar-button').click();
				$('#locationDialogBox').trigger('hide');
			}
		}else{
			$('.hl-searchbar-button').click();
		}
		/*End changes for Story 9704*/
		}
		}
	}
}

function closeModalBoxWithId(id){
	if(ieVersion == 8){
		$(id).trigger('hide');
	}
	planTypeForPublic = '';
	/* P08-8423a Sprint23 - Story9249/9257/9258 Changes Start */
	if(id == '#preSearchDialogBox'){
		$('#quickSearchTypeThrCol').val('');
		/*-----START CHANGES A9991-1034 A615A-1094 Nov 2013-----*/
		$('#ioeqSelectionInd').val('');
		$('#ioe_qType').val('');
		$('#classificationLimit').val('');
		$('#suppressFASTDocCall').val('');
		$('#pcpSearchIndicator').val('');
		$('#specSearchIndicator').val('');
		$('#axcelSpecialtyAddCatTierTrueInd').val('');
	}
	/* P08-8423a Sprint23 - Story9249/9257/9258 Changes End */
}
/*P8423a Sprint17 - Story4558 Changes End*/
/*P8423a Sprint17 - Story7910 Changes Start*/
function askann1appidFunction(){
	var options = new Object();
	options.annURL = annLaunchUrl;
	options.annUniqueIdentifier = uniqueAnnParam;
	var annURL = options.annURL;
	var unique = options.annUniqueIdentifier;

	NIT.LaunchAgent(annURL, unique);
}

function askann1appidFunctionLeft(){
	var options = new Object();
	options.annURL = annLaunchUrl;
	options.annUniqueIdentifier = annLaunchLeftParam;
	var annURL = options.annURL;
	var unique = options.annUniqueIdentifier;

	NIT.LaunchAgent(annURL, unique);
}

function askann1appidFunctionSecure(){
	var options = new Object();
	options.annURL = annLaunchUrl;
	options.annUniqueIdentifier = uniqueAnnParam;
	var annURL = options.annURL;
	var unique = options.annUniqueIdentifier;

	NIT.LaunchAgent(annURL, unique);
}

function askann1appidSecureLeft(){
	var options = new Object();
	options.annURL = annLaunchUrl;
	options.annUniqueIdentifier = annLaunchLeftParam;
	var annURL = options.annURL;
	var unique = options.annUniqueIdentifier;

	NIT.LaunchAgent(annURL, unique);
	
}

/*P8423a Sprint17 - Story7910 Changes End*/

/*P8423a Sprint19 - Story8131 Changes Start*/

function contact_us()
{
	var url= CONTEXT_ROOT + 'docfind_contact_us.html';
	if(window.name == "popup")
	{
		location.href = url;
	}
	else
	{
		var windowName = "popup";
		var winOpts = 'width=600,height=525,scrollbars=yes,resizable=yes,toolbar=yes';
		aWindow = window.open(url, windowName, winOpts);
		aWindow.focus();
	}
}

function contact_secure_ft(){
	var url= $('#memberSecureDomain').text() + '/memberSecure/featureRouter/contactUs?page=docFind';
	if(window.name == "popup"){
		location.href = url;
	}else{
		var windowName = "popup";
		var winOpts = 'width=850,height=600,scrollbars=yes,resizable=yes,toolbar=yes';
		
		aWindow = window.open(url, windowName, winOpts);
		aWindow.focus();
	}
}

/*P8423a Sprint19 - Story8131 Changes End*/


/*P8423a Sprint0 - Story9535 Changes Start*/
/* Start changes for P21861a May15 release - N709197 */
function loginToDSE(){
	var site_id = $.getUrlVar('site_id');
	if($('#site_id').val()!=null && $('#site_id').val()!=undefined && $('#site_id').val() == 'innovationhealth'){
		$('#logInTop2').click(function(){
			window.location = 'https://'+getIhDseDomainName()+'/MbrLanding/RoutingServlet?createSession=true';
		});
	}else{
	$('#logInTop2').click(function(){
		window.location = $('#loginBoxUrl').text();
	});
	}    
}

function registerToDSE(){
	var site_id = $.getUrlVar('site_id');
	if($('#site_id').val()!=null && $('#site_id').val()!=undefined && $('#site_id').val() == 'innovationhealth'){
		$('#registerTop2').click(function(){
			window.location = 'https://'+getIhDseDomainName()+'/memberRegistration/register/home';
		});
	}else{
	$('#registerTop2').click(function(){
		window.location = $('#regUrl').text();
	});
	}    
}
/* End changes for P21861a May15 release - N709197 */
/*P8423a Sprint0 - Story9535 Changes End*/

/***********************************************************************************************************
CLINICAL QUALITY AEXCEL FUNCTIONS START FROM HERE
***********************************************************************************************************/

/* This is Aexcel info */
function docfind_additional_info_aexcel(){
	var domRegistration = document.domain;
	domDemographics = "";
	
	if ( domRegistration.substr(0,3)=="dev"){
		domDemographics = "dev3www.aetna.com"
	}
	else if(domRegistration.substr(0,2) =="qa"){
		domDemographics = "qa3www.aetna.com"
	}
	else if(domRegistration.substr(0,3) =="str"){	
		domDemographics = "str2www.aetna.com"	
	}	
	else{
		domDemographics = "www.aetna.com"	
	}
	
	var windowName='cancel';
	var url="http://"+domDemographics+"/docfind/docfind_additional_information_aexcel.html";
	var winOpts = 'width=600,height=525,scrollbars=yes,resizable=yes';
	window.name='MAINWINDOW';
	aWindow=window.open(url,windowName,winOpts);
}

function learn_more_aexcel(){
	var windowName='cancel';
	var url = url_aexcel();
	var winOpts = 'width=600,height=525,scrollbars=yes,resizable=yes';
	window.name='MAINWINDOW';
	aWindow=window.open(url,windowName,winOpts);
}


function aexcelSpec(){
	var windowName='cancel';
	var url = url_aexcel()+'#spec';
	var winOpts = 'width=600,height=525,scrollbars=yes,resizable=yes';
	window.name='MAINWINDOW';
	aWindow=window.open(url,windowName,winOpts);
}

function aexcelInfoVolume(){
	var windowName='cancel';
	var url = url_aexcel()+'#volume';
	var winOpts = 'width=600,height=525,scrollbars=yes,resizable=yes';
	window.name='MAINWINDOW';
	aWindow=window.open(url,windowName,winOpts);
}

function aexcelInfoQual(){
	var windowName='cancel';
	var url = url_aexcel()+'#qual';
	var winOpts = 'width=600,height=525,scrollbars=yes,resizable=yes';
	window.name='MAINWINDOW';
	aWindow=window.open(url,windowName,winOpts);
}

function aexcelInfoPerformance(){
	var windowName='cancel';
	var url = url_aexcel()+'#performance';
	var winOpts = 'width=600,height=525,scrollbars=yes,resizable=yes';
	window.name='MAINWINDOW';
	aWindow=window.open(url,windowName,winOpts);
}

function aexcelInfoAdverse(){
	var windowName='cancel';
	var url = url_aexcel()+'#adverse';
	var winOpts = 'width=600,height=525,scrollbars=yes,resizable=yes';
	window.name='MAINWINDOW';
	aWindow=window.open(url,windowName,winOpts);
}

function aexcelInfo30(){
	var windowName='cancel';
	var url = url_aexcel()+'#30';
	var winOpts = 'width=600,height=525,scrollbars=yes,resizable=yes';
	window.name='MAINWINDOW';
	aWindow=window.open(url,windowName,winOpts);
}

function aexcelInfoBreast(){
	var windowName='cancel';
	var url = url_aexcel()+'#breast';
	var winOpts = 'width=600,height=525,scrollbars=yes,resizable=yes';
	window.name='MAINWINDOW';
	aWindow=window.open(url,windowName,winOpts);
}

function aexcelInfoCerv(){
	var windowName='cancel';
	var url = url_aexcel()+'#cerv';
	var winOpts = 'width=600,height=525,scrollbars=yes,resizable=yes';
	window.name='MAINWINDOW';
	aWindow=window.open(url,windowName,winOpts);
}

function aexcelInfoHiv(){
	var windowName='cancel';
	var url = url_aexcel()+'#hiv';
	var winOpts = 'width=600,height=525,scrollbars=yes,resizable=yes';
	window.name='MAINWINDOW';
	aWindow=window.open(url,windowName,winOpts);
}

function aexcelInfoBeta(){
	var windowName='cancel';
	var url = url_aexcel()+'#beta';
	var winOpts = 'width=600,height=525,scrollbars=yes,resizable=yes';
	window.name='MAINWINDOW';
	aWindow=window.open(url,windowName,winOpts);
}

function aexcelInfoEff(){
	var windowName='cancel';
	var url = url_aexcel()+'#eff';
	var winOpts = 'width=600,height=525,scrollbars=yes,resizable=yes';
	window.name='MAINWINDOW';
	aWindow=window.open(url,windowName,winOpts);
}

function faq(){
	var windowName='cancel';
	var url = url_aexcel();
	var winOpts = 'width=600,height=525,scrollbars=yes,resizable=yes';
	window.name='MAINWINDOW';
	aWindow=window.open(url,windowName,winOpts);
}

function url_aexcel(){
	var domRegistration = document.domain;
	domDemographics = "";
	
	if (domRegistration.substr(0,4)=="dev2"){
		domDemographics = "dev2www.aetna.com";
	}else if(domRegistration.substr(0,4)=="dev3"){
		domDemographics = "dev3www.aetna.com";
	}else if(domRegistration.substr(0,3)=="dev"){
		domDemographics = "devwww.aetna.com";
	}else if(domRegistration.substr(0,3)=="qa2"){
		domDemographics = "qa2www.aetna.com";
	}else if(domRegistration.substr(0,3)=="qa3"){
		domDemographics = "qa3www.aetna.com";
	}else if(domRegistration.substr(0,3)=="str"){
		domDemographics = "str2www.aetna.com";
	}else if(domRegistration.substr(0,2)=="qa"){
		domDemographics = "qawww.aetna.com";
	}else{
		domDemographics = "www.aetna.com";
	}
	
	var windowName='cancel';
	var url="http://"+domDemographics+"/docfind/docfind_additional_information_aexcel.html";
	return url;
}

/***********************************************************************************************************
									CLINICAL QUALITY AEXCEL FUNCTIONS END HERE
***********************************************************************************************************/





/*P8423a Sprint19 - Story7061 Changes Start*/
function medformSubmit(id){
	if($("input[@name=groupIpaNameCappOffMapRadio_"+id+"]:checked").val() != null && $("input[@name=groupIpaNameCappOffMapRadio_"+id+"]:checked").val() != ''){
		$('#navPcpDeepLinkMedForm'+id).children('#capOffice').val($("input[@name=groupIpaNameCappOffMapRadio_"+id+"]:checked").val());
	}
	var patAccptNewPatInd = $('#navPcpDeepLinkMedForm'+id).children('#acceptNewPatInd').val();
	if(patAccptNewPatInd == 'N'){
		var provName = $('#navPcpDeepLinkMedForm'+id).children('#providerFullName').val();
		showNoPatModal(provName,id,'MED');
	}else{
		$('#navPcpDeepLinkMedForm'+id).submit();
	}
}

function medformSubmitDetailPage(){
	if($("input[@name=groupIpaNameCappOffMapRadioDetails]:checked").val() != null && $("input[@name=groupIpaNameCappOffMapRadioDetails]:checked").val() != ''){
		/*-----START CHANGES P18029-P19546-PCR17890 PCPInqService Feb 2014-----*/
		$('#navPcpDeepLinkMedFormDetailsPage').children('#capOffice').val($("input[@name=groupIpaNameCappOffMapRadioDetails]:checked").val());
		/*-----END CHANGES P18029-P19546-PCR17890 PCPInqService Feb 2014-----*/
	}
	var patAccptNewPatInd = $('#navPcpDeepLinkMedFormDetailsPage').children('#acceptNewPatInd').val();
	if(patAccptNewPatInd == 'N'){
		var provName = $('#navPcpDeepLinkMedFormDetailsPage').children('#providerFullName').val();
		showNoPatModal(provName,id,'MED');
	}else{
		$('#navPcpDeepLinkMedFormDetailsPage').submit();
	}
}
/*P8423a Sprint19 - Story7061 Changes End*/

/*P8423a Sprint19 - Story7099 Changes Start*/
function denformSubmit(id){
	if($("input[@name=groupIpaNameCappOffMapRadio_"+id+"]:checked").val() != null && $("input[@name=groupIpaNameCappOffMapRadio_"+id+"]:checked").val() != ''){
		$('#navPcpDeepLinkDenForm'+id).children('#providerId').val($("input[@name=groupIpaNameCappOffMapRadio_"+id+"]:checked").val());
		$('#navPcpDeepLinkDenForm'+id).children('#capOffice').val($("input[@name=groupIpaNameCappOffMapRadio_"+id+"]:checked").val());
	}
	var patAccptNewPatInd = $('#navPcpDeepLinkDenForm'+id).children('#acceptNewPatInd').val();
	if(patAccptNewPatInd == 'N'){
		var provName = $('#navPcpDeepLinkDenForm'+id).children('#providerFullName').val();
		showNoPatModal(provName,id,'DEN');
	}else{
		$('#navPcpDeepLinkDenForm'+id).submit();
	}
}

function denformSubmitDetailPage(){
	if($("input[@name=groupIpaNameCappOffMapRadioDetails]:checked").val() != null && $("input[@name=groupIpaNameCappOffMapRadioDetails]:checked").val() != ''){
		/*-----START CHANGES P18029-P19546-PCR17890 PCPInqService Feb 2014-----*/
		$('#navPcpDeepLinkDenFormDetailsPage').children('#providerId').val($("input[@name=groupIpaNameCappOffMapRadioDetails]:checked").val());
		$('#navPcpDeepLinkDenFormDetailsPage').children('#capOffice').val($("input[@name=groupIpaNameCappOffMapRadioDetails]:checked").val());
		/*-----END CHANGES P18029-P19546-PCR17890 PCPInqService Feb 2014-----*/
	}
	var patAccptNewPatInd = $('#navPcpDeepLinkDenFormDetailsPage').children('#acceptNewPatInd').val();
	if(patAccptNewPatInd == 'N'){
		var provName = $('#navPcpDeepLinkDenFormDetailsPage').children('#providerFullName').val();
		showNoPatModal(provName,id,'DEN');
	}else{
		$('#navPcpDeepLinkDenFormDetailsPage').submit();
	}
}
/*P8423a Sprint19 - Story7099 Changes End*/

/* P08-8423a Sprint21 - Story8873 Changes Start */
var noPatModalClick = true;
var noPatModalAckClick = true;

function showNoPatModal(provName,id,provType){
	if(noPatModalClick){
		buildNoPatModalBox(provName,id,provType);
		$('#noPatModalBoxPlaceHolder').trigger('show');	
		$('#noPatModalBoxPlaceHolder').css('display','none');
		noPatModalClick = false;
	}else{
		$('#noPatModalBoxPlaceHolder').trigger('show');
		$('#noPatModalBoxPlaceHolder').css('display','none');
	}
}

function showNoPatAckModal(provName){
	closeNoPatModalBox();
	$('#noPatAckModalBox').trigger('show');	
	$('#noPatAckModalBox').css('display','none');
}

function buildNoPatModalBox(provName,id,provType){
	var dialogText1 = $('#noPatText1').text() + provName + $('#noPatText2').text();
	var dialogText2 = $('#noPatText3').text();
	$('#noPatModalBoxPlaceHolder').attr('title_noPatModalBox', '<span>Note</span><br />');
	$('#noPatModalBoxPlaceHolder').attr('subtitle_noPatModalBox', '');
	$('#noPatModalBoxPlaceHolder').attr('dialogText_noPatModalBox', '<span class="pcpErrorText">' + dialogText1 +'</span><p style="margin-top:4px;margin-bottom:0px;">' + dialogText2 + '</p>');	
	
	$('#noPatModalBoxPlaceHolder').doDialogDse({width: 300, modal:true, draggable:true, closeOnEscape:true},
			[{id:'btnYes',value:'YES', "url":"javascript:void();"},
			 {id:'btnNo',value:'NO', "url":"javascript:void();"}],'noPatModalBox');
	
	$("#btnYes").click(function(){
		closeNoPatModalBox();
		if(provType == 'MED'){
			$('#navPcpDeepLinkMedForm'+id).submit();
		}else if (provType == 'DEN'){
			$('#navPcpDeepLinkDenForm'+id).submit();
		}
	});
	
	$("#btnNo").click(function(){
		showNoPatAckModal();
	});
	
	buildNoPatAckModalBox(provName);
	return false;
}

function buildNoPatAckModalBox(provName){
	var dialogText1 = $('#noPatText4').text() + provName + $('#noPatText5').text();
	var dialogText2 = $('#noPatText6').text();
	$('#noPatAckModalBox').attr('title_noPatAckModal', '<span>Note</span><br />');
	$('#noPatAckModalBox').attr('subtitle_noPatAckModal', '');
	$('#noPatAckModalBox').attr('dialogText_noPatAckModal', '<span class="pcpErrorText">' + dialogText1	+'</span><br /><p class="pcpErrorText" style="margin-top:4px;margin-bottom:0px;">' + dialogText2 + '</p>');	
	
	$('#noPatAckModalBox').doDialogDse({width: 300, modal:true, draggable:true, closeOnEscape:true},
			[{id:'btnCloseAck',value:'CLOSE', "url":"javascript:void();"}],'noPatAckModal');

	$("#btnCloseAck").click(function(){
		$('.dialog-main-wrapper_noPatAckModal').css("display","none");
		$('#dialog_modal_id_noPatAckModal').css("display","none");
	});
	return false;
}

function closeNoPatModalBox(){
	$('#dialog_modal_id_noPatModalBox').css("display","none");
	$('.dialog-main-wrapper_noPatModalBox').css("display","none");
}

/* P08-8423a Sprint21 - Story8873 Changes End */

/* P08-8423a Sprint22 - Story6841 Changes Start */
function checkProvMoreSpec(obj){
	if(obj.value == 'PROV_MEDSPEC'){
		specFromDB(obj.value);
	}
}

function specFromDB(obj,obj1){
	var selectedPlanVal = $('#modal_aetna_plans :selected').val();
	var stateCode = $('#stateDD').val();
	if(obj=='PROV_BHP' || obj=='PROV_EAP'){
		if(stateCode == "FL" && (selectedPlanVal == "MEHMO|Aetna Medicare(SM) Plan (HMO)" || selectedPlanVal == "MEHMO|Aetna Medicare Connect Plus (HMO)" 
			|| selectedPlanVal == "MEHMO|Aetna Medicare Value Plan (HMO)" || selectedPlanVal =="MEHMO|Aetna Medicare Premier Plan (HMO)")){
			location.href = "javascript:popUp('/dse/search/disclaimer?continueUrl=http://providersearch.mhnet.com/Members/CoventryHealthCareProviderSearch/tabid/397/Default.aspx')";
			return;
		}
	}
	updateHiddenVarForQuickSearch(obj1);
	if(obj=='PROV_PCP'){
		$('#classificationLimit').val('DMP');
		$('#suppressFASTDocCall').val('true');
		$('#pcpSearchIndicator').val('true');
	}
	
	var queryParameters = "site_id="+site_id+"&langPref="+langPref+"&contentId=" + obj;
	computeModelPlanType(obj);
	$('#preSearchModalContent').load('search/preSearchContentAjaxDB?' + queryParameters, function(response, status){
		if(isQuickSearchClicked){
				changeFormat();
				buildPreSearchListBox(response);
				$('#preSearchDialogBox').css("display","none");
				if(urlProtocol == urlProtocolNonSecure){
					$('.dialog-content-wrap_preSearchDialogBox').css("background-color","#ffffff");
					//$('.dialog-content-wrap_preSearchDialogBox').css("border","5px solid #D1D1D1");
				}
				isQuickSearchClicked = false;
			}else{
				$('#preSearchModalContentTable').html('<tr><td>'+response+'</td></tr>');
				$('#preSearchDialogBox').trigger('show');
				$('#preSearchDialogBox').css("display","none");
				if(urlProtocol == urlProtocolNonSecure){
					$('.dialog-content-wrap_preSearchDialogBox').css("background-color","#ffffff");
					//$('.dialog-content-wrap_preSearchDialogBox').css("border","5px solid #D1D1D1");
				}
			}
	});
     if(ieVersion == 10){
		window.setTimeout(function(){renderQuickSearchModal();}, 90);
	}
}

function limitSpec(select){
	var selected = 0;
	for(var i=0; i < select.options.length; i++){
		if(select.options[i].selected){
			selected++;
		}
		if(selected > 3){
			select.options[i].selected = false;
		}
	}
}

function staticRedirect(obj){
	if(obj.value == 'PCDMexico'){
		window.location.href="http://www.aetna.com/docfind/cms/html/mexico_dental_network.html";
	}
	if(obj.value == 'National Lab Listing'){
		var redirectnationalLabListingUrl = 'http://'+getPublicDseDomainName()+'/dse/cms/codeAssets/html/National_Lab_Listing.html';
		window.location.href = redirectnationalLabListingUrl;
	}
	
	if(obj.value == 'National Lab Listing' && langPref == 'sp'){
		var redirectnationalLabListingUrl = 'http://'+getPublicDseDomainName()+'/dse/cms/codeAssets/html/es/National_Lab_Listing_sp.html';
		window.location.href = redirectnationalLabListingUrl;
	}
/*-----START REVERTING CHANGES A9991-1034 A615A-1094 Nov 2013-----*/
	/*if(obj.value == 'Infertility'){
		popUpResize('http://www.aetna.com/docfind/cms/html/institutes_of_excellence_infertility.html');
	}
	if(obj.value == 'Bariatric Surgery Facility'){
		window.location.href="http://www.aetna.com/dse/cms/codeAssets/html/static/bariatric_facilities.html";
	}
	if(obj.value == 'Cardiac Intervention' || obj.value == 'Cardiac Rhythm' || obj.value == 'Cardiovascular Surgery'){
		window.location.href="http://www.aetna.com/dse/cms/codeAssets/html/static/institutes_of_quality_cardiac.html";
	}
	if(obj.value == 'Spine/Orthopedic' || obj.value == 'Total Joint Replacement Orthopedic'){
		window.location.href="http://www.aetna.com/dse/cms/codeAssets/html/static/orthopedic_facilities.html";
	}*/
/*-----END REVERTING CHANGES A9991-1034 A615A-1094 Nov 2013-----*/
}

/* P08-8423a Sprint22 - Story6841 Changes End */

function computeModelPlanType(str){
	if(str == "PROV_MEDTHEP" || str == "PROV_PCP" || str == "PROV_MEDSPEC" || 
			str == "Natural Therapy Professionals" || str == "All Medical Professionals" || str == "PROV_BHP" || 
				str == "PROV_LABS" || str == "Dialysis Centers" || str == "Urgent Care Centers" || 
					str == "Hospitals" || str == "Walk-In Clinics" || str == "medical" || 
						str == "PROV_MHF" || str == "PROV_SAF" || str == "PRVO_RTF" || 
							str == "PROV_IOQ" || str == "PROV_IOE" || str == "PROV_THPREH" || str == "PROV_IMG"
								|| str == "All Hospitals and Facilities" || str == "PROV_THPREH" || str == "Medical Equipment Suppliers" 
									|| str == "PROV_MT"	|| str == "PROV_OT"  	|| str == "Hospice"){
		planTypeForPublic = "medical_plans";
	}else if(str == "Primary Care Dentists (PCD)" || str == "PROV_DENSPEC" || str == "All Dental Professionals")	{
		planTypeForPublic = "dental_plans";
	}else if(str == "Hearing Discount Locations"){
		planTypeForPublic = "hearing_plans";
	}else if(str == "Vision routine eyewear and exam"){ 
		planTypeForPublic = "hearing_plans";
		//ptID = "vision_provider_type";
	}else if(str == "Pharmacies" || str == "Pharmacy Discount Locations"){
		planTypeForPublic = "pharmacy_plans";
	}else if( str == "ipacal"){
		planTypeForPublic = "ipacal_plans";
		//ptID = "ipacal_provider_type";
	}else if(str == "PROV_EAP"){
		planTypeForPublic = "eap_plans"; 
	}
	
}

function getPlanListDiv(planTypeForPublic){
	if(planTypeForPublic == "medical_plans"){
		return '#modal_plans_medical';
	}else if(planTypeForPublic == "dental_plans"){
		return '#modal_plans_dental';
	}else if(planTypeForPublic == "hearing_plans"){
		return '#modal_plans_hearing';
	}else if(planTypeForPublic == "pharmacy_plans"){
		return '#modal_plans_pharmacy';
	}else if(planTypeForPublic == "ipacal_plans"){
		return '#modal_plans_ipacal';
	}else if(planTypeForPublic == "eap_plans"){
		return '#modal_plans_eap';
	}else{
		return '#modalPlans';
	}
}

/* P08-8423a Sprint24 - Story9276 Changes Start */
function isTab1Selected(isTab1)
{			
	if(isTab1 == '')
	{
		
	}
	else
	{
		if(isTab1 == '1')
		{
			$("#isTab1Clicked").val('true');
			$("#isTab2Clicked").val('false');
			searchSubmit('true');
			$("#docfindSearchEngineForm").submit();
		}
		else if (isTab1 == '2'){
			$("#isTab1Clicked").val('false');
			$("#isTab2Clicked").val('true');
			searchSubmit('true');
			$("#docfindSearchEngineForm").submit();
		}				
	}			
}
/* P08-8423a Sprint24 - Story9276 Changes End */

/* P08-8423a Sprint3 - Story9839 Changes Start */
function createElementsForHLDisplayNames(){
	var hlDispNameList = $('#hlDispNameList').text();
	if(hlDispNameList.indexOf(',') != -1){
		var hlDispNameArray = new Array();
		hlDispNameArray = hlDispNameList.split(',');
		for(count=0; count<hlDispNameArray.length; count++){
			if(hlDispNameArray[count].indexOf('##')!=-1){
				var hlDispElements = hlDispNameArray[count].split('##');
				$('body').append('<div id=' + hlDispElements[0].toLowerCase() + 'hlLabel style=display:none;>' + hlDispElements[1] + '</div>');
			}
		}
	}
}
/* P08-8423a Sprint3 - Story9839 Changes End */

/***************************************************************************************************************
										CENTER SECTION SCRIPTS END HERE
****************************************************************************************************************/

/***************************************************************************************************************
										GENERIC FUNCTIONS START FROM HERE
****************************************************************************************************************/
function IEVersionCheck(){
	if(/MSIE (\d+\.\d+);/.test(navigator.userAgent))
	{
		var ieversion=new Number(RegExp.$1);
		return ieversion;
	}
	else if(!!navigator.userAgent.match(/Trident\/7.0/) && !!			navigator.userAgent.match(/.NET4.0E/))
	{
		var ieversion = 11;
		return ieversion;
	}
	else if (navigator.appName == 'Microsoft Internet Explorer')
  	{
    		var ua = navigator.userAgent;
		var re  = new RegExp("MSIE ([0-9]{1,}[\.0-9]{0,})");
		var ieversion = null;
  	  	if (re.exec(ua) != null){
      		ieversion = parseFloat(RegExp.$1);
		}
		return ieversion; 
  	}
	else if (navigator.appName == 'Netscape')
  	{
    		var ua = navigator.userAgent;
    		var re  = new RegExp("Trident/.*rv:([0-9]{1,}[\.0-9]					{0,})");
		var ieversion = null;
	  	if (re.exec(ua) != null){
			ieversion = parseFloat(RegExp.$1);
		}
  		return ieversion;
	}
	return null;
}

function populateUrlParameters(){
	$.extend({
		getUrlVars: function(){
			var vars = [], hash;
			var hashes = window.location.href.slice(window.location.href.indexOf('?') + 1).split('&');
			for(var i = 0; i < hashes.length; i++){
				hash = hashes[i].split('=');
				vars.push(hash[0]);
				vars[hash[0]] = hash[1];
			}
			return vars;
		},
		getUrlVar: function(name){
			return $.getUrlVars()[name];
		}
	});
}

function showSpinner(){
	showAndPlaceBusyModalPopupBox($('#spinner'),170,410);
      //var height = ($(document).height()-215)/4;
      var height = ($(window).height()-215)/4 + $(window).scrollTop();
	$('.TransparentBorder').css("background-color","#333333");
      $('.TransparentBorder').css("margin-top", height + "px");
	$('.BusyIndicatorBox').css("margin-top", height+15 + "px");
	$('#spinner').show();
}

function hideSpinner(){
	$('#spinner').hide();
}

/*P8423a Sprint18 - Story6904 Changes Start*/
function showModelSpinner(){
	/*Changing top and left value for center position*/
	showAndPlaceBusyModalPopupBox($('#modelSpinner'),20,50);
	$('.TransparentBorder').css("background-color","#333333");
	$('#modelSpinner').show();
}

function hideModelSpinner(){
	$('#modelSpinner').hide();
}
/* Show spinner when coming from Nav */
function showSpinnerFromNav(){
	var previousUrl =  previousPage;
	if(previousUrl.indexOf("memberSecure") != -1){
		showSpinner();
	}
}

function hideSpinnerFromNav(){
	var previousUrl =  previousPage;
	if(previousUrl.indexOf("memberSecure") != -1){
		window.setTimeout(function () {
			hideSpinner();
			},3000);
	}
}

function hideSpinnerForCAndFModel(){
	var previousUrl =  previousPage;
	if(previousUrl.indexOf("memberSecure") != -1){
			hideSpinner();
	}
}
/*P8423a Sprint18 - Story6904 Changes End*/

/* Start changes for P19134a November release 2013 */
function setSelectedForDropdown(dd, value){
	if(dd !=null && dd.options != null){
		for(var i=0; i < dd.options.length; i++){
			if(dd.options[i].value == value){
				dd.options[i].selected = true;
			}
		}
	}
}
/* Start changes for P19134a November release 2013 */

function popUp(URL){
	var windowName='popup';
	var winOpts = 'width=600,height=525,scrollbars=yes,resizable=yes,toolbar=yes,location=1,overflow=scroll';
	window.name='INDEX';	
	aWindow=window.open(URL,windowName,winOpts);
	aWindow.focus();
}

function popUpCustom(URL){
	var windowName='popup';
	var winOpts = 'width=1000,height=1000,scrollbars=yes,resizable=yes,toolbar=yes,overflow=scroll';
	window.name='INDEX';	
	aWindow=window.open(URL,windowName,winOpts);
	aWindow.focus();
}

function popUpResize(URL){
	var windowName='popup';
	var winOpts = 'width=800,height=600,scrollbars=yes,resizable=yes,toolbar=yes,overflow=scroll,location=yes,left=10,top=10';
	window.name='INDEX';	
	aWindow=window.open(URL,windowName,winOpts);
	aWindow.focus();
}
/*P8423a Sprint18 - Story6396-7342 Changes Start*/
/* POPUP for CMS related HTML Files */   
function smallPopUp(URL){
	var windowName='popup';
	var winOpts = 'width=500,height=425,scrollbars=yes,resizable=yes,toolbar=yes,overflow=scroll';
	window.name='INDEX';	
	aWindow=window.open(URL,windowName,winOpts);
	aWindow.focus();
}
/*P8423a Sprint18 - Story6396-7342 Changes End*/
/*P8423a Sprint14 - Story6396 Changes Start*/
function removeCSSForIE8(){
	var IEversion = IEVersionCheck();
	if(IEversion == 8 && IEversion != null){
		$('link[title="rdCommonCSS"]').remove('body');
	}
	window.print();
	$('head').append('<link href="/docfind/assets/css/rdCommon.css" rel="stylesheet" type="text/css" media="screen" title="rdCommonCSS"/>');
}

function focusPanel(showHideDiv, switchImgTag, name){
	var ele = document.getElementById(showHideDiv);
	var imageEle = document.getElementById(switchImgTag);
	if(ele.style.display == "none" || ele.style.display == "") {
		$('#'+showHideDiv).toggle('slow');
		ele.style.padding = "10px";
		 //imageEle.innerHTML = '<img class="blockImageBorder" src="/dse/assets/images/buttons_close2.gif">';
            imageEle.innerHTML = '<div class="blockImageBorderDiv"><img class="blockImageBorder" src="/dse/cms/codeAssets/images/accordion-close.png"></div>'+'<span class="accordionText">'+name+'</span>';
	}
	//imageEle.focus();
	//$(window).scrollTop(imageEle.offset().top);
      /* Story 10257*/
      $(window).scrollTop($('#'+switchImgTag).offset().top);
}
/*P8423a Sprint14 - Story6396 Changes End*/

/*P8423a Sprint17 - Story6190 Changes Start*/
function onlyNumbers(evt){
    var charCode = evt.which || evt.keyCode;
    if (charCode > 31 && (charCode < 48 || charCode > 57) && evt.keyCode!=46){
        return false;
    } 
    return true;
}
/*P8423a Sprint17 - Story6190 Changes End*/

function getPublicDseDomainName(){
	var domainName = document.domain;
	var retDomainName = "";
	if(domainName.substr(0,4)=="dev2"){
		retDomainName = "dev2www.aetna.com";
	}
	else if(domainName.substr(0,4)=="dev3"){
		retDomainName = "dev3www.aetna.com";
	}
	else if (domainName.substr(0,3)=="dev"){
		retDomainName = "devwww.aetna.com";
	}else if(domainName.substr(0,3)=="qa2"){
		retDomainName = "qa2www.aetna.com";
	}else if(domainName.substr(0,3)=="qa3"){
		retDomainName = "qa3www.aetna.com";
	}else if(domainName.substr(0,3)=="str"){
		retDomainName = "strwww.aetna.com";
	}
	else if(domainName.substr(0,2)=="qa"){
		retDomainName = "qawww.aetna.com";
	}
	else{
		retDomainName = "www.aetna.com";
	}
	return retDomainName;
}

function getSecureDseDomainName(){
	var domainName = document.domain;
	var retDomainName = "";
	if (domainName.substr(0,4)=="dev2"){
		retDomainName = "dev2www1.aetna.com";
	}else if(domainName.substr(0,4)=="dev3"){
		retDomainName = "dev3www1.aetna.com";
	}else if(domainName.substr(0,3)=="dev"){
		retDomainName = "devwww1.aetna.com";
	}else if(domainName.substr(0,3)=="qa2"){
		retDomainName = "qa2www1.aetna.com";
	}else if(domainName.substr(0,3)=="qa3"){
		retDomainName = "qa3www1.aetna.com";
	}else if(domainName.substr(0,3)=="str"){
		retDomainName = "strwww1.aetna.com";
	}else if(domainName.substr(0,2)=="qa"){
		retDomainName = "qawww1.aetna.com";
	}else{
		retDomainName = "www1.aetna.com";
	}
	return retDomainName;
}

var ua = $.browser;
function browserName(){
	if (ua.mozilla) {
	   return 'mozilla';
	}else if (ua.msie) {
	   return 'msie';
	}else if (ua.chrome) {
	   return 'chrome';
	}else if (ua.opera) {
	   return 'opera';
	}else if (ua.safari) {
	   return 'safari';
	}
	return null;
}

function browserVersion(){
	return ua.version.slice(0,3);
}

function markPageFilterGeoSearch(){
	var paginationValue = $("#pagination").val();
	var filterValue = $("#filterValues").val();
	
	if((paginationValue === undefined || paginationValue == '') 
			&& (filterValue === undefined || filterValue == '')){
		whyPressed = 'geo';
		markPage('clickedDistance');
	}
}

function annSearchComplete() {
	NIT.RaiseAgentEvent(NIT.DocFindSearchComplete);  
	/*-----START CHANGES P19791a Exchange August 2013-----*/
	if($('#site_id').val() == 'QualifiedHealthPlanDoctors' && (window.location.href.indexOf('search/detail') != -1 || window.location.href.indexOf('markPage') != -1)){
		$('#homeLeftSectionExchange').css('display','none');
	} 
	/*-----END CHANGES P19791a Exchange August 2013-----*/
	/*-----START CHANGES P8551c QHP_IVL PCR - n204189-----*/
	if($('#site_id').val() == 'ivl' && (window.location.href.indexOf('search/detail') != -1 || window.location.href.indexOf('markPage') != -1)){
		$('#homeLeftSectionExchange').css('display','none');
	} 
	/*-----END CHANGES P8551c QHP_IVL PCR - n204189-----*/
	/*$('#summaryPageINFO').css('display','block');
	$('#summaryPageINFOSpace').css('display','block');*/
	// Content 1023 changes
	$('#summaryPageAddINFO').css('display','block');
	$('#summaryPageAddINFOSpace').css('display','block');

}

function deleteAnnErrorCookie() {
	var $=jQuery
//	$.cookie("memberPageErrors", null, { expires: -1 });
	$.cookie("memberPageErrors", null, { expires: -1, path: '/', domain: '.aetna.com' });
}

function annErrorCookieDSE(error,errorType){
	
	if (errorType == 'System') {
		error = 'SystemError=' + error 
	}
	if (errorType == 'Alert') {
		error = 'Alert=' + error 
	}
	if (errorType =='Red') {
		error = 'Red=' + error 
	}

	if (error != null) {		 	
		deleteAnnErrorCookie(); 	
		var $=jQuery;
		$.cookie("memberPageErrors", error,  {path: '/', domain: '.aetna.com'} );		
	}	
		
}
function narrowNetworkModalBox(flagUrl, title){
	title = null;
    $contentElement = $("#narrowNetworkModal");
    $contentElement.load(flagUrl, null,                         
    function() {
    	$('#narrowNetworkModal').trigger('show');
    	$('#narrowNetworkModal.dialog-content').parents('div.dialog-main-wrapper').children('div.dialog-content-wrap').children('div.dialog-title').html('');
    	$('#narrowNetworkModal.dialog-content').parents('div.dialog-main-wrapper').children('div.dialog-close-button').css("left","752px");
    	$('#narrowNetworkModal.dialog-content').parents('div.dialog-main-wrapper').children('div.dialog-close-button').css("top","30px");
    	$('#narrowNetworkModal.dialog-content').parents('div.dialog-main-wrapper').children('div.dialog-content-wrap').children('div.dialog-button-holder').remove();
    	if(urlProtocol == urlProtocolNonSecure){
        	$('#narrowNetworkModal.dialog-content').parents('div.dialog-main-wrapper').children('div.dialog-content-wrap').css("background-color","#ffffff");
        	$('#narrowNetworkModal.dialog-content').parents('div.dialog-main-wrapper').children('div.dialog-content-wrap').css("border-color","#D1D1D1");
        	$('#narrowNetworkModal.dialog-content').parents('div.dialog-main-wrapper').children('div.dialog-content-wrap').css("border-style","solid");
        	$('#narrowNetworkModal.dialog-content').parents('div.dialog-main-wrapper').children('div.dialog-content-wrap').css("border-width","2px");
        	$('#narrowNetworkModal.dialog-content').parents('div.dialog-main-wrapper').children('div.dialog-transparent-border').css("width","800px");
        	$('#narrowNetworkModal.dialog-content').css("border","0px");
        }
    	if(urlProtocol == urlProtocolSecure){
    		$('#narrowNetworkModal.dialog-content').parents('div.dialog-main-wrapper').children('div.dialog-close-button').css("left","741px");
        	$('#narrowNetworkModal.dialog-content').parents('div.dialog-main-wrapper').children('div.dialog-close-button').css("top","40px");
        	
    	}
    	$('.dialog-modal').width($(document).width());
        $('.dialog-modal').height($(document).height() + 50);
     });
}

function buildNarrowNetworkModalBox(title){
    $('#narrowNetworkModal').attr('title', title+'<br/><br/>');
    $('#narrowNetworkModal').attr('subtitle', '');
    $('#narrowNetworkModal').attr('dialogText', '');
    $('#narrowNetworkModal').doDialog({width: 750,modal:true, draggable:true, closeOnEscape:true},
    [{id:"btnCloseNarrowNetwork",value:'CLOSE', url:"javascript:closeNarrowNetworkModalBox();"}]);
    
    $("#btnClose2").click(function(){
        $('#narrowNetworkModal').trigger('hide');
    });
}

function closeNarrowNetworkModalBox(){
    if( $('#narrowNetworkModal')!=undefined){
		$('#narrowNetworkModal').trigger('hide');
	}
	else{
		window.close();
	}
}

function renderModelButtonForNonSecure(){
	//START CHANGES A9991-1450-RelevancySearchErrorMessage - n596307
	//if(urlProtocol == urlProtocolNonSecure){
		$('.dialog-content-wrap').css("background-color","#ffffff");
		$('.dialog-content-wrap').css("border-color","#D1D1D1");
		$('.gold_button_left').html('');
		$('.gold_button_left').css("background-image","none");
		$('.gold_button_right').css("background-image","none");
		$('.gold_button_right').html('');
		//$('.gold_button').css("background-image","url(/dse/assets/images/go_btn_center.jpg)");
		$('.gold_button').css("height","25px");
		$('.gold_button').css("width","60px");
		$('.dialog-title').css("font-size","15px");
		$('.dialog-title').css("color","#002776");
		$('.dialog-close-button').css("background","transparent url(/dse/cms/codeAssets/images/close.png) no-repeat top right");
		$('.dialog-close-button').css("height","25px");
		$('.dialog-close-button').css("width","25px");
	//}
}

function callFromDetails(){
	chk = true;
	var params = $.getUrlVars();
	/*-----START CHANGES P19791a Exchange August 2013-----*/
	var site_id = $.getUrlVar('site_id');
	$('#site_id').val(site_id);
	/*-----END CHANGES P19791a Exchange August 2013-----*/
	byName = $.getUrlVar('isHospitalFromDetails');
	if(byName == 'true'){
		var byName = $.getUrlVar('searchQuery');
		$('#searchQuery').val(byName);
		byName = $.getUrlVar('hospitalNavigator');
		$('#hospitalNavigator').val(byName);
		byName = $.getUrlVar('hospitalName');
		byName = decodeURIComponent(byName);
		byName = byName.replace(/\+/g," ");
		$('#hospitalNameFromDetails').val(byName);
		byName = $.getUrlVar('isHospitalFromDetails');
		$('#hospitalFromDetails').val(byName.toString());
	}
	byName = $.getUrlVar('officesLinkIsTrueDetails');
	if(byName == 'true'){
		var byName = $.getUrlVar('officeNavigator');
		$('#officeLocation').val(byName);
		byName = $.getUrlVar('name');
		byName = decodeURIComponent(byName);
		byName = byName.replace(/\+/g," ");
		$('#otherOfficeProviderName').val(byName);
		byName = $.getUrlVar('officesLinkIsTrueDetails');
		$('#officesLinkIsTrueDetails').val(byName.toString());
	}
	byName = $.getUrlVar('planProductCode');
	if (urlProtocol == urlProtocolNonSecure){
		$('#planCodeFromDetails').val(byName);
	}
	byName = $.getUrlVar('currentSelectedPlan');
	$('#currentSelectedPlan').val(byName);
	if(whyPressed == 'geo' ||(urlProtocol == urlProtocolSecure && $.getUrlVar('zipCode') == "")){
		byName = $.getUrlVar('currentZipCode');
	}
	else{
		byName = $.getUrlVar('zipCode');
	}
	$('#zipCode').val(byName);
	/*-- START CHANGES P23695a PCR 20792 May2016- PLAN DISPLAY - n596307 --*/
	//condition always true to fix the selected Plan issue, if need to revert replace 1 by 0
	if(1){
		byName = getDisplayNameForSelectedPlan(replaceSpecialCharCodes($.getUrlVar('planProductName')));
	}
	else{
		byName = $.getUrlVar('planProductName');
		byName = decodeURIComponent(byName);
		byName = byName.replace(/\+/g," ");
	}
	/*-- END CHANGES P23695a PCR 20792 May2016- PLAN DISPLAY - n596307 --*/
	$('#listPlanSelected').html(byName);
	changeFormat();
	if($('#planCodeFromDetails').val()!=null && $('#planCodeFromDetails').val()!=""){
		searchWithPlan($('#listPlanSelected').text(),$('#planCodeFromDetails').val())
		if (urlProtocol == urlProtocolNonSecure){
			$('#columnPlanSelected').css('display','block');
		}
		
	}
	else if($('#planCodeFromDetails').val() == ""){
		if($('#site_id').val() == 'medicare' || $.getUrlVar('site_id') == 'medicare'){
			searchWithOutStatePlan(noneText);
		}
		else{
			searchWithOutPlan();
		}
	}
	searchSubmit('true');
	$("#docfindSearchEngineForm").submit();
	/*-- START CHANGES P23695a PCR 20792 May2016- PLAN DISPLAY - n596307 --*/
	$('#plandisplay').show();
	/*-- END CHANGES P23695a PCR 20792 May2016- PLAN DISPLAY - n596307 --*/
	
}

function callFromResultsIPA(){
	chk = true;
	var params = $.getUrlVars();
	/*-----START CHANGES P19791a Exchange August 2013-----*/
	var site_id = $.getUrlVar('site_id');
	$('#site_id').val(site_id);
	/*-----END CHANGES P19791a Exchange August 2013-----*/
	var byName = $.getUrlVar('searchQuery');
	$('#searchQuery').val(byName);
	byName = $.getUrlVar('hospitalNavigator');
	$('#hospitalNavigator').val(byName);
	byName = $.getUrlVar('ipaNameForProvider');
	byName = decodeURIComponent(byName);
	byName = byName.replace(/\+/g," ");
	$('#ipaNameForProvider').val(byName);
	byName = $.getUrlVar('ipaId');
	$('#porgId').val(byName);
	byName = $.getUrlVar('planProductCode');
	if (urlProtocol == urlProtocolNonSecure){
		$('#planCodeFromDetails').val(byName);
	}
	byName = $.getUrlVar('currentSelectedPlan');
	$('#currentSelectedPlan').val(byName);
	if(whyPressed == 'geo' ||(urlProtocol == urlProtocolSecure && $.getUrlVar('zipCode') == "")){
		byName = $.getUrlVar('currentZipCode');
	}
	else{
		byName = $.getUrlVar('zipCode');
	}
	$('#zipCode').val(byName);
	byName = $.getUrlVar('isIpaFromResults');
	$('#ipaFromResults').val(byName.toString());
	/*-- START CHANGES P23695a PCR 20792 May2016- PLAN DISPLAY - n596307 --*/
	//condition always true to fix the selected Plan issue, if need to revert replace 1 by 0
	if(1){
		byName = getDisplayNameForSelectedPlan(replaceSpecialCharCodes($.getUrlVar('planProductName')));
	}
	else{
		byName = $.getUrlVar('planProductName');
		byName = decodeURIComponent(byName);
		byName = byName.replace(/\+/g," ");
	}
	/*-- END CHANGES P23695a PCR 20792 May2016- PLAN DISPLAY - n596307 --*/
	$('#listPlanSelected').html(byName);
	changeFormat();
	
	if($('#planCodeFromDetails').val()!=null && $('#planCodeFromDetails').val()!=""){
		searchWithPlan($('#listPlanSelected').text(),$('#planCodeFromDetails').val())
		if (urlProtocol == urlProtocolNonSecure){
			$('#columnPlanSelected').css('display','block');
		}
		
	}
	else if($('#planCodeFromDetails').val() == ""){
		if($('#site_id').val() == 'medicare' || $.getUrlVar('site_id') == 'medicare'){
			searchWithOutStatePlan(noneText);
		}
		else{
			searchWithOutPlan();
		}
	}
	/*-- START CHANGES P23695a PCR 20792 May2016- PLAN DISPLAY - n596307 --*/
	searchSubmit('true');
	$("#docfindSearchEngineForm").submit();
	$('#plandisplay').show();
	/*-- END CHANGES P23695a PCR 20792 May2016- PLAN DISPLAY - n596307 --*/
}

function callFromDetailsIPA(){
	chk = true;
	var params = $.getUrlVars();
	/*-----START CHANGES P19791a Exchange August 2013-----*/
	var site_id = $.getUrlVar('site_id');
	$('#site_id').val(site_id);
	/*-----END CHANGES P19791a Exchange August 2013-----*/
	var byName = $.getUrlVar('searchQuery');
	$('#searchQuery').val(byName);
	byName = $.getUrlVar('hospitalNavigator');
	$('#hospitalNavigator').val(byName);
	byName = $.getUrlVar('ipaNameForProvider');
	byName = decodeURIComponent(byName);
	byName = byName.replace(/\+/g," ");
	$('#ipaNameForProvider').val(byName);
	byName = $.getUrlVar('ipaId');
	$('#porgId').val(byName);
	byName = $.getUrlVar('planProductCode');
	if (urlProtocol == urlProtocolNonSecure){
		$('#planCodeFromDetails').val(byName);
	}
	byName = $.getUrlVar('currentSelectedPlan');
	$('#currentSelectedPlan').val(byName);
	if(whyPressed == 'geo' ||(urlProtocol == urlProtocolSecure && $.getUrlVar('zipCode') == "")){
		byName = $.getUrlVar('currentZipCode');
	}
	else{
		byName = $.getUrlVar('zipCode');
	}
	$('#zipCode').val(byName);
	byName = $.getUrlVar('isIpaFromDetails');
	$('#ipaFromDetails').val(byName.toString());
	/*-- START CHANGES P23695a PCR 20792 May2016- PLAN DISPLAY - n596307 --*/
	//condition always true to fix the selected Plan issue, if need to revert replace 1 by 0
	if(1){
		byName = getDisplayNameForSelectedPlan(replaceSpecialCharCodes($.getUrlVar('planProductName')));
	}
	else{
		byName = $.getUrlVar('planProductName');
		byName = decodeURIComponent(byName);
		byName = byName.replace(/\+/g," ");
	}
	/*-- END CHANGES P23695a PCR 20792 May2016- PLAN DISPLAY - n596307 --*/
	$('#listPlanSelected').html(byName);
	changeFormat();
	if($('#planCodeFromDetails').val()!=null && $('#planCodeFromDetails').val()!=""){
		searchWithPlan($('#listPlanSelected').text(),$('#planCodeFromDetails').val())
		if (urlProtocol == urlProtocolNonSecure){
			$('#columnPlanSelected').css('display','block');
		}
		
	}
	else if($('#planCodeFromDetails').val() == ""){
		if($('#site_id').val() == 'medicare' || $.getUrlVar('site_id') == 'medicare'){
			searchWithOutStatePlan(noneText);
		}
		else{
			searchWithOutPlan();
		}
	}
	/*-- START CHANGES P23695a PCR 20792 May2016- PLAN DISPLAY - n596307 --*/
	searchSubmit('true');
	$("#docfindSearchEngineForm").submit();
	$('#plandisplay').show();
	/*-- END CHANGES P23695a PCR 20792 May2016- PLAN DISPLAY - n596307 --*/
}

/* Start changes for Story 9791 */
function callFromGroupResults(){
	chk = true;
	var params = $.getUrlVars();
	/*-----START CHANGES P19791a Exchange August 2013-----*/
	var site_id = $.getUrlVar('site_id');
	$('#site_id').val(site_id);
	/*-----END CHANGES P19791a Exchange August 2013-----*/
	var byName = $.getUrlVar('searchQuery');
	$('#searchQuery').val(byName);
	byName = $.getUrlVar('groupnavigator');
	$('#groupnavigator').val(byName);
	byName = $.getUrlVar('groupNameForProvider');
	byName = decodeURIComponent(byName);
	byName = byName.replace(/\+/g," ");
	$('#groupNameForProvider').val(byName);
	byName = $.getUrlVar('planProductCode');
	if (urlProtocol == urlProtocolNonSecure){
		$('#planCodeFromDetails').val(byName);
	}
	byName = $.getUrlVar('currentSelectedPlan');
	$('#currentSelectedPlan').val(byName);
	if(whyPressed == 'geo' ||(urlProtocol == urlProtocolSecure && $.getUrlVar('zipCode') == "")){
		byName = $.getUrlVar('currentZipCode');
	}
	else{
		byName = $.getUrlVar('zipCode');
	}
	$('#zipCode').val(byName);
	byName = $.getUrlVar('isGroupFromResults');
	$('#groupFromResults').val(byName.toString());
	/*-- START CHANGES P23695a PCR 20792 May2016- PLAN DISPLAY - n596307 --*/
	//condition always true to fix the selected Plan issue, if need to revert replace 1 by 0
	if(1){
		byName = getDisplayNameForSelectedPlan(replaceSpecialCharCodes($.getUrlVar('planProductName')));
	}
	else{
		byName = $.getUrlVar('planProductName');
		byName = decodeURIComponent(byName);
		byName = byName.replace(/\+/g," ");
	}
	/*-- END CHANGES P23695a PCR 20792 May2016- PLAN DISPLAY - n596307 --*/
	$('#listPlanSelected').html(byName);
	changeFormat();
	if($('#planCodeFromDetails').val()!=null && $('#planCodeFromDetails').val()!=""){
		searchWithPlan($('#listPlanSelected').text(),$('#planCodeFromDetails').val())
		if (urlProtocol == urlProtocolNonSecure){
			$('#columnPlanSelected').css('display','block');
		}
		
	}
	else if($('#planCodeFromDetails').val() == ""){
		if($('#site_id').val() == 'medicare' || $.getUrlVar('site_id') == 'medicare'){
			searchWithOutStatePlan(noneText);
		}
		else{
			searchWithOutPlan();
		}
	}
	/*-- START CHANGES P23695a PCR 20792 May2016- PLAN DISPLAY - n596307 --*/
	searchSubmit('true');
	$("#docfindSearchEngineForm").submit();
	$('#plandisplay').show();
	/*-- END CHANGES P23695a PCR 20792 May2016- PLAN DISPLAY - n596307 --*/
}
function callFromGroupDetails(){
	chk = true;
	var params = $.getUrlVars();
	/*-----START CHANGES P19791a Exchange August 2013-----*/
	var site_id = $.getUrlVar('site_id');
	$('#site_id').val(site_id);
	/*-----END CHANGES P19791a Exchange August 2013-----*/
	var byName = $.getUrlVar('searchQuery');
	$('#searchQuery').val(byName);
	byName = $.getUrlVar('groupnavigator');
	$('#groupnavigator').val(byName);
	byName = $.getUrlVar('groupNameForProvider');
	byName = decodeURIComponent(byName);
	byName = byName.replace(/\+/g," ");
	$('#groupNameForProvider').val(byName);
	byName = $.getUrlVar('planProductCode');
	if (urlProtocol == urlProtocolNonSecure){
		$('#planCodeFromDetails').val(byName);
	}
	byName = $.getUrlVar('currentSelectedPlan');
	$('#currentSelectedPlan').val(byName);
	if(whyPressed == 'geo' ||(urlProtocol == urlProtocolSecure && $.getUrlVar('zipCode') == "")){
		byName = $.getUrlVar('currentZipCode');
	}
	else{
		byName = $.getUrlVar('zipCode');
	}
	$('#zipCode').val(byName);
	byName = $.getUrlVar('isGroupFromDetails');
	$('#groupFromDetails').val(byName.toString());
	/*-- START CHANGES P23695a PCR 20792 May2016- PLAN DISPLAY - n596307 --*/
	//condition always true to fix the selected Plan issue, if need to revert replace 1 by 0
	if(1){
		byName = getDisplayNameForSelectedPlan(replaceSpecialCharCodes($.getUrlVar('planProductName')));
	}
	else{
		byName = $.getUrlVar('planProductName');
		byName = decodeURIComponent(byName);
		byName = byName.replace(/\+/g," ");
	}
	/*-- END CHANGES P23695a PCR 20792 May2016- PLAN DISPLAY - n596307 --*/
	$('#listPlanSelected').html(byName);
	changeFormat();
	if($('#planCodeFromDetails').val()!=null && $('#planCodeFromDetails').val()!=""){
		searchWithPlan($('#listPlanSelected').text(),$('#planCodeFromDetails').val())
		if (urlProtocol == urlProtocolNonSecure){
			$('#columnPlanSelected').css('display','block');
		}
	}
	else if($('#planCodeFromDetails').val() == ""){
		if($('#site_id').val() == 'medicare' || $.getUrlVar('site_id') == 'medicare'){
			searchWithOutStatePlan(noneText);
		}
		else{
			searchWithOutPlan();
		}
	}
	/*-- START CHANGES P23695a PCR 20792 May2016- PLAN DISPLAY - n596307 --*/
	searchSubmit('true');
	$("#docfindSearchEngineForm").submit();
	$('#plandisplay').show();
	/*-- END CHANGES P23695a PCR 20792 May2016- PLAN DISPLAY - n596307 --*/
}

/* End changes for Story 9791 */

function showParNonParmsg()
{
	$('#NoParMsgID').show();
}

function showDirectionsModal()
{
if($('#mapDialogBox').length >0 && !($('#mapDialogBox').attr('class') == 'dialog-content')){
		$('#mapDialogBox').doDialogDefault({width:600, modal:false, draggable:true, closeOnEscape:true},[]);
}
}

function showFilterDialogBox(){
	/*-- START CHANGES P23695 Medicare Spanish Translation - n596307 --*/
	var buttonClearValue;
	var buttonSearchValue;
	if(site_id == 'medicare' && langPref == 'sp'){
		buttonClearValue = "Borrar";
		buttonSearchValue = "Buscar";
	}
	else{
		buttonClearValue = "Clear";
		buttonSearchValue = "Search";
	}
	/*-- END CHANGES P23695 Medicare Spanish Translation - n596307 --*/
	if($('#filterDialog').length >0 && !($('#filterDialog').attr('class') == 'dialog-content')){
		$('#filterDialog').doDialogDefault({width:350, modal:true, draggable:true, closeOnEscape:true},
				 [{id:"Clear", value:buttonClearValue, url:"", arrow:false},
				  {id:"Search", value:buttonSearchValue,url:"", arrow:false}
		]);
	}
}

function showParProvText(){
$(window).scrollTop($('#resultsDisclaimer').offset().top);
}

jQuery.fn.print = function(){
	// NOTE: We are trimming the jQuery collection down to the
	// first element in the collection.
	if (this.size() > 1){
		this.eq( 0 ).print();
		return;
	} else if (!this.size()){
		return;
	}
 
	// ASSERT: At this point, we know that the current jQuery
	// collection (as defined by THIS), contains only one
	// printable element.
 
	// Create a random name for the print frame.
	var strFrameName = ("printer-" + (new Date()).getTime());
 
	// Create an iFrame with the new name.
	var jFrame = $( "<iframe name='" + strFrameName + "'>" );
 
	// Hide the frame (sort of) and attach to the body.
	jFrame
		.css( "width", "1px" )
		.css( "height", "1px" )
		.css( "position", "absolute" )
		.css( "left", "-9999px" )
		.appendTo( $( "body:first" ) )
	;
 
	// Get a FRAMES reference to the new frame.
	var objFrame = window.frames[ strFrameName ];
 
	// Get a reference to the DOM in the new frame.
	var objDoc = objFrame.document;
 
	// Grab all the style tags and copy to the new
	// document so that we capture look and feel of
	// the current document.
 
	// Create a temp document DIV to hold the style tags.
	// This is the only way I could find to get the style
	// tags into IE.
	var jStyleDiv = $( "<div>" ).append(
		$( "style" ).clone()
		);
 
	// Write the HTML for the document. In this, we will
	// write out the HTML of the current element.
	objDoc.open();
	objDoc.write( "<!DOCTYPE html PUBLIC \"-//W3C//DTD XHTML 1.0 Transitional//EN\" \"http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd\">" );
	objDoc.write( "<html>" );
	objDoc.write( "<body>" );
	objDoc.write( "<head>" );
	objDoc.write( "<title>" );
	objDoc.write( document.title );
	objDoc.write( "</title>" );
	objDoc.write( jStyleDiv.html() );
	objDoc.write( "</head>" );
	objDoc.write( this.html() );
	objDoc.write( "</body>" );
	objDoc.write( "</html>" );
	objDoc.close();
 
	// Print the document.
	objFrame.focus();
	objFrame.print();
 
	// Have the frame remove itself in about a minute so that
	// we don't build up too many of these frames.
	setTimeout(
		function(){
			jFrame.remove();
		},
		(60 * 1000)
		);
}

function adjustModalLayerDimentions(){
	$('.dialog-modal').width($(document).width());
    $('.dialog-modal').height($(document).height() + 50);
}


function rd_medical_plan_redirect(obj){
	/*-- START CHANGES P20751b ACO Branding - n596307 --*/
	var plan = obj.value;
	if($('#site_id').val()!=null && $('#site_id').val()!=undefined && $('#site_id').val() == "inova"){	
		if(plan== "INEPO|Innovation Health EPO" || plan == "IMPPO|Innovation Health PPO 1" || plan == "IMPPO|Innovation Health PPO 2" || plan == "IMPPO|Innovation Health HSA HDP" || plan== "IMPPO|Innovation Health HRA HDP")
		{
			location.href="javascript:popUp('/docfind/cms/html/inova_plan.html')";
		}
	}
	else if(plan == "showAllPlans" || plan == "showOnlyGeoPlans"){
		handleTogglePlansLinkFunctionality(plan);
	}
	/*-- END CHANGES P20751b ACO Branding - n596307 --*/
}

function ShowAllFlagsInPopUp(index){	
    var dialogTextVal = $("#allFlags_"+index).html();
    
    $('#allFlagsDialogbox').html(dialogTextVal);	
    
    $('#allFlagsDialogbox').trigger('show')
    
    $("#btnCloseAllFlags").click(function(){
    	$('#allFlagsDialogbox').trigger('hide');
   });
    
}

function prevAnnCookie(){
	NIT.PAMainWindow=true;
	NIT.ClearPACookie();
	return true;
}

function prePopulateZipForSecure(){
	if(urlProtocol == urlProtocolSecure){
		var locationAddress =  window.location.href;
		if(locationAddress.indexOf('/search')> 0 && (!(locationAddress.indexOf('#markPage')> 0)) && (!(locationAddress.indexOf('/detail')> 0)) &&($.getUrlVar('isGroupFromDetails')!='true' && $.getUrlVar('isGroupFromResults')!='true' && $.getUrlVar('isIpaFromDetails')!='true' && $.getUrlVar('isIpaFromResults')!='true' && $.getUrlVar('isHospitalFromDetails')!='true' && $.getUrlVar('officesLinkIsTrueDetails')!='true')) {
			changeFormatGeoLocation();
			if(!($('#restUser').val() || $('#guestUser').val())){
				$('#hl-autocomplete-search-location').val($('#memberZipCode').val());
			}
			$('#geoSearch').val($('#memberZipCode').val());
		}
	}
}

/*P08-8423a Sprint08-2013 - Story10133 Changes Start*/ 
var chkTOSmodel = true;
function ShowTOSInPopUp(index){
	var providername = $("#TOS_Name_"+index).html();
	if(chkTOSmodel){
		buildTOSAlertBox(providername);
		$('#TOSDialogbox').trigger('show');
		chkTOSmodel = false;
	}else{
		var divTitle = document.getElementById("diaTitle");
		if(divTitle != null)
			{
			divTitle.innerHTML = providername;
			}
		$('#TOSDialogbox').trigger('show');
	}	
    var dialogTextVal = $("#TOS_"+index).html();
    $('#TOSDialogbox').html(dialogTextVal);
    $('#TOSDialogbox').trigger('show');
    $('.dialog-modal').width($(document).width());
    $('.dialog-modal').height($(document).height() + 50);
    
    	
}

function buildTOSAlertBox(providername){
	
		$('#TOSDialogbox').attr('title', providername);
	    $('#TOSDialogbox').attr('subtitle','Types Of Service');
	    $('#TOSDialogbox').attr('dialogText','You can narrow your search to a particular type of service using the Type pull-down on the search screen.');
		/*$('#TOSDialogbox').doDialogDefault({width: 360, modal:true, draggable:true, closeOnEscape:true},
		[{id:'btnCloseTOSbox',value:'CLOSE', "url":"javascript:closeModalBoxWithId('#TOSDialogbox')"}],'TOSDialogbox');*/
	    $('#TOSDialogbox').doDialogflag({width: 360, modal:true, draggable:true, closeOnEscape:true},
	     [{id:"btnClose",value:'CLOSE', url:"javascript:closeDialogrd();", arrow:true}]);
	    
	    $("#btnClose").click(function(){
	    	$('#TOSDialogbox').trigger('hide');
	   });
}

function closeDialogrd()
{
	$('#TOSDialogbox').trigger('hide');
}

/*P08-8423a Sprint08-2013 - Story10133 Changes End*/


function whereValFunction(){
	if($('#hl-autocomplete-search-location').val() != ghostTextWhereBox){
		if(trim($("#hl-autocomplete-search-location").val()) != '' && trim($("#geoMainTypeAheadLastQuickSelectedVal").val())!=trim($('#hl-autocomplete-search-location').val())){
			var str = $(".typeAheadURLOrignal").html();
			if(str!=null && str!=''){
				if(validateZipCode($('#hl-autocomplete-search-location').val())){
					str+="&zipcode="+$('#hl-autocomplete-search-location').val();
		    			str+="&radius=25";
				}
				else {
					$('#QuickZipcode').val("");
					$('#QuickCoordinates').val("");
					$('#stateCode').val("");
					str+="&where="+$('#hl-autocomplete-search-location').val();
				}
				$(".typeAheadURL").html(str);
			}
		}
	}else{
		$(".typeAheadURL").html($(".typeAheadURLOrignal").html());
	}
}

function searchQueryZipValFun(){
//Blank out the zip code in every case before we hit trigger search. 
	//Fix for defect : DEF0200725601
    $('#zipCode').val('');	
    //End of fix for DEF0200725601

	if($('#hl-autocomplete-search-location').val() != ghostTextWhereBox){
		if($('#hl-autocomplete-search-location').val()!=null && trim($('#hl-autocomplete-search-location').val())!='' && trim($('#hl-autocomplete-search-location').val())!= undefined){
			$('#geoSearch').val(trim($('#hl-autocomplete-search-location').val()));
		}
	}
      if($('#geoSearch').val() !=null && trim($('#geoSearch').val())!=''){
				if(validateZipCode($('#geoSearch').val())){
					$('#zipCode').val(($.trim($('#geoSearch').val().toString())).substring(0,5));
				}
			}
}

function isAlpha(xStr){  
    var regEx = /^[a-zA-Z\-\ ]+$/;  
    return xStr.match(regEx);  
}

function leftDistanceSearch()
{
        var prevDist='';
        var distance ='';
        $('#narrowSearchResultsSelect_prim li').bind('mousedown', function(evt) {
                prevDist = $('#withinMilesValue').text();
        });

        $('#narrowSearchResultsSelect_prim li').bind('mouseup', function(evt) {
                distance = $(".narrowSearchResultsSelect_select").attr("value");
                if (prevDist != distance){
                        whyPressed = 'geo';
				   $("#pagination").val("");
                        goClick();
                }
        });
}


function ondebugClick(){
	var hiddenurl = $('#hiddenSearchUrlDataInd').text();
	var output = hiddenurl.substring(hiddenurl.indexOf('?')+1);		
	var paramList = output.split("&"); 
	var displayinfo="";
	var i;
	for (i = 0; i < paramList.length; i++) {
		if(paramList[i]!= undefined && paramList[i].length>0){
			if(paramList[i].indexOf('¢er')>0){
				var bigText = paramList[i];
				var index=bigText.indexOf('¢er');
				var centerinfo = bigText.substring(index);
				bigText = bigText.substring(0,index);

				displayinfo = displayinfo + bigText +"\n";
				displayinfo = displayinfo + centerinfo +"\n";
			}else{
				displayinfo = displayinfo + paramList[i] +"\n";
			}
		}
	}
	alert(displayinfo);
}

function displayHiddenBlock(){
	$('#hiddenSearchUrlDataInd').css('display','block');
}

var groupIpaCapModalInd = true;
function showGrpIpaCapModalBox(id,medDen){
	if($('#showIpaGrpNameCapModalBox'+id).val() == 'true'){
		if(groupIpaCapModalInd){
			buildGroupIpaBox(id,medDen);
			groupIpaCapModalInd=false;
		}
		var dialogTextVal = $("#groupIpaNameCappOff_"+id).html();
		$('#groupIpaCapModalBox').html(dialogTextVal);
		$('#groupIpaCapModalBox').trigger('show');
	}
}

function buildGroupIpaBox(id,medDen){
	if(medDen != undefined && medDen != null && medDen != '' && medDen == "MED"){
		$('#groupIpaCapModalBox').attr('title', 'Make My Primary Doctor');
	}
	else if(medDen != undefined && medDen != null && medDen != '' && medDen == "DEN"){
		$('#groupIpaCapModalBox').attr('title', 'Make My Primary Dentist');
	}
	$('#groupIpaCapModalBox').attr('subtitle', '');
	$('#groupIpaCapModalBox').doDialogDefault({width: 300, modal:true, draggable:true, closeOnEscape:true},
			[{id:'btnCancelGroupIpa',value:'CANCEL', "url":"javascript:void(0);"},
			 {id:'btnContinueGroupIpa',value:'CONTINUE', "url":"javascript:void(0);"}],'groupIpaCapModalBox');
	
	$("#btnCancelGroupIpa").click(function(){
		$('#groupIpaCapModalBox').trigger('hide');
	  });
	
	$("#btnContinueGroupIpa").click(function(){
		if($("input[@name=groupIpaNameCappOffMapRadio_"+id+"]:checked").attr('id') != undefined){
			var groupIpaNameCappOffId = ($("input[@name=groupIpaNameCappOffMapRadio_"+id+"]:checked").attr('id')).toString();
			if(groupIpaNameCappOffId != undefined && groupIpaNameCappOffId != null && trim(groupIpaNameCappOffId) != ''){
				if(medDen != undefined && medDen != null && medDen != '' && medDen=="MED"){
					medformSubmit(id);
				}
				else if(medDen != undefined && medDen != null && medDen != '' && medDen=="DEN"){
					denformSubmit(id);
				}
			}
		}
	  });
	
	if ($('.dialog-close-button_groupIpaCapModalBox').length > 0) {
		$('.dialog-close-button_groupIpaCapModalBox').click(function() {
			$('#groupIpaCapModalBox').trigger('hide');
		});
	}
	return false;
}

var groupIpaCapModalDetailsInd = true;
function showGrpIpaCapModalBoxDetails(medDen){
	if($('#showIpaGrpNameCapModalBoxDetails').text() == 'true'){
		if(groupIpaCapModalDetailsInd){
			buildGroupIpaBoxDetails(medDen);
			groupIpaCapModalDetailsInd=false;
		}
		var dialogTextVal = $("#groupIpaNameCappOffDetails").html();
		$('#groupIpaCapModalBox').html(dialogTextVal);
		$('#groupIpaCapModalBox').trigger('show');
	}
}

function buildGroupIpaBoxDetails(medDen){
	if(medDen != undefined && medDen != null && medDen != '' && medDen == "MED"){
		$('#groupIpaCapModalBox').attr('title', 'Make My Primary Doctor');
	}
	else if(medDen != undefined && medDen != null && medDen != '' && medDen == "DEN"){
		$('#groupIpaCapModalBox').attr('title', 'Make My Primary Dentist');
	}
	$('#groupIpaCapModalBox').attr('subtitle', '');
	$('#groupIpaCapModalBox').doDialogDefault({width: 300, modal:true, draggable:true, closeOnEscape:true},
			[{id:'btnCancelGroupIpa',value:'CANCEL', "url":"javascript:void(0);"},
			 {id:'btnContinueGroupIpa',value:'CONTINUE', "url":"javascript:void(0);"}],'groupIpaCapModalBox');
	
	$("#btnCancelGroupIpa").click(function(){
		$('#groupIpaCapModalBox').trigger('hide');
	  });
	
	$("#btnContinueGroupIpa").click(function(){
		if($("input[@name=groupIpaNameCappOffMapRadioDetails]:checked").attr('id') != undefined){
			var groupIpaNameCappOffIdDetails = ($("input[@name=groupIpaNameCappOffMapRadioDetails]:checked").attr('id')).toString();
			if(groupIpaNameCappOffIdDetails != undefined && groupIpaNameCappOffIdDetails != null && trim(groupIpaNameCappOffIdDetails) != ''){
				if(medDen != undefined && medDen != null && medDen != '' && medDen=="MED"){
					medformSubmitDetailPage();
				}
				else if(medDen != undefined && medDen != null && medDen != '' && medDen=="DEN"){
					denformSubmitDetailPage();
				}
			}
		}
	  });
	
	if ($('.dialog-close-button_groupIpaCapModalBox').length > 0) {
		$('.dialog-close-button_groupIpaCapModalBox').click(function() {
			$('#groupIpaCapModalBox').trigger('hide');
		});
	}
	return false;
}

function mainTypeAheadThrdColValSelectionDecider(){
	if($('#searchQuery').val() !=undefined && $('#searchQuery').val() != null && $('#searchQuery').val() !=""){
		if($('#searchQuery').val() != $('#mainTypeAheadSelectionVal').val()){
			$('#quickSearchTypeMainTypeAhead').val('');
			$('#quickCategoryCode').val('');
		}
		
		if($('#searchQuery').val() != $('#thrdColSelectedVal').val()){
			$('#quickSearchTypeThrCol').val('');
			/*-----START CHANGES A9991-1034 A615A-1094 Nov 2013-----*/
			$('#ioeqSelectionInd').val('');
			$('#ioe_qType').val('');
		}
	}
}

/* Start changes for SR1317 - Aug 2013 */
function showCalHmoPopUp(){
	var locationAddress = window.location.href;
	if(locationAddress.indexOf("markPage") != -1){
		populateUrlParameters();
		var product = $.getUrlVar('publicPlan');
		var searchQuery = $('#searchQuery').val();
		var ucRole = $('#ucClassificationCodeDiv').text();
		var secureProd = $('#secureMedPlan').text();
		if(((ucRole != null && ucRole == "true") || (searchQuery.toLowerCase() == "Urgent Care Centers".toLowerCase())) && 
				((product == "HRHMO" ||  product == "MEHMO" || product == "COHMO" || product == "MHMO" || 
				 product == "HRHMO" ||  product == "QPOS" || product == "Mexico" || product == "VPHMO") || 
				 (secureProd == "HRHMO" ||  secureProd == "MEHMO" || secureProd == "COHMO" || secureProd == "MHMO" || 
				 secureProd == "HRHMO" ||  secureProd == "QPOS" || secureProd == "Mexico" || secureProd == "VPHMO") )){
			/*-- START CHANGES P23695 Medicare Spanish Translation - n596307 --*/
			if(site_id == 'medicare' && langPref == 'sp'){
				URL = "/dse/cms/codeAssets/html/es/urgentcare_ca.html"; 	
			}
			else{
				URL = "/dse/cms/codeAssets/html/static/urgentcare_ca.html"; 	
			}
			/*-- END CHANGES P23695 Medicare Spanish Translation - n596307 --*/
			var windowName='popup';
			var winOpts = 'width=950,height=220,scrollbars=no,resizable=no,toolbar=yes';
			window.name='INDEX';
			aWindow=window.open(URL,windowName,winOpts);
			aWindow.focus();			
		}
	}

}
/* End changes for SR1317 - Aug 2013 */

/*-----START CHANGES P19791a Exchange August 2013-----*/
function searchByPlanQHP(){
if($('input:radio[id=filterPlanQHP]').is(':checked')){
	var productCode = $('input:radio[id=filterPlanQHP]:checked').val();
	if(productCode != null && productCode != ""){
		$('#modalSelectedPlan').val(productCode);
		filteredCode = productCode;
	}
	else if(filteredCode != null && filteredCode != ""){
		$('#modalSelectedPlan').val(filteredCode);
	}
	else{
		$("#modalSelectedPlan").val('');
	}
	}
}
/*-----END CHANGES P19791a Exchange August 2013-----*/


/*-----START CHANGES ZipLimit Defect August 2013-----*/
function geoZipVerificationForInZipFun(){
	if(($('#geoSearch').val() == $('#zipCode').val()) && $('#sendZipLimitInd').val()!= undefined && $('#sendZipLimitInd').val() == 'true'){
		$('#sendZipLimitInd').val('true');
	}
	/*else if($('#site_id').val()!=null && $('#site_id').val()!=undefined && $('#site_id').val()!='' && $('#site_id').val() == 'princeton'
			&& $('#geoSearch').val() == $('#zipCode').val() && $('#distance').val() != '' && $('#distance').val() == "0"){
preValOfGeoBox = $('#geoSearch').val();
		$('#distance').val('1');		
$('#sendZipLimitInd').val('true');
	}*/
	else{
		$('#sendZipLimitInd').val('');
	}
	/* SR 1385 Changes start*/
	if(preValOfGeoBox!=$('#geoSearch').val()){
		$('#distance').val('0');
	}
      /* SR 1385 Changes end*/
}

/*-----END CHANGES ZipLimit Defect August 2013-----*/

/*Start SR1326 Aug13 changes*/
function popUpLeapFrog(URL)
{
	var windowName='popup';
	var winOpts = 'width=800,height=600,scrollbars=yes,resizable=yes,toolbar=yes,overflow=scroll';
	window.name='INDEX';	
	aWindow=window.open(URL,windowName,winOpts);
	aWindow.focus();
}

function popUpLeapFrogHtml(URL)
{
	var windowName='popup';
	var winOpts = 'width=600,height=310,scrollbars=yes,resizable=yes,toolbar=yes,overflow=scroll';
	window.name='INDEX';	
	aWindow=window.open(URL,windowName,winOpts);
	aWindow.focus();
}
/*End SR1326 Aug13 changes*/

/************************************************************************************************************
											GENERIC FUNCTIONS END HERE
************************************************************************************************************/
function hideTransitionModal()
{
	
		$('#nwTransitionMessage').trigger('hide');				    				
	
}

function triggerTransitionModal(){
	
	$('#nwTransitionMessage.dialog-content').parents('div.dialog-main-wrapper').children('div.dialog-content-wrap').children('div.dialog-title').html('<b>Alert</b>');
	renderModelButtonForNonSecure();
	var napHeight = $('#napWarningDialog.dialog-content').parents('div.dialog-main-wrapper').children('div.dialog-transparent-border').height();
	$('#napWarningDialog.dialog-content').parents('div.dialog-main-wrapper').children('div.dialog-transparent-border').css("height",napHeight + 2);
	$('#nwTransitionMessage').trigger('show');
}
/*-----START CHANGES A9991-1034 A615A-1094 Nov 2013-----*/
function setIOEQparameter( param,  value){
	if($(param)!=undefined)
		{
			$(param).val(value);
		}
}

/* Start changes for P19134a November release 2013 */
function rendersortDropdown(){	

	var currentSortOrder ='';
	var prevSortOrder = '';
       /*start changes for 1385*/
	if ($('#withinMilesValue').text() == '0'){		
		$('#hide_distace').hide();
		$('#narrowSearchResultsSelectDiv').hide();
	}else{
		$('#hide_distace').show();
		$('#narrowSearchResultsSelectDiv').show();
	} 
	/*End changes for 1385*/

	$('#bestResultsSelect_prim li').bind('mousedown', function(evt) {
       prevSortOrder = $('#sortOrder').val();
	});

	$('#bestResultsSelect_prim li').bind('mouseup', function(evt) {

		currentSortOrder = $(".bestResultsSelect_select").attr("value");
        if (prevSortOrder != currentSortOrder){
                whyPressed = 'geo';
                goClick();
        }
	});

	$('#otherResultsSelect_prim li').bind('mousedown', function(evt) {
       prevSortOrder = $('#sortOrder').val();
	});

	$('#otherResultsSelect_prim li').bind('mouseup', function(evt) {
		currentSortOrder = $(".otherResultsSelect_select").attr("value");
		if (prevSortOrder != currentSortOrder){
                whyPressed = 'geo';
                goClick();
        }
	});
}
/* End changes for P19134a November release 2013 */
/* P20488a changes start for error pop up */
function docFindShowOrHideHint(textFocus)
{
if(textFocus == 1)
{
	/*-- START CHANGES P23695 Medicare Spanish Translation - n709197 --*/
	
	var hintMsg = $('#whatBoxErrMsgDiv').html();
	/*-- START CHANGES P23695 Medicare Spanish Translation - n709197 --*/
	$('#contextHelpBoxDialog').html(hintMsg);
	$('#warning_msg').show();
	$("#contextHelpBoxDialog").show();
}
}
/* P20488a changes End for error pop up */

/* P20488 - 1231 changes start */
function addGhostWhatText(){
	var text = $('#hl-autocomplete-search').val();
	if(text == "" && text != ghostTextWhatBox){
		$('#hl-autocomplete-search').val(ghostTextWhatBox);
		$('.hl-autocomplete .hl-search-box .hl-searchbar .hl-searchbar-input').css('color','#BCBEC0');
		$('.hl-autocomplete .hl-search-box .hl-searchbar .hl-searchbar-input').css('font-style','italic');
	}	
}
function addGhostGeoText(){
	var text = $('#hl-autocomplete-search-location').val();
	if(text == "" && text != ghostTextWhereBox){
		$('#hl-autocomplete-search-location').val(ghostTextWhereBox);
		$('.hl-autocomplete-location-textBox .hl-autocomplete-location-box .hl-autocomplete-locationbar .hl-searchbar-input-location').css('color','#BCBEC0');
		$('.hl-autocomplete-location-textBox .hl-autocomplete-location-box .hl-autocomplete-locationbar .hl-searchbar-input-location').css('font- style','italic');
	}	
}

/*-- START CHANGES P20751b ACO Branding - n596307 --*/
function addGhostGeoColumnNoText(){
	var text = $('#hl-no-location-autocomplete-search').val();
	if(text == "" && text != ghostTextWhereBox){
		$('#hl-no-location-autocomplete-search').val(ghostTextWhereBox);
		$('.hl-no-location-textBox .hl-no-location-box .hl-no-locationbar .hl-no-location-searchbar-input').css ('color','#BCBEC0');
		$('.hl-no-location-textBox .hl-no-location-box .hl-no-locationbar .hl-no-location-searchbar-input').css('font- style','italic');
	}	
}
/*-- END CHANGES P20751b ACO Branding - n596307 --*/

function addGhostGeoColumnText(){
	var text = $('#hl-location-autocomplete-search').val();
	if(text == "" && text != ghostTextWhereBox){
		$('#hl-location-autocomplete-search').val(ghostTextWhereBox);
		$('.hl-location-textBox .hl-location-box .hl-locationbar .hl-location-searchbar-input').css ('color','#BCBEC0');
		$('.hl-location-textBox .hl-location-box .hl-locationbar .hl-location-searchbar-input').css('font- style','italic');
	}	
}

function displayErrorLocationPopup(){
	/*-- START CHANGES P23695 Medicare Spanish Translation - n709197 --*/
	$('#locationDialogBox.dialog-content').parents('div.dialog-main-wrapper').children('div.dialog-content-wrap').css({ 'background-color': '#FFFFFF' });;
	$('#locationDialogBox.dialog-content').parents('div.dialog-main-wrapper').children('div.dialog-content-wrap').children('div.dialog-title').text(tellUsYourLocation).css({ 'font-weight': 'bold', 'color': '#7d3f98', 'font-size': '18pt' });;
	
	var $title=$('#locationDialogBox.dialog-content').parents('div.dialog-main-wrapper').children('div.dialog-content-wrap').children('div.dialog-title');
	
	$('#locationDialogBox').html('<table id=locationTable><tr><td id="">' +
	'<tr><td colspan = 2 ><br/><span style="font-size:13.5px;color:#D31E11">'+hlLocationPopUpErrorMsg+'</span></td></tr><tr><td><img style="position:relative;top:5px;" src="/dse/assets/images/error_rd.jpg" alt="Error detected. Enter a location to fix the error." /></td><td id="locationTypeAheadBox">' + $('#includeTALocScript').html() + '<div class="hl-location-textBox"></div></td></tr></table>');
	/*-- END CHANGES P23695 Medicare Spanish Translation - n709197 --*/
	$('#cancelWHLocCriteria').click(function(){
		$('#locationDialogBox').trigger('hide');
		$('#ioe_qType').val('');
		/* start changes for MS SR 1438 Aug 2015*/
		$('#suppressFASTDocCall').val(false);
		/* end changes for MS SR 1438 Aug 2015*/
		return false;
	});
	
	$('#searchWHLocCriteria').bind('click',function(event){
		/*Start changes for type ahead location*/
		if(trim($('#hl-location-autocomplete-search').val()) == "" || trim($('#hl-location-autocomplete-search').val()) == ghostTextWhereBox){
			$('#locationDialogBox').trigger('hide');
			displayErrorLocationPopup();
		}
		else if((trim($('#hl-autocomplete-search-location').val())) != (trim($('#hl-location-autocomplete-search').val()))){
			if((trim($('#hl-autocomplete-search-location').val())) != (trim($('#hl-location-autocomplete-search').val()))){
                        //$('#hl-autocomplete-search').val(searchTerm);
                        //$('#thrdColSelectedVal').val(searchTerm);
				changeFormatGeoLocation();
				$('#hl-autocomplete-search-location').val($('#hl-location-autocomplete-search').val());
			}
			$('.hl-searchbar-button').click();
			$('#locationDialogBox').trigger('hide');
		}
		/*End changes for type ahead locations*/   
		 else{
			$('#hl-autocomplete-search').val(searchTerm);
			$('#thrdColSelectedVal').val(searchTerm);
			$('.hl-searchbar-button').click();
			$('#locationDialogBox').trigger('hide');
		}
		return false;
	});
	
	renderFilterUIForNonSecure();
	$('#locationDialogBox').trigger('show');
      $('.dialog-modal').width($(document).width());
      $('.dialog-modal').height($(document).height() + 50);
	$('a#searchWHLocCriteria').children('table').children('tbody').children('tr').children('td.gold_button').css("position","relative");
	$('a#cancelWHLocCriteria').children('table').children('tbody').children('tr').children('td.gold_button').css("position","relative");
	var transHeight = $('#locationDialogBox.dialog-content').parents('div.dialog-main-wrapper').children('div.dialog-content-wrap').height();
	$('#locationDialogBox.dialog-content').parents('div.dialog-main-wrapper').children('div.dialog-transparent-border').css("height",transHeight+32);
}
/* P20488 - 1231 changes end */

/* Start Changes P20448a(A9991-1225) - Mar 14 release */
function showPrintDirectoryDialogBox(){	
	$('#printPDButton').unbind();
	
	$('#printDirectoryDialogBox.dialog-content').parents('div.dialog-main-wrapper').children('div.dialog-content-wrap').children('div.dialog-title').text('Print a Provider Directory').css({ 'font-weight': 'bold', 'color': '#7d3f98', 'font-size': '18pt' });;
	var $title=$('#printDirectoryDialogBox.dialog-content').parents('div.dialog-main-wrapper').children('div.dialog-content-wrap').children('div.dialog-title');
		
	$('#printDirectoryDialogBox').html('<table id=locationTable><tr><td id="">' +
			'<tr><td><br/>Select the Print Directory button below to continue.  You will be asked to provide your search criteria again.</td></tr><tr></td></tr></table>');
		
	$('#cancelPDButton').click(function(){
		$('#printDirectoryDialogBox').trigger('hide');		
		return false;
	});		
	
	$('#printPDButton').click(function(){
		openPrintPD('/docfind/home.do?site_id=docfind&langpref=en&tabKey=tab5&fromDse=fromDse');
		$('#printDirectoryDialogBox').trigger('hide');			
		return false;
	});	
	
	renderFilterUIForNonSecure();
	
	$('#printDirectoryDialogBox').trigger('show');
      $('.dialog-modal').width($(document).width());
      $('.dialog-modal').height($(document).height() + 50);      
	$('a#printPDButton').children('table').children('tbody').children('tr').children('td.gold_button').css("position","relative");
	$('a#cancelPDButton').children('table').children('tbody').children('tr').children('td.gold_button').css("position","relative");
	var transHeight = $('#printDirectoryDialogBox.dialog-content').parents('div.dialog-main-wrapper').children('div.dialog-content-wrap').height();
	$('#printDirectoryDialogBox.dialog-content').parents('div.dialog-main-wrapper').children('div.dialog-transparent-border').css("height",transHeight+32);
}
/* End Changes P20448a(A9991-1225) - Mar 14 release */

/* P20941a August 2014 - Coventry Integration Medicare Advantage High Value  Networks - Rohit : START */
function addMedicareSiteIdtoURL(selPlanValue){
	var queryParameters = {}, queryString = location.search.substring(1),
    re = /([^&=]+)=([^&]*)/g, m;
	while (m = re.exec(queryString)) {
	    queryParameters[decodeURIComponent(m[1])] = decodeURIComponent(m[2]);
	}
	queryParameters['site_id'] = 'medicare';
	if(selPlanValue!=undefined && selPlanValue!=null && selPlanValue!=''){
		queryParameters['planStatusSelected'] = selPlanValue;
	}
	location.search = $.param(queryParameters);
}
/* P20941a August 2014 - Coventry Integration Medicare Advantage High Value  Networks - Rohit : END */
/*-- Start changes SR1347 Sep2014 - N204183 --*/
function prefillExternalSearchTypeAndGeoSearch(){
	populateUrlParameters();
	var externalSearchType = document.getElementById("externalSearchType");
	var stateToBePrefilled=$('#stateToBePrefilled').html();
	if(externalSearchType != undefined && externalSearchType.innerHTML != null && externalSearchType.innerHTML != ''){
		if($('#hl-autocomplete-search').val()!= undefined){
			$('#hl-autocomplete-search').val(externalSearchType.innerHTML);
			$('.hl-autocomplete .hl-search-box .hl-searchbar .hl-searchbar-input').css('color','#000000');
			$('.hl-autocomplete .hl-search-box .hl-searchbar .hl-searchbar-input').css('font-style','normal');
		}
		$('#thrdColSelectedVal').val(externalSearchType.innerHTML);
		$('#searchTypeThrCol').val("byProvType");
		$('#quickSearchTypeThrCol').val("byProvType");
		$('#searchQuery').val(externalSearchType.innerHTML);
	}
	if(stateToBePrefilled!=null && trim(stateToBePrefilled) != ""){
	var externalZipCode = document.getElementById("externalZipCode");
	if(externalZipCode != undefined && externalZipCode.innerHTML != null && externalZipCode.innerHTML != ''){
		if($('#hl-autocomplete-search-location').val()!= undefined){
			$('#hl-autocomplete-search-location').val(externalZipCode.innerHTML);
			$('.hl-autocomplete-location-textBox .hl-autocomplete-location-box .hl-autocomplete-locationbar .hl-searchbar-input-location').css('color','#000000');
			$('.hl-autocomplete-location-textBox .hl-autocomplete-location-box .hl-autocomplete-locationbar .hl-searchbar-input-location').css('font-style','normal');
		}
	}
}
}
/*-- End changes SR1347 Sep2014 - N204183 --*/
function displayRxFauxOnPlanSelection(searchTerm){
	searchWithFauxRowPlan($('#modal_aetna_plans :selected').text());
	$('#quickSearchTypeThrCol').val('byProvType');
	changeFormat();
	planTypeForPublic = '';
	$('#showNoPlans').text('true');
	$('#suppressFASTCall').val('true');
	$('#suppressFASTDocCall').val('false');
	$('#hl-autocomplete-search').val(searchTerm);
	$('#thrdColSelectedVal').val(searchTerm);
	$('.hl-searchbar-button').click();
	$('#planListDialogBox').trigger('hide');
}
/*-- Start changes P23046a SEP-2015 - N709197 --*/
function displayDentalFauxRwOnPlanSelection(searchTerm){
	searchWithFauxRowPlan($('#modal_aetna_plans :selected').text());
	var planVal = $('#modal_aetna_plans :selected').val();
	if (planVal != null){
		var pipe = planVal.indexOf('|');
		if (pipe > -1){
			planVal = trim(planVal.substring(0, pipe));
		}
	}
	$('#modalSelectedPlan').val(planVal);
	$('#quickSearchTypeThrCol').val('byProvType');
	changeFormat();
	planTypeForPublic = '';
	$('#showNoPlans').text('true');
	$('#suppressFASTCall').val('true');
	$('#suppressFASTDocCall').val('false');
	$('#hl-autocomplete-search').val(searchTerm);
	$('#thrdColSelectedVal').val(searchTerm);
	$('.hl-searchbar-button').click();
	$('#planListDialogBox').trigger('hide');
}

function searchWithFauxRowPlan(planSelected){
	$('#listPlanSelected').text(trimSpace(planSelected));
	$('#productPlanName').val(trimSpace(planSelected));
	$('#listPlanSelected').css('font-weight','bold');
	$('#columnPlanSelected').css('display','block');
	$('#plandisplay').show();
	$('#planChange').click(function(event){
		$('#planCodeFromDetails').val('');
		$('#productPlanName').val('');
		$('#suppressFASTCall').val('');
	    showStatePlanListModal();
		return false;
	});
}
/*-- End changes P23046a SEP-2015 - N709197 --*/
function setCookie(cname, cvalue, exmins) {
    if (exmins) {
		var date = new Date();
		//setting cookie for 5 minutes
		date.setTime(date.getTime()+(exmins*60*1000));
		var expires = "; expires="+date.toGMTString();
	}
	else {
		var expires = "";
	}
	document.cookie = cname+"="+cvalue+expires+"; path=/";
}
function getCookie(cname) {
    var name = cname + "=";
    var ca = document.cookie.split(';');
    for(var i=0; i<ca.length; i++) {
        var c = ca[i];
        while (c.charAt(0)==' ') c = c.substring(1);
        if (c.indexOf(name) != -1) return c.substring(name.length, c.length);
    }
    return "";
}
function eraseCookie(name) {
	setCookie(name,"",0);
}

function displayStatePopup(){
        // chkBuild=false;
        $('#planCodeFromDetails').val('');
        $('#productPlanName').val('');
        /*-- START CHANGES P20941a August2014 - Medicare Advantage - n596307 --*/
        if($('#switchForStatePlanSelectionPopUp')!=null && $('#switchForStatePlanSelectionPopUp')!=undefined 
                && $.trim($('#switchForStatePlanSelectionPopUp').text()) == 'ON'){
	        showStatePlanListModal();
        }
        /*-- END CHANGES P20941a August2014 - Medicare Advantage - n596307 --*/
        else if( directLinkSiteFound && planPrefillFlowSwitch != null && planPrefillFlowSwitch != 'true'){

        //don't show plan selection model box

        searchWithNoPlan();

}
        else{
                showPlanListModal();
        }
}

//content 1008
function searchWithDefaultPlan(){
	$('#modalSelectedPlan').val("ROPOS");	//shouldn't be hardcoded - todo later
	$('#columnPlanSelected').css('display','none');
	$('#plandisplay').hide();
	searchSubmit('true');
	$("#docfindSearchEngineForm").submit();
	if((chk  || $('#searchQuery').val()) && (!($('#hl-autocomplete-search').val() == ghostTextWhatBox))){
		$(document).off('click','.hl-searchbar-button');
	}
}
function changePlanFromSorryMessage(){
	$('#planCodeFromDetails').val('');
	$('#productPlanName').val('');
	/*-- START CHANGES SR1399 DEC'14 - n596307 --*/
	var planDisplayName = getCookie('planDisplayName');
	var externalPlanCode = getCookie('externalPlanCode');
	if(checkPlanPrefillFlow() || (planDisplayName != null && planDisplayName != '' && externalPlanCode != null && externalPlanCode != ''))
	{
		if(!($('#planFamilySwitch')!=null && $('#planFamilySwitch')!=undefined && $.trim($('#planFamilySwitch').text()) == 'ON')){
			if($("#modal_aetna_plans") != undefined){
				$('#modal_aetna_plans :selected').text('Select');
				$('#modal_aetna_plans :selected').val('');
			}
		}
	}
	/*-- END CHANGES SR1399 DEC'14 - n596307 --*/
	/*-- START CHANGES P20941a August2014 - Medicare Advantage - n596307 --*/
	if($('#switchForStatePlanSelectionPopUp')!=null && $('#switchForStatePlanSelectionPopUp')!=undefined 
    		&& $.trim($('#switchForStatePlanSelectionPopUp').text()) == 'ON'){
    	showStatePlanListModal();
    }
	/*-- END CHANGES P20941a August2014 - Medicare Advantage - n596307 --*/
	//content 1008
	else if($('#site_id').val()!=null && $('#site_id').val()!=undefined && $('#site_id').val() == 'universityofrochester'){
		//don't show plan selection model box
		searchWithDefaultPlan();
	}
	else if(directLinkSiteFound && planPrefillFlowSwitch != null && planPrefillFlowSwitch != 'true'){

    //don't show plan selection model box

    searchWithNoPlan();

}
	else{
		showPlanListModal();
	}
}
/*-- START CHANGES SR1399 DEC'14 - n596307 --*/
function checkPlanPrefillFlow(){
	var externalPlanCode=$('#externalPlanCode').html();
	if(externalPlanCode!=null && trim(externalPlanCode) != ""){
		return true;
	}
	else{
		return false;
	}
}

function searchWithOutPlanPrefillFlow(planSelected){
	$('#listPlanSelected').text(trim(planSelected));
	$('#productPlanName').val(trim(planSelected));
	$('#listPlanSelected').css('font-weight','bold');
	$('#columnPlanSelected').css('display','block');
	$('#plandisplay').show();
	$('#modal_aetna_plans :selected').text('');
	$('#modal_aetna_plans :selected').val('');
	$('#planChange').click(function(event){
		$('#planCodeFromDetails').val('');
		$('#productPlanName').val('');
		$('#modal_aetna_plans :selected').text('Select');
		$('#modal_aetna_plans :selected').val('');
		
		/*-- START CHANGES P20941a August2014 - Medicare Advantage - n596307 --*/
		if($('#switchForStatePlanSelectionPopUp')!=null && $('#switchForStatePlanSelectionPopUp')!=undefined 
	    		&& $.trim($('#switchForStatePlanSelectionPopUp').text()) == 'ON'){
				showStatePlanListModal();
	    }
		/*-- END CHANGES P20941a August2014 - Medicare Advantage - n596307 --*/
		//content 1008
    	else if($('#site_id').val()!=null && $('#site_id').val()!=undefined && $('#site_id').val() == 'universityofrochester'){
    		//don't show plan selection model box
    		searchWithDefaultPlan();
    	}
    	else if(directLinkSiteFound && planPrefillFlowSwitch != null && planPrefillFlowSwitch != 'true'){

        //don't show plan selection model box

        searchWithNoPlan();

}
		else{
			showPlanListModal();
		}
		
		return false;
	});
}
/*-- END CHANGES SR1399 DEC'14 - n596307 --*/

function detectBrowserName() { 
	if(navigator.userAgent.indexOf("Chrome") != -1 ) 
	{
		return 'Chrome';
	}
	else if(navigator.userAgent.indexOf("Opera") != -1 )
	{
		return 'Opera';
	}
	else if(navigator.userAgent.indexOf("Firefox") != -1 ) 
	{
		return 'Firefox';
	}
	else if((navigator.userAgent.indexOf("MSIE") != -1 ) || (!!document.documentMode == true )) //IF IE > 10
	{
		return 'IE'; 
	}  
	else 
	{
		return 'unknown';
	}
}

/*-- START CHANGES P20751 - PDI Removal - n596307 --*/
function prefillExternalPCPDTypeForSecure(){
	var externalPCPDSearchType = document.getElementById("externalPCPDSearchType");
	if(externalPCPDSearchType != undefined && externalPCPDSearchType.innerHTML != null && externalPCPDSearchType.innerHTML != ''){
		if($('#hl-autocomplete-search').val()!= undefined){
			$('#hl-autocomplete-search').val(externalPCPDSearchType.innerHTML);
			$('.hl-autocomplete .hl-search-box .hl-searchbar .hl-searchbar-input').css('color','#000000');
			$('.hl-autocomplete .hl-search-box .hl-searchbar .hl-searchbar-input').css('font-style','normal');
		}
		if(externalPCPDSearchType.innerHTML == 'All PCPs'){
			$('#classificationLimit').val('DMP');
			$('#suppressFASTDocCall').val('true');
			$('#pcpSearchIndicator').val('true');
		}
		$('#thrdColSelectedVal').val(externalPCPDSearchType.innerHTML);
		$('#searchTypeThrCol').val("byProvType");
		$('#quickSearchTypeThrCol').val("byProvType");
		$('#searchQuery').val(externalPCPDSearchType.innerHTML);
		/*if($('#hl-autocomplete-search-location').val() != undefined){
			var location = trim($('#hl-autocomplete-search-location').val());
			if(location != ghostTextWhereBox && location !=''){
				$('.hl-searchbar-button').click();
			}
		}*/
	}
}
/*-- END CHANGES P20751 - PDI Removal - n596307 --*/


function searchWithNoPlan(){

    $('#modalSelectedPlan').val('');

    $('#linkwithoutplan').val('true');

    $('.dialog-main-wrapper_planModal').css("display","none");

    $('#dialog_modal_id_planModal').css("display","none");

    if(ieVersion == 8 && ieVersion != null){

            $('#planListDialogBox').css("display","none");

    }

    searchWithOutPlan();

    searchSubmit('true');

    $("#docfindSearchEngineForm").submit();

    if((chk  || $('#searchQuery').val()) && (!($('#hl-autocomplete-search').val() == ghostTextWhatBox))){

            $(document).off('click','.hl-searchbar-button');

    }

}

/* Start changes for P21861a May15 release - N204183 */
function getIhDseDomainName(){
	var domainName = document.domain;
	var retDomainName = "";
	if (domainName.substr(0,4)=="dev2"){
		retDomainName = "dev2member.innovationhealth.myplanportal.com";
	}else if(domainName.substr(0,4)=="dev3"){
		retDomainName = "dev3member.innovationhealth.myplanportal.com";
	}else if(domainName.substr(0,3)=="dev"){
		retDomainName = "devmember.innovationhealth.myplanportal.com";
	}else if(domainName.substr(0,3)=="qa2"){
		retDomainName = "qa2member.innovationhealth.myplanportal.com";
	}else if(domainName.substr(0,3)=="qa3"){
		retDomainName = "qa3member.innovationhealth.myplanportal.com";
	}else if(domainName.substr(0,3)=="str"){
		retDomainName = "strmember.innovationhealth.myplanportal.com";
	}else if(domainName.substr(0,2)=="qa"){
		retDomainName = "qamember.innovationhealth.myplanportal.com";
	}else{
		retDomainName = "member.innovationhealth.myplanportal.com";
	}
	return retDomainName;
}

function getIhDseDomainNameForPublic(){
	var domainName = document.domain;
	var retDomainName = "";
	if(domainName.substr(0,4)=="dev2"){
		retDomainName = "dev2www.myplanportal.com";
	}
	else if(domainName.substr(0,4)=="dev3"){
		retDomainName = "dev3www.myplanportal.com";
	}
	else if (domainName.substr(0,3)=="dev"){
		retDomainName = "devwww.myplanportal.com";
	}else if(domainName.substr(0,3)=="qa2"){
		retDomainName = "qa2www.myplanportal.com";
	}else if(domainName.substr(0,3)=="qa3"){
		retDomainName = "qa3www.myplanportal.com";
	}else if(domainName.substr(0,3)=="str"){
		retDomainName = "strwww.myplanportal.com";
	}
	else if(domainName.substr(0,2)=="qa"){
		retDomainName = "qawww.myplanportal.com";
	}
	else{
		retDomainName = "www.myplanportal.com";
	}
	return retDomainName;
}
/* End changes for P21861a May15 release - N204183 */

/*--- START CHANGES P23695 Medicare Spanish Translation - n596307 ---*/
function manageGlobalVarsForCustomization(){
	populateUrlParameters();
	var langPrefUrl = $.getUrlVar('langPref');
	if(langPrefUrl == null || langPrefUrl == "" || langPrefUrl == undefined){
		$('#langPref').val("en");
	}
	else{
		if(langPrefUrl.indexOf('#markPage') > 0){
			langPrefUrl = langPrefUrl.split('#markPage')
			langPrefUrl = langPrefUrl[0];
		}
		$('#langPref').val(langPrefUrl);
	}
	
	var siteIdUrl = $.getUrlVar('site_id');
	if(siteIdUrl == null || siteIdUrl == "" || siteIdUrl == undefined){
		$('#site_id').val("dse");
	}
	else{
		if(siteIdUrl.indexOf('#markPage') > 0){
			siteIdUrl = siteIdUrl.split('#markPage')
			siteIdUrl = siteIdUrl[0];
		}
		$('#site_id').val(siteIdUrl);
	}
	
	ghostTextWhatBox = $('#ghostTextWhatBoxDiv').html();
	ghostTextWhereBox = $('#ghostTextWhereBoxDiv').html();
	tellUsYourLocation = $('#tellUsYourLocationDiv').html();
	hlLocationPopUpErrorMsg = $('#hlLocationPopUpErrorMsgDiv').html();
	zipCityState = $('#zipCityStateDiv').html();
	ghostTextLocationBox = $('#ghostTextLocationBoxDiv').html();
	planNetworkInformation = $('#planNetworkInformationDiv').html();
	/*-- Start changes for P23419a Aug16 release - N204183 --*/
	ratingReviewPleat = $('#ratingReviewPleat').html();
	/*-- End changes for P23419a Aug16 release - N204183 --*/
	if($('#langPref').val() != null && $('#langPref').val() == 'sp'){
		noneText = "Ninguno";
	}
	else{
		noneText = "None";
	}
	if($('#site_id').val() != null && $('#site_id').val() != ''){
		site_id = $('#site_id').val();
	}
	else{
		site_id = "dse";
	}
	if($('#langPref').val() != null && $('#langPref').val() != ''){
		langPref = $('#langPref').val();
	}
	else{
		langPref = "en";
	}
	if($('#directLinkSiteIDsDiv').html() != null){
		var directLinkSiteIDs = $('#directLinkSiteIDsDiv').html().split(",");
		for (var index = 0; index < directLinkSiteIDs.length; index++) {
			if($('#site_id').val() == directLinkSiteIDs[index]){
				directLinkSiteFound = true;
			}
		}
	}
}
/*--- END CHANGES P23695 Medicare Spanish Translation - n596307 ---*/

function redirectFeedback(){
	var domainVal;
	if(urlProtocol == urlProtocolSecure){
		if(site_id == "innovationhealth"){
			domainVal = "https://"+getIhDseDomainName();
		}else
			domainVal = "https://"+getSecureDseDomainName();
	}else{
		if(site_id == "innovationhealth"){
			domainVal = "http://"+etIhDseDomainNameForPublic();
		}else
			domainVal = "http://"+getPublicDseDomainName();
	}
	
	var teaLeafCookie = getCookie("TLAETGuid");
	
	var redirectUrl = "https://secure.opinionlab.com/ccc01/comment_card_json_4_0_b.asp?r=" +
			domainVal+"/dse/search?site_id="+site_id+
			"&width=1152&height=864&referer=" +
			domainVal+"%2Fdse%2Fsearch%3Fsite_id%3D"+site_id+
			"&prev=&time1=1444105200377&time2=1444105222037&currentURL=" +
			domainVal+"%2Fdse%2Fsearch%3Fsite_id%3D"+site_id +
			"&ocodeVersion=5.7.5&trigger=Floating&type=OnPage&custom_var="+teaLeafCookie+"|undefined/undefined/undefined|iframe&_rev=2";
			
//	alert (redirectUrl);
	popUpFeedback(redirectUrl);
}

function getCookie(cname) {
    var name = cname + "=";
    var ca = document.cookie.split(';');
    for(var i=0; i<ca.length; i++) {
        var c = ca[i];
        while (c.charAt(0)==' ') c = c.substring(1);
        if (c.indexOf(name) == 0) return c.substring(name.length, c.length);
    }
     return "";
}

function popUpFeedback(URL){
	var windowName='popup';
	var winOpts = 'width=600,height=525,scrollbars=yes,resizable=yes,toolbar=yes,location=1,overflow=scroll';
	window.name='INDEX';	
	aWindow=window.open(URL,windowName,winOpts);
	aWindow.focus();
}
function replaceSpecialCharCodes(productPlanName){
	if(productPlanName != undefined && productPlanName != ""){
		productPlanName = productPlanName.replace(/\+/gi, " ");
		productPlanName = productPlanName.replace(/%20/gi, " ");
		productPlanName = productPlanName.replace(/%3a/gi, ":");
		productPlanName = productPlanName.replace(/%24/gi, "$");
		productPlanName = productPlanName.replace(/%25/gi, "%");
		productPlanName = productPlanName.replace(/%26/gi, "&");
		productPlanName = productPlanName.replace(/%28/gi, "(");
		productPlanName = productPlanName.replace(/%29/gi, ")");
		productPlanName = productPlanName.replace(/%7c/gi, "|");
		productPlanName = productPlanName.replace(/%2b/gi, "+");
	}
	return productPlanName;
}
function GetEstimatesWellMatch( wellMatchURL )
{
	trackWTTopicFeature("Wellmatch DSE","Self Service"); 
trackWTTopicFeature("Wellmatch Total","Self Service");
	if($('#myAssistant')!= undefined  && $('#myAssistant').val() == "true")
    {      
                 showMyAssistantExtDialog();
    }else if($('#isGuestUser')!= undefined  && $('#isGuestUser').val() == "true"){
           showGuestIdDialog();
    }
    else{
    	popUp('/dse/search/disclaimer?continueUrl=' + wellMatchURL );
    }
}

//508 changes
function defaultFocusToSearchFor(){
	if($('#hl-autocomplete-search').length > 0){
		$('#hl-autocomplete-search').focus();
	}
    $('#hl-autocomplete-search').focus(function(){
		$('#hl-autocomplete-search').css({'outline':'thin dotted black'});
		
	});
    $('#hl-autocomplete-search').blur(function(){
		$('#hl-autocomplete-search').css({'outline':''});
		
	});
}

function configuringBindEvents(){
	$('td#imageDivLink2').keydown(function(event){ 
	    var keyCode = (event.keyCode ? event.keyCode : event.which);   
	    if (keyCode == 13) {
	       $('td#imageDivLink2').trigger('click');
	    }
	});
	$('td#imageDivLink3').keydown(function(event){ 
	    var keyCode = (event.keyCode ? event.keyCode : event.which);   
	    if (keyCode == 13) {
	       $('td#imageDivLink3').trigger('click');
	    }
	});
	$('td#imageDivLink4').keydown(function(event){ 
	    var keyCode = (event.keyCode ? event.keyCode : event.which);   
	    if (keyCode == 13) {
	       $('td#imageDivLink4').trigger('click');
	    }
	});
	$('td#imageDivLink6').keydown(function(event){ 
	    var keyCode = (event.keyCode ? event.keyCode : event.which);   
	    if (keyCode == 13) {
	       $('td#imageDivLink6').trigger('click');
	    }
	});
	$('td#imageDivLink7').keydown(function(event){ 
	    var keyCode = (event.keyCode ? event.keyCode : event.which);   
	    if (keyCode == 13) {
	       $('td#imageDivLink7').trigger('click');
	    }
	});
	$('#logInStatePopup_es').keydown(function(event){ 
	    var keyCode = (event.keyCode ? event.keyCode : event.which);   
	    if (keyCode == 9) {
	       $('#logInStatePopup_es').focus();
	    }
	});
	$('#logInStatePopup_es').focus(function(){
		$('#logInStatePopup_es').css({'outline':'thin dotted black'});
	});
	$('#logInStatePopup_es').blur(function(){
		$('#logInStatePopup_es').css({'outline':''});
	});

	$('#logInStatePopup').keydown(function(event){ 
	    var keyCode = (event.keyCode ? event.keyCode : event.which);   
	    if (keyCode == 9) {
	       $('#logInStatePopup').focus();
	    }
	});
	$('#logInStatePopup').focus(function(){
		$('#logInStatePopup').css({'outline':'thin dotted black'});
	});
	$('#logInStatePopup').blur(function(){
		$('#logInStatePopup').css({'outline':''});
	});
	
	$('#selectAPlan').keydown(function(event){ 
	    var keyCode = (event.keyCode ? event.keyCode : event.which);   
	    if (keyCode == 9) {
	       $('#selectAPlan').focus();
	    }
	});
	$('#selectAPlan').focus(function(){
		$('#selectAPlan').css({'outline':'thin dotted black'});
	});
	$('#selectAPlan').blur(function(){
		$('#selectAPlan').css({'outline':''});
	});
}