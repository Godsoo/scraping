/*-- START CHANGES P20941a August2014 - Medicare Advantage - n596307 --*/
var chkBuild = true;
var comServletCatCode;
function showStatePlanListModal(){
	if(chkBuild){
		var stateCode = $('#stateDD').val();
		var selectedPlan = $('#modal_aetna_plans :selected').val();
		buildStatePlanListAlertBox();
		$('#modal_aetna_plans_prim').remove();
		$('#attachedDiv').remove();
		$('#planListDialogBox').trigger('show');
		$('#planListDialogBox').css('display','none');

		$('.dialog-transparent-border_planModal').css("background-color","#333333");
		$('.dialog-dialogText_planModal').css("padding","0px 20px 10px");
		$('.dialog-dialogDynamicText_planModal').css("padding","0px 20px 20px");
		$('.dialog-dialogDynamicText_planModal').css("display","none");
		$('.dialog-close-button_planModal').css("display","none");
		$(".choosePlanNewGoldButton").css("display","none");
		$(".choosePlanNewGoldButtonSpanish").css("display","none");
		$("#withoutPlan").css("display","none");
		$('.dialog-subtitle_planModal').css("padding","20px");
		$('.dialog-subtitle_planModal').css("margin","0px");
		$('.dialog-title_planModal').css("margin","0px");
		$('.dialog-content-wrap_planModal').css("background-color","#ffffff");
		//$('.dialog-content-wrap_planModal').css("border","5px solid #D1D1D1");
		var prePlanModalHeight = $('#planListDialogBox.dialog-content_planModal').parents('div.dialog-main-wrapper_planModal').children('div.dialog-content-wrap_planModal').height();
		$('#planListDialogBox.dialog-content_planModal').parents('div.dialog-main-wrapper_planModal').children('div.dialog-transparent-border_planModal').css("height",prePlanModalHeight+40);
		$('.dialog-transparent-border_planModal').css('width','572px');
		/*-- Start changes SR1347 Sep2014 - N204183 --*/
		var stateToBePrefilled=$('#stateToBePrefilled').html();
		/*-- START CHANGES SR1399 DEC'14 - n596307 --*/
		var externalProdCode=$('#externalProdCode').html();
		var externalPlanName=$('#externalPlanName').html();
		//pshydv - fix for prefilling plans when externalPlanCodes are changed directly from URL without clearin cache
		if(stateToBePrefilled!=null && trim(stateToBePrefilled) != "" && externalProdCode!=null && externalPlanName!=null){
			$(".quickSearch_dropdown").val(trim(stateToBePrefilled));
			prefillPlanFromStateCode(trim(stateToBePrefilled), trim(externalProdCode), trim(externalPlanName));
		}
		else if(stateToBePrefilled!=null && trim(stateToBePrefilled) != ""){
			$(".quickSearch_dropdown").val(trim(stateToBePrefilled));
			prefillPlanFromStateCode(trim(stateToBePrefilled));
		}
		else if(stateCode != '' && stateCode != null){
			$(".quickSearch_dropdown").val(trim(stateCode));
			prefillPlanFromStateCode(trim(stateCode));
			var planPrefillFlowSwitch = getCookie('planPrefillFlowSwitch');
			if(selectedPlan!= '' && selectedPlan != null){
				$("#modal_aetna_plans").val(selectedPlan);
				if(planPrefillFlowSwitch != null && planPrefillFlowSwitch == 'true'){
					continueButtonSelected();
				}
			}
		}
		/*-- END CHANGES SR1399 DEC'14 - n596307 --*/
		var externalSearchType=$('#externalSearchType').html();
		if(externalSearchType!=null && trim(externalSearchType) != ""){
			$('#hl-autocomplete-search').val(externalSearchType);
		}
		/*-- End changes SR1347 Sep2014 - N204183 --*/
		chkBuild = false;
	}
	else{
		var stateCode = $('#stateDD').val();
		var selectedPlan = $('#modal_aetna_plans :selected').val();
		var stateList=$('#modalStates').html();
		$('#planListDialogBox').attr('dialogText_planModal', stateList);
		$('.dialog-dialogText_planModal').html(stateList);
		$('.dialog-main-wrapper_planModal').css("display","block");
		$('#dialog_modal_id_planModal').css("display","block");
		$('#planListDialogBox_planModal').trigger('show');
		$('#planListDialogBox_planModal').css('display','none');
		$('.dialog-close-button_planModal').css("display","none");
		$(".choosePlanNewGoldButton").css("display","none");
		$(".choosePlanNewGoldButtonSpanish").css("display","none");
		$("#withoutPlan").css("display","none");
		$('.dialog-transparent-border_planModal').css("background-color","#333333");

		$('.dialog-dialogText_planModal').css("padding","0px 20px 10px");
		$('.dialog-dialogDynamicText_planModal').css("padding","0px 20px 20px");
		$('.dialog-subtitle_planModal').css("padding","20px");
		$('.dialog-subtitle_planModal').css("margin","0px");
		$('.dialog-title_planModal').css("margin","0px");
		$('.dialog-content-wrap_planModal').css("background-color","#ffffff");
		//$('.dialog-content-wrap_planModal').css("border","5px solid #D1D1D1");
		var prePlanModalHeight = $('#planListDialogBox.dialog-content_planModal').parents('div.dialog-main-wrapper_planModal').children('div.dialog-content-wrap_planModal').height();
		$('#planListDialogBox.dialog-content_planModal').parents('div.dialog-main-wrapper_planModal').children('div.dialog-transparent-border_planModal').css("height",prePlanModalHeight+40);
		$('.dialog-transparent-border_planModal').css('width','572px');
		/*-- Start changes SR1347 Sep2014 - N204183 --*/
		if(stateCode != '' && stateCode != null){
			$(".quickSearch_dropdown").val(trim(stateCode));
			prefillPlanFromStateCode(trim(stateCode));
			if(selectedPlan!= '' && selectedPlan != null){
				$("#modal_aetna_plans").val(selectedPlan);
			}
		}
		var externalSearchType=$('#externalSearchType').html();
		if(externalSearchType!=null && trim(externalSearchType) != ""){
			$('#hl-autocomplete-search').val(externalSearchType);
		}
		/*-- End changes SR1347 Sep2014 - N204183 --*/
	}
	return false;
}

function buildStatePlanListAlertBox(){
	var title=$('#modalStateTitle').html();
	var subTitle=$('#modalStateSubtitle').html();
	var stateList=$('#modalStates').html();
	
	$('#planListDialogBox').attr('title_planModal', title);
	$('#planListDialogBox').attr('subtitle_planModal', subTitle);
	$('#planListDialogBox').attr('dialogText_planModal', stateList);
	
	$('#planListDialogBox').doDialogCustomDse({width: 470, modal:true, draggable:true, closeOnEscape:false},
			[{id:'btnChooseStatePlan',value:'CHOOSE PLAN',url:"javascript:closeGenericModalBox()"}],'planModal');
	
	$(".choosePlanNewGoldButton").bind('click',function(){ 
		/*-- START CHANGES P8551c QHP_IVL PCR - n204189 --*/
		//508 Changes
		defaultFocusToSearchFor();
		continueButtonSelected();
		/*-- END CHANGES P8551c QHP_IVL PCR - n204189 --*/
	});
	
	$(".choosePlanNewGoldButtonSpanish").bind('click',function(){ 
		//508 Changes
		defaultFocusToSearchFor();
		continueButtonSelected();
	});

	$("#contWOPlan_ft").bind('click',function(){
var stateCode = $('#stateDD').val();
		var selectedPlan = $('#modal_aetna_plans :selected').val();
		if(stateCode != null && stateCode != ''){
			$('#stateDD').val('');
			eraseCookie('stateCode');
		}
		if(selectedPlan != null && selectedPlan != ''){
			$('#modal_aetna_plans :selected').val('');
			eraseCookie('selectedPlan');
		}
		$('#modalSelectedPlan').val('');
		$('#linkwithoutplan').val('true');
		$('.dialog-main-wrapper_planModal').css("display","none");
		$('#dialog_modal_id_planModal').css("display","none");
		$('.dialog-dialogDynamicText_planModal').css("display","none");
		if(ieVersion == 8 && ieVersion != null){
			$('#planListDialogBox').css("display","none");
		}
		//showing no plan selected on search page
		planSelected = noneText;
		/*-- START CHANGES SR1399 DEC'14 - n596307 --*/
		var externalPlanCode = getCookie('externalPlanCode');
		if(checkPlanPrefillFlow() || (externalPlanCode != null && externalPlanCode != ''))
		{
			searchWithOutPlanPrefillFlow(planSelected);
			eraseCookie('planDisplayName');
			eraseCookie('externalPlanCode');
		}
		else{
			searchWithOutStatePlan(planSelected);
		}
		//Building No plan Selected Alert
		buildNoPlanSelectedAlertBox();
		return false;
	});

	return false;
}

/*-- START CHANGES P8551c QHP_IVL PCR - n204189 --*/
function extractChildPlans(childPlans){
	if (childPlans != null){
		var pipe = childPlans.indexOf('|');
		if (pipe > -1){
			childPlans = trim(childPlans.substring(pipe+1,childPlans.length));
		}
		var childPlanList = childPlans.split(":");
		var index;
		var childPlanFinalList;
		for (index = 0; index < childPlanList.length; index++) {
			if(childPlanList[index] != null && childPlanList[index] != ''){
				if(childPlanFinalList == undefined){
					childPlanFinalList =  " " + childPlanList[index];
				}
				else{
					childPlanFinalList  += ", " + childPlanList[index];
				}
			}
		}
		return childPlanFinalList;
	}
}

function addPlanFamilyToSelectedPlan(){
	var childPlans = $('#modal_aetna_plans :selected').val();
	var planFamilySelected;
	if(childPlans == null || childPlans == undefined){
		if($('#listPlanSelected').val() != null && $('#listPlanSelected').val() != undefined){
			childPlans = $('#listPlanSelected').val();
		}
		else{
			return "";	
		}
  	}
	if (childPlans.indexOf('_PLANHEADER_') > -1){
		var headerWithChildPlans = childPlans.split('_PLANHEADER_');
		if(headerWithChildPlans != null){
			var childPlanList = extractChildPlans(headerWithChildPlans[0]);
			/*-- START CHANGES SR1399 DEC'14 - n596307 --*/
			//pshydv - removing planPrefillName 
			if (headerWithChildPlans[1].indexOf('_PLANPREFILL_') > -1){
				var headerAndChoosenPlan = headerWithChildPlans[1].split('_PLANPREFILL_');
				if(headerAndChoosenPlan != null){
					planFamilySelected = headerAndChoosenPlan[0].concat(" include:",childPlanList);
				}
			}
			/*-- START CHANGES SR1399 DEC'14 - n596307 --*/
			else{
				planFamilySelected = headerWithChildPlans[1].concat(" include:",childPlanList);
			}
		}
	}
	else{
		planFamilySelected = childPlans;
	}
	return planFamilySelected;
}


function continueButtonSelected(){
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
	if(planSelected == ""){
		displayNoPlansSelectedErrorMessage();
		return false;
	}
	if(planSelected == "Select" || planVal == "DINDE"){
		return false;
	}
	$('.dialog-main-wrapper_planModal').css("display","none");
	$('#dialog_modal_id_planModal').css("display","none");
	$('.dialog-dialogDynamicText_planModal').css("display","none");
	if(ieVersion == 8 && ieVersion != null){
		$('#planListDialogBox').css("display","none");
	}
	if(planSelected != null){
		/*-- START CHANGES P8551c QHP_IVL PCR - n596307 --*/
		if($('#switchForShowPlansFamilyWise')!=null && $.trim($('#switchForShowPlansFamilyWise').text()) == 'ON')
		{
			planSelected = addPlanFamilyToSelectedPlan();
		}
		/*-- END CHANGES P8551c QHP_IVL PCR - n596307 --*/
		searchWithPlan(planSelected,planVal);
		$('#modalSelectedPlan').val(planVal);
		//To show selected Plan on Search page also
		if($("#modalSelectedPlan").val() != '' && $("#modalSelectedPlan").val()!= null){
			$('#plandisplay').show();
		}
		$('#columnPlanSelected').css('display','block');

		/*-- START CHANGES P8551c QHP_IVL PCR - N204189 --*/
		/* Show or hide Dental plans */
		var dentalPlans = ($('#listOfdentalPlans').text()).split(",");
		var showDental = true;
		for ( index = 0; index < dentalPlans.length; index++ ) {
			if( trimSpace(dentalPlans[index]) != "" )
			{
				if ( trimSpace(dentalPlans[index]) == trimSpace(planVal) )
				{
					showDental = true;
					break;
				}
				showDental = false;
			}
		} 

		if( showDental )
		{
			$('.dentalBlueLink').show();
		}
		else
		{
			$('.dentalBlueLink').hide();
		}
		/*  Show or hide Dental plans */
		/*-- END CHANGES P8551c QHP_IVL PCR - N204189 --*/

		whyPressed = 'publicPlan';
if($('#hl-autocomplete-search-location').val()!= undefined && $('#hl-autocomplete-search-location').val() != ghostTextWhereBox
			&& $('#hl-autocomplete-search-location').val()!='' && $('#hl-autocomplete-search').val()!= undefined 
			&& $('#hl-autocomplete-search').val() != ghostTextWhatBox && $('#hl-autocomplete-search').val()!='')
		{
			markPage('publicPlanSelected');
			searchSubmit('true');
			$("#docfindSearchEngineForm").submit();
		}			
	}		 
	/*-- Start changes SR1347 Sep2014 - N204183 --*/
	var externalSearchType = document.getElementById("externalSearchType");
	var stateToBePrefilled=$('#stateToBePrefilled').html();
	if(externalSearchType != undefined && externalSearchType.innerHTML != null && externalSearchType.innerHTML != '' && (stateToBePrefilled==null || trim(stateToBePrefilled) == "")){
		 showLocationDialogBox(trim(externalSearchType.innerHTML));
	}
	/*-- End changes SR1347 Sep2014 - N204183 --*/
	return false;
}
/*-- END CHANGES P8551c QHP_IVL PCR - n204189 --*/

function stateCodePlanPopulate(searchTerm){
	$('.dialog-dialogDynamicText_planModal').css("display","none");
	$(".choosePlanNewGoldButton").css("display","none");
	$(".choosePlanNewGoldButtonSpanish").css("display","none");
$("#withoutPlan").css("display","none");
	var stateCode = searchTerm.value;
	if(!validateStateCode(stateCode)){
		var prePlanModalHeight = $('#planListDialogBox.dialog-content_planModal').parents('div.dialog-main-wrapper_planModal').children('div.dialog-content-wrap_planModal').height();
		$('#planListDialogBox.dialog-content_planModal').parents('div.dialog-main-wrapper_planModal').children('div.dialog-transparent-border_planModal').css("height",prePlanModalHeight+40);
		return;
	}
	var ajaxReturn = false;
	$.ajax( {
		type : "GET",
		url : "search/populateStateProducts",
		data : 'searchVal=' + stateCode,
		dataType : "text",
		async: false,
		success : function(response) {
			if (response == "") {
				displayNoPlansErrorMessage();
			} else {
				$('#modalStatePlans').val(response);
				showStatePlans();
				/*-- START CHANGES P8551c QHP_IVL PCR - n204189 --*/
				if( response.indexOf("selected") != -1 ){
					continueButtonSelected();
				}
				/*-- END CHANGES P8551c QHP_IVL PCR - n204189 --*/
				ajaxReturn = true;
			}
		},
	});
	
	return ajaxReturn;
}
	

function showStatePlans(){
	var statePlanList=$('#modalStatePlans').val();
	$('.dialog-dialogDynamicText_planModal').html(statePlanList);
	var plansAvailable=$('#selectAPlanAvailableInState').html();
	$('.dialog-dialogDynamicText_planModal').prepend(plansAvailable);
	$('.dialog-dialogDynamicText_planModal').css("display","block");
	var prePlanModalHeight = $('#planListDialogBox.dialog-content_planModal').parents('div.dialog-main-wrapper_planModal').children('div.dialog-content-wrap_planModal').height();
	$('#planListDialogBox.dialog-content_planModal').parents('div.dialog-main-wrapper_planModal').children('div.dialog-transparent-border_planModal').css("height",prePlanModalHeight+40);
	$(".choosePlanNewGoldButton").css("display","block");
	$(".choosePlanNewGoldButtonSpanish").css("display","block");
	if($('#site_id').val()!=null && $('#site_id').val()!=undefined && ($('#site_id').val() == 'QualifiedHealthPlanDoctors')||$('#site_id').val() =='ivl'){
		$('.dialog-dialogDynamicText_planModal').append('<br/><h4>For Aetna Leap Plans click <a href="http://www.aetnafindadoc.com" target="_blank">www.aetnafindadoc.com</a></h4>');
	}
	var stateCode = $('#stateDD').val();
	if(stateCode != '' && stateCode != null && stateCode == 'FL' && $('#site_id').val()!=null && $('#site_id').val()!=undefined && $('#site_id').val() == 'medicare'){
		$("#withoutPlan").css("display","none");
	}
	else{
		$("#withoutPlan").css("display","block");
	}
}

function validateStateCode(stateCode){
	if(stateCode.length == 2 && isNaN(stateCode)){
		return true;
	}else{
		return false;
	}
}

function displayNoPlansErrorMessage(){
	var errMessage=$('#errorMessageNoPlans').html();
	$('.dialog-dialogDynamicText_planModal').html(errMessage);
	$('.dialog-dialogDynamicText_planModal').css("display","block");
	var prePlanModalHeight = $('#planListDialogBox.dialog-content_planModal').parents('div.dialog-main-wrapper_planModal').children('div.dialog-content-wrap_planModal').height();
	$('#planListDialogBox.dialog-content_planModal').parents('div.dialog-main-wrapper_planModal').children('div.dialog-transparent-border_planModal').css("height",prePlanModalHeight+40);
	$(".choosePlanNewGoldButton").css("display","none");
	$(".choosePlanNewGoldButtonSpanish").css("display","none");
$("#withoutPlan").css("display","none");
}

function displayNoPlansSelectedErrorMessage(){
	if($('.dialog-dialogDynamicText_planModal').find('#errorNoPlansImage').length==0){
		var errMessage=$('#errorMessageNoPlansSelected').html();
		$('.dialog-dialogDynamicText_planModal').prepend(errMessage);
	}
	$('.dialog-dialogDynamicText_planModal').css("display","block");
	var prePlanModalHeight = $('#planListDialogBox.dialog-content_planModal').parents('div.dialog-main-wrapper_planModal').children('div.dialog-content-wrap_planModal').height();
	$('#planListDialogBox.dialog-content_planModal').parents('div.dialog-main-wrapper_planModal').children('div.dialog-transparent-border_planModal').css("height",prePlanModalHeight+40);
	//$(".choosePlanGoldButton").css("display","none");
}

function searchWithOutStatePlan(planSelected){
	$('#listPlanSelected').text(trim(planSelected));
	$('#productPlanName').val(trim(planSelected));
	$('#listPlanSelected').css('font-weight','bold');
	$('#columnPlanSelected').css('display','block');
	$('#plandisplay').show();
	$('#planChange').click(function(event){
		$('#planCodeFromDetails').val('');
		$('#productPlanName').val('');
	    showStatePlanListModal();
		return false;
	});
}

function buildNoPlanSelectedAlertBox(){
	$('#noPlanAlertDialogBox').html($('#noPlanAlertDialogBoxContent').html());
	$('#noPlanAlertDialogBox.dialog-content').parents('div.dialog-main-wrapper').children('div.dialog-content-wrap').children('div.dialog-title').html($('#modalStateNoPlanSelectedTitle').html());
	var noPlanAlertHeight = $('#noPlanAlertDialogBox.dialog-content').parents('div.dialog-main-wrapper').children('div.dialog-transparent-border').height();
	$('#noPlanAlertDialogBox.dialog-content').parents('div.dialog-main-wrapper').children('div.dialog-transparent-border').css("height",noPlanAlertHeight + 2);
	$('.dialog-content-wrap').css("background-color","#ffffff");
	$('.dialog-content-wrap').css("border-color","#D1D1D1");
	renderDefaultUIForButton();
	$('#noPlanAlertDialogBox').trigger('show');
}

function renderDefaultUIForButton(){
	//$('.gold_button_left').css("background-image","url(/dse/assets/images/BTN_gold_left.gif)");
	//$('.gold_button').css("background-image","url(/dse/assets/images/BTN_gold_center_fill.gif)");
	$('.gold_button').css("height","20px");
	$('.gold_button').css("width","100px");
	//$('.gold_button_right').css("background-image","url(/dse/assets/images/BTN_gold_right.gif)");
}

function showStateModalBoxAgain(){
	$('#noPlanAlertDialogBox').trigger('hide');
	showStatePlanListModal();
}
/*-- Start changes SR1347 Sep2014 - N204183 --*/
function prefillPlanFromStateCode(stateCode, externalProdCode, externalPlanName){
	$('.dialog-dialogDynamicText_planModal').css("display","none");
	$(".choosePlanNewGoldButton").css("display","none");
	$(".choosePlanNewGoldButtonSpanish").css("display","none");
$("#withoutPlan").css("display","none");
	if(!validateStateCode(stateCode)){
		var prePlanModalHeight = $('#planListDialogBox.dialog-content_planModal').parents('div.dialog-main-wrapper_planModal').children('div.dialog-content-wrap_planModal').height();
		$('#planListDialogBox.dialog-content_planModal').parents('div.dialog-main-wrapper_planModal').children('div.dialog-transparent-border_planModal').css("height",prePlanModalHeight+40);
		return;
	}
	var ajaxReturn = false;
	$.ajax( {
		type : "GET",
		url : "search/populateStateProducts",
		data : 'searchVal=' + stateCode + '&externalProdCode=' + externalProdCode + '&externalPlanName=' + externalPlanName + '&selectedState=true',
		dataType : "text",
		async: false,
		success : function(response) {
			if (response == "") {
				displayNoPlansErrorMessage();
			} else {
				$('#modalStatePlans').val(response);
				showStatePlans();
				/*-- START CHANGES P8551c QHP_IVL PCR - n204189 --*/
				if( response.indexOf("selected") != -1 ){
					continueButtonSelected();
				}
				/*-- END CHANGES P8551c QHP_IVL PCR - n204189 --*/
				ajaxReturn = true;
			}
		},
	});
}
/*-- End changes SR1347 Sep2014 - N204183 --*/

/*-- START CHANGES P20751b ACO Branding - n596307 --*/
function handleTogglePlansLinkFunctionality(plan){
	//hiding div before refilling
	$('.dialog-dialogText_planModal').css("display","none");
	//AJAX call to show full plan listing by greying out plans out of area.
	var hlValueToBePassed;
	if($("#QuickGeoType").val()=='state'){
		hlValueToBePassed = $('#stateCode').val();
	}
	else{
		hlValueToBePassed = $('#QuickZipcode').val();
	}
	var planDiv = fetchPlanListAsPerGeoInput(hlValueToBePassed, plan);
	//$('#planListDialogBox').attr('dialogText_planModal', $(planDiv).html());
	$('.dialog-dialogText_planModal').html($(planDiv).html());
	//adding show all plans warning text
	if(plan == "showAllPlans"){
		$('.dialog-dialogText_planModal').prepend($('#showAllPlansText').html());
	}
	//showing div again after refilling
	$('.dialog-dialogText_planModal').css("display","block");
	autoAdjustTransparentBorder();
}

function fetchPlanListAsPerGeoInput(geoInput, planValSelected){
	/*if(!validateStateCode(stateCode)){
		var prePlanModalHeight = $('#planListDialogBox.dialog-content_planModal').parents('div.dialog-main-wrapper_planModal').children('div.dialog-content-wrap_planModal').height();
		$('#planListDialogBox.dialog-content_planModal').parents('div.dialog-main-wrapper_planModal').children('div.dialog-transparent-border_planModal').css("height",prePlanModalHeight+40);
		return;
	}*/
	$.ajax( {
		type : "GET",
		url : "search/populatePlanListAsPerGeoInput",
		data : 'searchVal=' + geoInput + '&planValSelected=' + planValSelected + '&planTypeForPublic=' + planTypeForPublic,
		dataType : "text",
		async: false,
		success : function(response) {
			if (response == "") {
				displayNoPlansErrorMessage();
			} else {
				$('#modalStatePlans').html(response);
			}
		},
	});
	return '#modalStatePlans';
}

function searchWithHLSuggestions(){
	if(trim($("#hl-autocomplete-search-location").val()) != '' 
		&& trim($("#geoMainTypeAheadLastQuickSelectedVal").val())!=trim($('#hl-autocomplete-search-location').val())){
		//make force HL selection
		var hlStatusCode;
		if(hlStatusCodeFirstWhereBox != null && hlStatusCodeFirstWhereBox != undefined){
			hlStatusCode = hlStatusCodeFirstWhereBox;
		}
		else if(hlStatusCodeSecondWhereBox != null && hlStatusCodeSecondWhereBox != undefined){
			hlStatusCode = hlStatusCodeSecondWhereBox;
		}
		if(hlStatusCode != null && hlStatusCode != undefined){
			responseFromHL(trim($('#hl-autocomplete-search').val()),trim($('#hl-autocomplete-search-location').val()),hlStatusCode);
		}
		else{
			//HL is down - show full plan listing
			console.log("HL service is down");
			showPlanListModal();
		}
	}
	else{	//selected from HL
		//show dynamic plan listing
		showPlanListModal();
	}
}

function autoAdjustTransparentBorderHLSuggesionPopUp(){
	var modalHeight = $('#preSearchHLDialogBox.dialog-content_preSearchHLDialogBox').parents('div.dialog-main-wrapper_preSearchHLDialogBox').children('div.dialog-content-wrap_preSearchHLDialogBox').height();
	$('#preSearchHLDialogBox.dialog-content_preSearchHLDialogBox').parents('div.dialog-main-wrapper_preSearchHLDialogBox').children('div.dialog-transparent-border_preSearchHLDialogBox').css("height",modalHeight+40);
}

var chkHLLocationBoxBuild = true;
function showHLNoLocationDialogBox(searchTerm){
	if(chkHLLocationBoxBuild){
		buildHLNoLocationDialogBox(searchTerm);
		chkHLLocationBoxBuild = false;
	}
	else{
		$('#locationHLDialogBox.dialog-content').parents('div.dialog-main-wrapper').children('div.dialog-content-wrap').children('div.dialog-title').text($('#hlModalSecondCallChangedTitle').html()).css({ 'font-weight': 'bold', 'color': '#7d3f98', 'font-size': '18pt' });;
		var $title=$('#locationHLDialogBox.dialog-content').parents('div.dialog-main-wrapper').children('div.dialog-content-wrap').children('div.dialog-title');
			$('#locationHLDialogBox').html('<table class="rddialogHLSuggestionSubTitle"><tr><td>You typed "<span id="whereBoxValNoLocations">'+searchTerm+'</span>". We can\'t find a matching location.</td></tr>' +
					'<tr><td><br/>Please enter a zip code or city and state.</td>'+
					'<tr><td id="whereValRequired"></td></tr>'+
					'</tr><tr><td id="locationTypeAheadBox">' + $('#includeTANoLocScript').html() + '<div class="hl-no-location-textBox"></div></td></tr></table>');
		
		renderFilterUIForNonSecure();
		$('#locationHLDialogBox').trigger('show');
	      $('.dialog-modal').width($(document).width());
	      $('.dialog-modal').height($(document).height() + 50);
		$('a#searchWHLocHLCriteria').children('table').children('tbody').children('tr').children('td.gold_button').css("position","relative");
		$('a#cancelWHLocHLCriteria').children('table').children('tbody').children('tr').children('td.gold_button').css("position","relative");
		autoAdjustTransBorderHeightHLWhereBox();
	}
	return false;
}

function buildHLNoLocationDialogBox(searchTerm){
	$('#locationHLDialogBox.dialog-content').parents('div.dialog-main-wrapper').children('div.dialog-content-wrap').children('div.dialog-title').text($('#hlModalSecondCallChangedTitle').html()).css({ 'font-weight': 'bold', 'color': '#7d3f98', 'font-size': '18pt' });;
	var $title=$('#locationHLDialogBox.dialog-content').parents('div.dialog-main-wrapper').children('div.dialog-content-wrap').children('div.dialog-title');
		$('#locationHLDialogBox').html('<table class="rddialogHLSuggestionSubTitle"><tr><td>You typed "<span id="whereBoxValNoLocations">'+searchTerm+'</span>". We can\'t find a matching location.</td></tr>' +
				'<tr><td><br/>Please enter a zip code or city and state.</td>'+
				'<tr><td id="whereValRequired"></td></tr>'+
				'</tr><tr><td id="locationTypeAheadBox">' + $('#includeTANoLocScript').html() + '<div class="hl-no-location-textBox"></div></td></tr></table>');
	
	renderFilterUIForNonSecure();
	$('#locationHLDialogBox').trigger('show');
      $('.dialog-modal').width($(document).width());
      $('.dialog-modal').height($(document).height() + 50);
	$('a#searchWHLocHLCriteria').children('table').children('tbody').children('tr').children('td.gold_button').css("position","relative");
	$('a#cancelWHLocHLCriteria').children('table').children('tbody').children('tr').children('td.gold_button').css("position","relative");
	autoAdjustTransBorderHeightHLWhereBox();
	
	$('#cancelWHLocHLCriteria').click(function(){
		$('#locationHLDialogBox').trigger('hide');
		$('#ioe_qType').val('');
		return false;
	});
	
	$('#searchWHLocHLCriteria').bind('click',function(event){
		/*Start changes for type ahead location*/
		/* P20488 - 1231 changes start */
		if(trim($('#hl-no-location-autocomplete-search').val()) == "" || trim($('#hl-no-location-autocomplete-search').val()) == ghostTextWhereBox){
			//show error div
			$('#whereValRequired').html($('#hlModalNoValueProvided').html());
			autoAdjustTransBorderHeightHLWhereBox();
		} /* P20488 - 1231 changes end */
		else if((trim($('#hl-autocomplete-search-location').val())) != (trim($('#hl-no-location-autocomplete-search').val()))){
			changeFormatGeoLocation();
			$('#hl-autocomplete-search-location').val($('#hl-no-location-autocomplete-search').val());
			$('#whereValRequired').html('');
			$('#locationHLDialogBox').trigger('hide');
			searchWithHLSuggestions();
		}
		//if same value is feeded again in this popUp also, display the popUp again
		else{
			$('#locationHLDialogBox').trigger('hide');
			showHLNoLocationDialogBox(searchTerm);
		}
		/*End changes for type ahead locations*/   
		return false;
	});
}

var chkHLNoLocationBoxBuild = true;
function showHLLocationDialogBox(searchTerm){
	if(chkHLNoLocationBoxBuild){
		buildHLLocationDialogBox(searchTerm);
		chkHLNoLocationBoxBuild = false;
	}
	else{
		$('#locationHLDialogBox.dialog-content').parents('div.dialog-main-wrapper').children('div.dialog-content-wrap').children('div.dialog-title').text($('#hlModalSecondCallChangedTitle').html()).css({ 'font-weight': 'bold', 'color': '#7d3f98', 'font-size': '18pt' });;
		var $title=$('#locationHLDialogBox.dialog-content').parents('div.dialog-main-wrapper').children('div.dialog-content-wrap').children('div.dialog-title');
		$('#locationHLDialogBox').html('<table class="rddialogHLSuggestionSubTitle"><tr><td>You typed "<span id="whereBoxValNoLocations">'+searchTerm+'</span>". We can\'t find a matching location.</td></tr>' +
				'<tr><td><br/>Please enter a zip code or city and state.</td>'+
				'<tr><td id="whereValRequired"></td></tr>'+
				'</tr><tr><td id="locationTypeAheadBox">' + $('#includeTALocScript').html() + '<div class="hl-location-textBox"></div></td></tr></table>');

		renderFilterUIForNonSecure();
		$('#locationHLDialogBox').trigger('show');
		$('.dialog-modal').width($(document).width());
		$('.dialog-modal').height($(document).height() + 50);
		$('a#searchWHLocHLCriteria').children('table').children('tbody').children('tr').children('td.gold_button').css("position","relative");
		$('a#cancelWHLocHLCriteria').children('table').children('tbody').children('tr').children('td.gold_button').css("position","relative");
		autoAdjustTransBorderHeightHLWhereBox();
	}
	return false;
}

function buildHLLocationDialogBox(searchTerm){
	$('#locationHLDialogBox.dialog-content').parents('div.dialog-main-wrapper').children('div.dialog-content-wrap').children('div.dialog-title').text($('#hlModalSecondCallChangedTitle').html()).css({ 'font-weight': 'bold', 'color': '#7d3f98', 'font-size': '18pt' });;
	var $title=$('#locationHLDialogBox.dialog-content').parents('div.dialog-main-wrapper').children('div.dialog-content-wrap').children('div.dialog-title');
	$('#locationHLDialogBox').html('<table class="rddialogHLSuggestionSubTitle"><tr><td>You typed "<span id="whereBoxValNoLocations">'+searchTerm+'</span>". We can\'t find a matching location.</td></tr>' +
			'<tr><td><br/>Please enter a zip code or city and state.</td>'+
			'<tr><td id="whereValRequired"></td></tr>'+
			'</tr><tr><td id="locationTypeAheadBox">' + $('#includeTALocScript').html() + '<div class="hl-location-textBox"></div></td></tr></table>');

	renderFilterUIForNonSecure();
	$('#locationHLDialogBox').trigger('show');
	$('.dialog-modal').width($(document).width());
	$('.dialog-modal').height($(document).height() + 50);
	$('a#searchWHLocHLCriteria').children('table').children('tbody').children('tr').children('td.gold_button').css("position","relative");
	$('a#cancelWHLocHLCriteria').children('table').children('tbody').children('tr').children('td.gold_button').css("position","relative");
	autoAdjustTransBorderHeightHLWhereBox();

	$('#cancelWHLocHLCriteria').click(function(){
		$('#locationHLDialogBox').trigger('hide');
		$('#ioe_qType').val('');
		return false;
	});

	$('#searchWHLocHLCriteria').bind('click',function(event){
		/*Start changes for type ahead location*/
		/* P20488 - 1231 changes start */
		if(trim($('#hl-location-autocomplete-search').val()) == "" || trim($('#hl-location-autocomplete-search').val()) == ghostTextWhereBox){
			//show error div
			$('#whereValRequired').html($('#hlModalNoValueProvided').html());
			autoAdjustTransBorderHeightHLWhereBox();
		} /* P20488 - 1231 changes end */
		else if((trim($('#hl-autocomplete-search-location').val())) != (trim($('#hl-location-autocomplete-search').val()))){
			changeFormatGeoLocation();
			$('#hl-autocomplete-search-location').val($('#hl-location-autocomplete-search').val());
			$('#whereValRequired').html('');
			$('#locationHLDialogBox').trigger('hide');
			searchWithHLSuggestions();
		}
		//if same value is feeded again in this popUp also, display the popUp again
		else{
			$('#locationHLDialogBox').trigger('hide');
			showHLLocationDialogBox(searchTerm);
		}
		/*End changes for type ahead locations*/   
		return false;
	});
}

function autoAdjustTransBorderHeightHLWhereBox(){
	var transHeight = $('#locationHLDialogBox.dialog-content').parents('div.dialog-main-wrapper').children('div.dialog-content-wrap').height();
	$('#locationHLDialogBox.dialog-content').parents('div.dialog-main-wrapper').children('div.dialog-transparent-border').css("height",transHeight+32);
}

function decidePopUpLayoutAsPerResponse(response){
	if(response != null){
		if(response.indexOf('firstHLCallData') > -1){
			return false;
		}
		else if(response.indexOf('secondHLCallData') > -1){
			return true;
		}
	}
}

function changeDivContentAsPerResponse(whereBoxVal, response){
	if(decidePopUpLayoutAsPerResponse(response)){
		$('.rddialogHLSuggestionTitle').html($('#hlModalSecondCallChangedTitle').html());
		$('.rddialogHLSuggestionSubTitle').html($('#hlModalSecondCallChangedSubTitle').html());
		$('#whereBoxValPossibleLocations').text(whereBoxVal);
	}
	else{
		$('.rddialogHLSuggestionTitle').html($('#hlModalChangedTitle').html());
		$('.rddialogHLSuggestionSubTitle').html($('#hlModalChangedSubTitle').html());
		$('#whereBoxValMultipleLocations').text(whereBoxVal);
	}
}

function buildPreSearchHLListBox(whereBoxVal, response){
	var hlModalTitle;
	var hlModalSubTitle;
	//changeDivContentAsPerResponse(whereBoxVal, response);
	if(decidePopUpLayoutAsPerResponse(response)){
		$('#whereBoxValPossibleLocations').text(whereBoxVal);
		hlModalTitle = $('#hlModalSecondCallTitle').html();
		hlModalSubTitle = $('#hlModalSecondCallSubTitle').html();
	}
	else{
		$('#whereBoxValMultipleLocations').text(whereBoxVal);
		hlModalTitle = $('#hlModalTitle').html();
		hlModalSubTitle = $('#hlModalSubTitle').html();
	}
	$('#preSearchHLDialogBox').attr('title_preSearchHLDialogBox',hlModalTitle);
	$('#preSearchHLDialogBox').attr('subtitle_preSearchHLDialogBox', hlModalSubTitle);
	$('#preSearchHLDialogBox').attr('dialogText_preSearchHLDialogBox', '<table id="preSearchHLModalContentTable" width=100%><tr><td>'+response+'</td></tr></table>');
	
	if(urlProtocol == urlProtocolNonSecure){
		$('#preSearchHLDialogBox').doDialogDse({width: 400, modal:true, draggable:true, closeOnEscape:true},
				[{id:'btnCancelPreSearchHL',value:'Cancel', "url":"javascript:closeModalBoxWithId('#preSearchHLDialogBox');"},
				{id:'btnChoosePreSearchHL',value:'Continue',url:"javascript:triggerSearch('#preSearchHLDialogBox');"}],'preSearchHLDialogBox');
	}
	
	$('#btnCancelPreSearchHL').click(function(){
		$('#preSearchHLDialogBox').trigger('hide');
		return false;
	});
	
	$('#btnChoosePreSearchHL').click(function(){
		hlContinueButtonSelected();
	});	
}

function hlContinueButtonSelected(){
	var hlValSelected = $('#quickSearchHLSelection :selected').text();
	if(hlValSelected == ""){
		displayLocationRequiredErrorMessage();
		return false;
	}
	else{
		$('#errorLocRequired').html('');
		//proceed further
		var hlResponseData = $('#quickSearchHLSelection :selected').val();
		if(hlResponseData != null && hlResponseData != undefined && hlResponseData.indexOf('|') > -1){
			fillTheHLResponseVal(hlResponseData);
		}
		$('.hl-searchbar-button').click();
		$('#preSearchHLDialogBox').trigger('hide');
		return false;
	}
}

function fillTheHLResponseVal(hlResponseData){
	var hlResponseDataList = hlResponseData.split('|');
	var whichCallData = hlResponseDataList[0];
	var label ;
	var typeOfGeoInput ;
	var zipCode ;
	var coordinates ;
	var city;
	var stateCode ;
	var whereBoxVal;
	if(whichCallData == 'firstHLCallData'){
		label = hlResponseDataList[1];
		typeOfGeoInput = hlResponseDataList[3];
		zipCode = hlResponseDataList[4];
		coordinates = hlResponseDataList[5];
		stateCode = hlResponseDataList[6];
		$('#QuickZipcode').val(zipCode);
		$('#QuickCoordinates').val(coordinates);
		$('#stateCode').val(stateCode);
		var str = $(".typeAheadURLOrignal").html();
		if(str!=null && str!=''){
			if(($('#QuickZipcode').val()!=null && $('#QuickZipcode').val()!='' && $('#QuickZipcode').val()) && ($('#QuickCoordinates').val()!=null && $('#QuickCoordinates').val()!='' && $('#QuickCoordinates').val())){
				str+="&zipcode="+$('#QuickZipcode').val();
				str+="&radius=25";
			}
			else if($('#stateCode').val()!=null && $('#stateCode').val()!='' && $('#stateCode').val()){
				str+="&stateabbr="+$('#stateCode').val();
			}
			$(".typeAheadURL").html(str);
		}

	}
	else if(whichCallData == 'secondHLCallData'){
		typeOfGeoInput = 'detectedValue';
		zipCode = hlResponseDataList[7];
		stateCode = hlResponseDataList[9];
		coordinates = hlResponseDataList[10];
		whereBoxVal = hlResponseDataList[11];
		if((hlResponseDataList[8] != null && hlResponseDataList[8] != '') || (hlResponseDataList[9] != null && hlResponseDataList[9] != '')){
			label = hlResponseDataList[8]+', '+ hlResponseDataList[9];
			if(zipCode != null && zipCode != ''){
				$('#QuickZipcode').val(zipCode);
				if(coordinates != null && coordinates !=''){
					$('#QuickCoordinates').val(coordinates);
				}
			}
			else if(stateCode != null && stateCode!= ''){
				$('#stateCode').val(stateCode);
			}
		}
		else if(zipCode != null && zipCode != ''){
			label = hlResponseDataList[7];
			$('#QuickZipcode').val(zipCode);
			$('#QuickCoordinates').val(coordinates);
		}
	}
	$("#hl-autocomplete-search-location").val(label);
	$("#geoMainTypeAheadLastQuickSelectedVal").val(label);
	$('#QuickGeoType').val(typeOfGeoInput);
	$('#geoBoxSearch').val('true');
	$('#originalWhereBoxVal').val(whereBoxVal);
}

function displayLocationRequiredErrorMessage(){
	if($('.dialog-dialogText_preSearchHLDialogBox').find('#errorImage').length==0){
		var errMessage=$('#errorMessageNoSuggestionsSelected').html();
		$('.dialog-dialogText_preSearchHLDialogBox').prepend(errMessage);
	}
	$('.dialog-dialogText_preSearchHLDialogBox').css("display","block");
	autoAdjustTransparentBorderHLSuggesionPopUp();
}

/* IE 10 fix for select dialog box*/
function renderHLQuickSearchModal(){	
	if(ieVersion == 10){		
		var ddquickSearchHLSelection = document.getElementById('quickSearchHLSelection');
		var quickSearchMultipleSelection = document.getElementById('quickSearchMultipleSelection');
		//var increaseHieght = true;
		if (ddquickSearchHLSelection != null && ddquickSearchHLSelection.options.length > 4 ){			
			var heightIE10 = $('.dialog-transparent-border_preSearchHLDialogBox').height() + 50;
			$('.dialog-transparent-border_preSearchHLDialogBox').css("height", heightIE10+"px");
			$('.quickSearch_dropdown').css("height","100px");
		}
		
		if (quickSearchMultipleSelection != null && quickSearchMultipleSelection.options.length >4){
            var heightIE10 = $('.dialog-transparent-border_preSearchHLDialogBox').height() + 50;
			$('.dialog-transparent-border_preSearchHLDialogBox').css("height",heightIE10+"px");
			$('.quickSearchMultiple_dropdown').css("height","100px");
		}
		
	}
}
/* IE 10 fix for select dialog box*/

var isHLDown;
function responseFromHL(whatBoxVal, whereBoxVal, hlResponse){
	var ajaxReturn = false;
	$.ajax( {
		beforeSend:function(){
        loadSpinner()
        },
		type : "GET",
		url : "search/preSearchHLResponseAjax",
		data : 'whatBoxVal= ' + whatBoxVal + '&whereBoxVal=' + whereBoxVal + '&hlResponse=' + hlResponse,
		dataType : "text",
		async: false,
		success : function(response) {
        	hideSpinner();
        	if (response == "") {
        		if(locationDialogBoxFormed){
        			showHLNoLocationDialogBox(whereBoxVal);
        		}
        		else{
        			showHLLocationDialogBox(whereBoxVal);
        		}
        	}
        	else if(response == "HealthLine is Down"){
        		isHLDown = true;
        		showPlanListModal();
        	}
        	else{
        		showPreSearchHLListBox(whereBoxVal,response);
        		if(response.indexOf("selected") != -1){
        			hlContinueButtonSelected();
        		}
        		ajaxReturn = true;
        	}
        },
	});
	if(ieVersion == 10){
		window.setTimeout(function(){renderHLQuickSearchModal();}, 90);
	}
	return ajaxReturn;
}

var isHLQuickSearchClicked = true;
function showPreSearchHLListBox(whereBoxVal, response){
	if(isHLQuickSearchClicked){
		buildPreSearchHLListBox(whereBoxVal, response);
		$('#preSearchHLDialogBox').trigger('show');
		$('#preSearchHLDialogBox').css("display","none");
		if(urlProtocol == urlProtocolNonSecure){
			$('.dialog-content-wrap_preSearchHLDialogBox').css("background-color","#ffffff");
			//$('.dialog-content-wrap_preSearchHLDialogBox').css("border","5px solid #D1D1D1");
			$('.dialog-dialogText_preSearchHLDialogBox').css("padding","0px 10px 10px");
			autoAdjustTransparentBorderHLSuggesionPopUp();
		}
		isHLQuickSearchClicked = false;
	}else{
		changeDivContentAsPerResponse(whereBoxVal, response);
		$('#preSearchHLModalContentTable').html('<tr><td>'+response+'</td></tr>');
		$('#errorLocRequired').html('');
		$('#preSearchHLDialogBox').trigger('show');
		$('#preSearchHLDialogBox').css("display","none");
		if(urlProtocol == urlProtocolNonSecure){
			$('.dialog-content-wrap_preSearchHLDialogBox').css("background-color","#ffffff");
			//$('.dialog-content-wrap_preSearchHLDialogBox').css("border","5px solid #D1D1D1");
			$('.dialog-dialogText_preSearchHLDialogBox').css("padding","0px 10px 10px");
			autoAdjustTransparentBorderHLSuggesionPopUp();
		}
	}
	//508 - Compliance
	setDSEDialogFocus('preSearchHLDialogBox');
}
function showSOFTMessageWarningBox(whatBoxVal){
	$('#softMessageDialog').html($('#softMessageDialogContent').html());
	$('#whatBoxVal').text(whatBoxVal);
	$('#softMessageDialog').doDialogDefault({width:350, modal:true, draggable:true, closeOnEscape:true},
			[{id:"softMessage_OK", value:"Close",url:"", arrow:false}]);

	$('#softMessageDialog.dialog-content').parents('div.dialog-main-wrapper').children('div.dialog-content-wrap').children('div.dialog-title').html('<b>A Message about your search results</b>');
	renderModelButtonForNonSecure();
	$('#softMessageDialog').trigger('show');
	var height = $('#softMessageDialog.dialog-content').parents('div.dialog-main-wrapper').children('div.dialog-transparent-border').height();
	$('#softMessageDialog.dialog-content').parents('div.dialog-main-wrapper').children('div.dialog-transparent-border').css("height",height + 2);
	
	$('#softMessage_OK').bind('click',function(){
		$('#softMessageDialog').trigger('hide');
		return false;
	});
}

var comCallFailBuild = false;
function getComServletPDF(comServletCatCode){
	jQuery.support.cors = true;
	var detailsUrl = window.location.href;
	var isDetailsPage = (detailsUrl != null && detailsUrl.indexOf('search/detail') != -1);
	var proxyUrl;
	if(isDetailsPage){
		proxyUrl = "forDetailsPage/getPDFfromCom";
	}
	else{
		proxyUrl = "search/getPDFfromCom";
	}
    $.ajax({
          beforeSend:function(){
          loadSpinner()
          },
          type : 'GET',
    	  url: proxyUrl,
    	  data : 'categoryCode=' + comServletCatCode,
    	  timeout : 13000,
    	  datatype : 'xml',
    	  success : function(responseXml)
    	  {
        	  hideSpinner();
        	  var pdfURL;
        	  //if(urlProtocol == urlProtocolNonSecure){
        	  if($(responseXml).find('link').text() != null && $(responseXml).find('link').text().length > 0){
        		  pdfURL = $(responseXml).find('link').text();
        	  }
        	  else{
        		  pdfURL =  $($.parseXML(responseXml)).find('link').text();
        	  }
        	  if(pdfURL == null || pdfURL == undefined || pdfURL == ''){
        		  if(comCallFailBuild){
        			  $('#comServletCallFailDialog').trigger('show');
        		  }
        		  else{
        			  showCOMServletCallFailedBox();
        		  }  
        	  }
        	  else{
        		  popUpACO(pdfURL); 
        	  }
    	  },
          error: function(x, t, m) {
        	  hideSpinner();
        	  if(comCallFailBuild){
        		  $('#comServletCallFailDialog').trigger('show');
        	  }
        	  else{
        		  showCOMServletCallFailedBox();
        	  }
          },
  });     
}

function showCOMServletCallFailedBox(){
	comCallFailBuild = true;
	$('#comServletCallFailDialog').html($('#comServletCallFailDialogContent').html());
	$('#comServletCallFailDialog').doDialogDefault({width:350, modal:true, draggable:true, closeOnEscape:true},
			[{id:"comServletCallFail_OK", value:"Close",url:"", arrow:false}]);

	$('#comServletCallFailDialog.dialog-content').parents('div.dialog-main-wrapper').children('div.dialog-content-wrap').children('div.dialog-title').html('<b>We\'re sorry.</b>');
	renderModelButtonForNonSecure();
	$('#comServletCallFailDialog').trigger('show');
	var height = $('#comServletCallFailDialog.dialog-content').parents('div.dialog-main-wrapper').children('div.dialog-transparent-border').height();
	$('#comServletCallFailDialog.dialog-content').parents('div.dialog-main-wrapper').children('div.dialog-transparent-border').css("height",height + 2);
	
	$('#comServletCallFail_OK').bind('click',function(){
		$('#comServletCallFailDialog').trigger('hide');
		return false;
	});
}

function showCOMServletCallFailedBoxDetailsPage(){
	comCallFailBuild = true;
	$('#comServletCallFailDialogDetailsPage').html($('#comServletCallFailDialogDetailsPageContent').html());
	$('#comServletCallFailDialogDetailsPage').doDialogDefault({width:350, modal:true, draggable:true, closeOnEscape:true},
			[{id:"comServletCallFail_OK", value:"Close",url:"", arrow:false}]);

	$('#comServletCallFailDialogDetailsPage.dialog-content').parents('div.dialog-main-wrapper').children('div.dialog-content-wrap').children('div.dialog-title').html('<b>We\'re sorry.</b>');
	renderModelButtonForNonSecure();
	$('#comServletCallFailDialogDetailsPage').trigger('show');
	var height = $('#comServletCallFailDialogDetailsPage.dialog-content').parents('div.dialog-main-wrapper').children('div.dialog-transparent-border').height();
	$('#comServletCallFailDialogDetailsPage.dialog-content').parents('div.dialog-main-wrapper').children('div.dialog-transparent-border').css("height",height + 2);
	
	$('#comServletCallFail_OK').bind('click',function(){
		$('#comServletCallFailDialogDetailsPage').trigger('hide');
		return false;
	});
}

function popUpACO(URL){
	var windowName='popup';
	var winOpts = 'width=900,height=600,scrollbars=yes,resizable=yes,toolbar=yes,overflow=scroll,location=yes,left=180,top=120';
	window.name='INDEX';	
	window.open(URL,windowName,winOpts);
	//aWindow.focus();
}

function handleACOFunctionality(){
	var planLogo = $('#selectedPlanLogoDiv').html();
    if(planLogo != null){
    	var srcLoc = planLogo.indexOf('src=');
    	var closingTagLoc = planLogo.indexOf('>');
    	if (srcLoc > 0 && closingTagLoc > 0){
    		planLogo = planLogo.substring(srcLoc+5, closingTagLoc-1);
    		if(planLogo != null && planLogo != ''){
    			$('#selectedPlanLogoFromArms').html($('#selectedPlanLogoDiv').html());
    			$('#selectedPlanLogoFromArms').css("display","block");
    		}
    		else{
    			$('#selectedPlanLogoFromArms').css("display","none");
    		}
    	}
    }
    var paginationValue = $("#pagination").val();
    if((paginationValue == undefined || paginationValue == '' || paginationValue == '0')){
    	if($('#showSOFTMessageDiv').html() != null && $('#showSOFTMessageDiv').html() == 'true'){
    		//show soft message pop up
    		showSOFTMessageWarningBox($('#searchQuery').val());
    	}
    }
    hidePrintAProvDirectoryOption();
}

function hidePrintAProvDirectoryOption(){
	if(($('#hidePrintAProvDirectoryLeftDiv').html() != null && $('#hidePrintAProvDirectoryLeftDiv').html() == 'true')
		|| ($('#hidePrintAProvDirectoryResultsDiv').html() != null && $('#hidePrintAProvDirectoryResultsDiv').html() == 'true')	
		||($('#hidePrintAProvDirectoryMedDetDiv').html() != null && $('#hidePrintAProvDirectoryMedDetDiv').html() == 'true')
		||($('#hidePrintAProvDirectoryHospDetDiv').html() != null && $('#hidePrintAProvDirectoryHospDetDiv').html() == 'true')
		){
		$('#loginBoxTitleNewDocfindLink').css('display','none');
		//$('#printAProvDirectoryLink').css('display','none');
		$('#printAProvDirectoryLink').remove();
		
	}
	else{
		$('#loginBoxTitleNewDocfindLink').css('display','block');
		$('#printAProvDirectoryLink').css('display','block');
	}
}
/*-- END CHANGES P20751b ACO Branding - n596307 --*/
//508-Compliance
function handlePlanRedirection(planVal){
	if(planVal == "NYEPO|NYC Community Plan"){
		location.href="javascript:popUp('/dse/cms/codeAssets/html/static/NYC_Community_Plan.html')";
	}
	else if(planVal == "SPMA1|Savings Plus of Massachusetts OA Managed Choice" || planVal == "SPMA2|Savings Plus of Massachusetts POSII" ||planVal=="SPMA3|Savings Plus of Massachusetts OA Aetna Select"){
		location.href="javascript:popUp('/dse/cms/codeAssets/html/static/Savings_Plus_of_Massachusetts.html')";
	}
	else if(planVal == "AWHD1|(NC) Aetna Whole Health - Duke Health & WakeMed"){
		location.href="javascript:popUp('/dse/cms/codeAssets/html/dukeACO.html')";
	}

	else if(planVal == "DINDE|Aetna Dental Indemnity Plan"){
		location.href="javascript:popUp('http://www.aetna.com/docfind/custom/AetnaInc/Indemnity.html')";
	}
	else if(planVal == "A9PMC|Aetna Premier Care-Innovation Health"){
		location.href="javascript:popUp('http://www.myplanportal.com/dse/search?site_id=innovationhealth&externalPlanCode=A9PMC|Aetna_Premier_Care_Innovation_Health')";
	}  
	else if(planVal == "MH1AS|Aetna Whole Health(SM)- Memorial Hermann ACN Select" || planVal == "MHEPO|Aetna Whole Health(SM) Memorial Hermann Accountable Care Network"){
		location.href="javascript:popUp('/dse/cms/codeAssets/html/static/Memorial_Herman_Popup.html')";
	}
	else if(planVal == "MSMCA|San Antonio - SmartCare Aetna (Silver)" || planVal == "MSMCA|San Antonio - SmartCare Aetna (Gold)"){
		location.href="javascript:popUp('/dse/cms/codeAssets/html/static/SmartCarePopup.html')";
	}
	else if(planVal == "QHP|Qualified Health Plans")
	{
		location.href="javascript:popUp('/docfind/cms/html/redirectToQhpd.html')";
	}
	else if(planVal == "IVL|Individual Exchange Plans")
	{
		location.href="javascript:popUp('/docfind/cms/html/redirectToIvl.html')";
	}
	else if(planVal == "POAAS|Plan V OA Aetna Select Memorial Hermann Accountable Care Network "){
		location.href="javascript:popUp('/dse/cms/codeAssets/html/static/Memorial_Herman_Popup.html')";
	}
	else if(planVal == "MHOAS|Memorial Hermann Accountable Care Network (Houston)"){
		location.href="javascript:popUp('/docfind/cms/html/Memorial_Herman_Popup.html')";
	}
	else if(planVal == "AMHAS|Aetna Whole Health HSA Memorial Hermann ACN(Houston)"){
		location.href="javascript:popUp('/docfind/cms/html/Memorial_Herman_Popup.html')";
	}
	/*-- START CHANGES Medicare plan display content - n596307 --*/
	else if(planVal == "2016DDP|Delta Dental Plan"){
		if(langPref == 'sp'){
			location.href="javascript:popUp('/dse/search/disclaimer?site_id=medicare&langPref=sp&continueUrl=http://www.deltadentalins.com/aetna')";
		}
		else{
			location.href="javascript:popUp('/dse/search/disclaimer?site_id=medicare&langPref=en&continueUrl=http://www.deltadentalins.com/aetna')";
		}
	}
	
	/*-- END CHANGES Medicare plan display content - n596307 --*/
	else if(planVal == "CMRMT|CMR"){
		location.href="javascript:popUp('/dse/cms/codeAssets/pdf/CMR.pdf')";
	}
	else if(planVal == "A9PMC|Aetna Premier Care Network Plus Innovation Health"){
		location.href="javascript:popUp('/dse/search?site_id=innovationhealth')";
	}
	else if(planVal == "PEBMO|PEBTF Custom HMO"){
		location.href="javascript:popUp('/dse/cms/codeAssets/html/PEBTF.html')";
	}
	else if(planVal == "MPPO|Choice PPO"){
		location.href="javascript:popUp('/dse/cms/codeAssets/html/PEBTF.html')";
	}
	else if(planVal == "MPPO|Bronze Plan"){
		location.href="javascript:popUp('/dse/cms/codeAssets/html/PEBTF.html')";
	}
	else if(planVal == "APOP|Aetna Medicare Prescription Drug Plan (PDP)"){
		displayRxFauxOnPlanSelection('Pharmacies');
	}
	
	else if(planVal == "MEHMO|Aetna MedicareSM Plan (HMO)"){
		location.href="javascript:redirectToStaticPage('http://www.providerlookuponline.com/coventry/po7/gateway.aspx?plancode=187&clientprodcode=118752&site_mode=2')";
	}
	else if(planVal == "MEHMO|Aetna Medicare Value Plan (HMO) 2017"){
		location.href="javascript:redirectToStaticPage('http://www.providerlookuponline.com/coventry/po7/gateway.aspx?plancode=187&clientprodcode=118749&site_mode=2')";
	}
	else if(planVal == "MEHMO|Aetna Medicare Premier Plan (HMO) 2017"){
		location.href="javascript:redirectToStaticPage('http://www.providerlookuponline.com/coventry/po7/gateway.aspx?plancode=187&clientprodcode=118750&site_mode=2')";
	}
	else if(planVal == "MEHMO|Aetna Medicare Select Plan (HMO)"){
		location.href="javascript:redirectToStaticPage('http://www.providerlookuponline.com/coventry/po7/gateway.aspx?plancode=187&clientprodcode=118754&site_mode=2')";
	}
	else if(planVal == "MEDSNP|Aetna Medicare Maximum Plan (HMO SNP)"){
		location.href="javascript:redirectToStaticPage('http://www.providerlookuponline.com/coventry/po7/gateway.aspx?plancode=187&clientprodcode=118753&site_mode=2')";
	}
	else if(planVal == "APCN|Aetna Premier Care Network Plus Basic Plan"){
		popUp('/dse/cms/codeAssets/html/tyco_popup.html');
		location.href="javascript:redirectToStaticPage('http://www.aetna.com/dse/search?site_id=dse')";
	}
	else if(planVal == "APCN|Aetna Premier Care Network Plus Consumer Plan"){
		popUp('/dse/cms/codeAssets/html/tyco_popup.html');
		location.href="javascript:redirectToStaticPage('http://www.aetna.com/dse/search?site_id=dse')";
	}
	
	else if(planVal == "A13MC|Aetna Premier Care Network Plus Catholic Health Initiatives"){
		
		location.href="javascript:popUp('/dse/cms/codeAssets/html/APCN_2017.html')";
	}
	else if(planVal == "A14MC|Aetna Premier Care Network Plus Integris Network"){
		
		location.href="javascript:popUp('/dse/cms/codeAssets/html/APCN_2017.html')";
	}
	else if(planVal == "A15MC|Aetna Premier Care Network Plus Quality Partners In Care"){
		
		location.href="javascript:popUp('/dse/cms/codeAssets/html/APCN_2017.html')";
	}
	
	/*-- Start changes P23046a SEP-2015 - N709197 --*/
	else if(planVal == "EPOD|MA EPO Dental" || planVal == "PPOD|MA PPO Dental"){
		displayDentalFauxRwOnPlanSelection('Dentist');
		/*if(langPref == 'sp'){
			location.href="javascript:popUp('/dse/search/disclaimer?site_id=medicare&langPref=sp&continueUrl=https://www.sslws.net/ProviderSearch/Search.aspx?logo=aethmppo&s=aethmppo')";
		}
		else{
			location.href="javascript:popUp('/dse/search/disclaimer?site_id=medicare&langPref=en&continueUrl=https://www.sslws.net/ProviderSearch/Search.aspx?logo=aethmppo&s=aethmppo')";
		}*/
	}
	/*-- End changes P23046a SEP-2015 - N709197 --*/
	if($('#site_id').val()!=null && $('#site_id').val()!=undefined && $('#site_id').val() == 'mymeritain'){
		if(planVal == "ABC|V-BENN"){
			location.href="javascript:popUp('/dse/cms/codeAssets/html/static/vbenn_plan_popup.html')";
		}
	}
	
	else if($('#site_id').val()!=null && $('#site_id').val()!=undefined && $('#site_id').val() == "trsactivecare"){	
		if(planVal == "OAAS|ActiveCare Select" || planVal == "SHAAS|Seton Health Alliance (Austin)" || planVal == "BSAAS|Baylor Scott & White Quality Alliance (DFW Region)" || planVal == "BHSAS|Baptist Health System and HealthTexas Medical Group (San Antonio)" || planVal == "RMPPO|Behavioral Healthcare Program")
		{
			location.href="javascript:popUp('/docfind/cms/html/TRS_ActiveCare_select_popup1.html')";
		}
	}
	
	else if($('#site_id').val()!=null && $('#site_id').val()!=undefined && $('#site_id').val() == 'ivl'){
		if(planVal == "NYDEP|Gold $10 Copay EPO NY SignatureSM PD:Gold $10 Copay EPO NY SignatureSM C/O:Gold $10 Copay EPO NY SignatureSM DEP 30:Platinum $5 Copay EPO NY SignatureSM PD:Platinum $5 Copay EPO NY SignatureSM C/O:Platinum $5 Copay EPO NY SignatureSM DEP 30:Silver $20 Copay EPO NY SignatureSM PD:Silver $20 Copay EPO NY SignatureSM C/O:Silver $20 Copay EPO NY SignatureSM DEP 30:Bronze Deductible Only EPO NY SignatureSM PD:Bronze Deductible Only EPO NY SignatureSM C/O:Bronze Deductible Only EPO NY SignatureSM DEP 30_PLANHEADER_New York Elect Choice w/Pediatric Dental (For Qualified Conversion Plan Members Only)_PLANPREFILL_New York Elect Choice w/Pediatric Dental (For Qualified Conversion Plan Members Only)"
			|| planVal == "NYDEP|Gold $10 Copay EPO NY SignatureSM PD:Gold $10 Copay EPO NY SignatureSM C/O:Gold $10 Copay EPO NY SignatureSM DEP 30:Platinum $5 Copay EPO NY SignatureSM PD:Platinum $5 Copay EPO NY SignatureSM C/O:Platinum $5 Copay EPO NY SignatureSM DEP 30:Silver $20 Copay EPO NY SignatureSM PD:Silver $20 Copay EPO NY SignatureSM C/O:Silver $20 Copay EPO NY SignatureSM DEP 30:Bronze Deductible Only EPO NY SignatureSM PD:Bronze Deductible Only EPO NY SignatureSM C/O:Bronze Deductible Only EPO NY SignatureSM DEP 30_PLANHEADER_New York Elect Choice w/Pediatric Dental (For Qualified Conversion Plan Members Only)_PLANPREFILL_Gold $10 Copay EPO NY SignatureSM PD"
				|| planVal == "NYDEP|Gold $10 Copay EPO NY SignatureSM PD:Gold $10 Copay EPO NY SignatureSM C/O:Gold $10 Copay EPO NY SignatureSM DEP 30:Platinum $5 Copay EPO NY SignatureSM PD:Platinum $5 Copay EPO NY SignatureSM C/O:Platinum $5 Copay EPO NY SignatureSM DEP 30:Silver $20 Copay EPO NY SignatureSM PD:Silver $20 Copay EPO NY SignatureSM C/O:Silver $20 Copay EPO NY SignatureSM DEP 30:Bronze Deductible Only EPO NY SignatureSM PD:Bronze Deductible Only EPO NY SignatureSM C/O:Bronze Deductible Only EPO NY SignatureSM DEP 30_PLANHEADER_New York Elect Choice w/Pediatric Dental (For Qualified Conversion Plan Members Only)_PLANPREFILL_Gold $10 Copay EPO NY SignatureSM C/O"
					|| planVal == "NYDEP|Gold $10 Copay EPO NY SignatureSM PD:Gold $10 Copay EPO NY SignatureSM C/O:Gold $10 Copay EPO NY SignatureSM DEP 30:Platinum $5 Copay EPO NY SignatureSM PD:Platinum $5 Copay EPO NY SignatureSM C/O:Platinum $5 Copay EPO NY SignatureSM DEP 30:Silver $20 Copay EPO NY SignatureSM PD:Silver $20 Copay EPO NY SignatureSM C/O:Silver $20 Copay EPO NY SignatureSM DEP 30:Bronze Deductible Only EPO NY SignatureSM PD:Bronze Deductible Only EPO NY SignatureSM C/O:Bronze Deductible Only EPO NY SignatureSM DEP 30_PLANHEADER_New York Elect Choice w/Pediatric Dental (For Qualified Conversion Plan Members Only)_PLANPREFILL_Gold $10 Copay EPO NY SignatureSM DEP 30"
						|| planVal == "NYDEP|Gold $10 Copay EPO NY SignatureSM PD:Gold $10 Copay EPO NY SignatureSM C/O:Gold $10 Copay EPO NY SignatureSM DEP 30:Platinum $5 Copay EPO NY SignatureSM PD:Platinum $5 Copay EPO NY SignatureSM C/O:Platinum $5 Copay EPO NY SignatureSM DEP 30:Silver $20 Copay EPO NY SignatureSM PD:Silver $20 Copay EPO NY SignatureSM C/O:Silver $20 Copay EPO NY SignatureSM DEP 30:Bronze Deductible Only EPO NY SignatureSM PD:Bronze Deductible Only EPO NY SignatureSM C/O:Bronze Deductible Only EPO NY SignatureSM DEP 30_PLANHEADER_New York Elect Choice w/Pediatric Dental (For Qualified Conversion Plan Members Only)_PLANPREFILL_Platinum $5 Copay EPO NY SignatureSM PD"
							|| planVal == "NYDEP|Gold $10 Copay EPO NY SignatureSM PD:Gold $10 Copay EPO NY SignatureSM C/O:Gold $10 Copay EPO NY SignatureSM DEP 30:Platinum $5 Copay EPO NY SignatureSM PD:Platinum $5 Copay EPO NY SignatureSM C/O:Platinum $5 Copay EPO NY SignatureSM DEP 30:Silver $20 Copay EPO NY SignatureSM PD:Silver $20 Copay EPO NY SignatureSM C/O:Silver $20 Copay EPO NY SignatureSM DEP 30:Bronze Deductible Only EPO NY SignatureSM PD:Bronze Deductible Only EPO NY SignatureSM C/O:Bronze Deductible Only EPO NY SignatureSM DEP 30_PLANHEADER_New York Elect Choice w/Pediatric Dental (For Qualified Conversion Plan Members Only)_PLANPREFILL_Platinum $5 Copay EPO NY SignatureSM C/O"
								|| planVal == "NYDEP|Gold $10 Copay EPO NY SignatureSM PD:Gold $10 Copay EPO NY SignatureSM C/O:Gold $10 Copay EPO NY SignatureSM DEP 30:Platinum $5 Copay EPO NY SignatureSM PD:Platinum $5 Copay EPO NY SignatureSM C/O:Platinum $5 Copay EPO NY SignatureSM DEP 30:Silver $20 Copay EPO NY SignatureSM PD:Silver $20 Copay EPO NY SignatureSM C/O:Silver $20 Copay EPO NY SignatureSM DEP 30:Bronze Deductible Only EPO NY SignatureSM PD:Bronze Deductible Only EPO NY SignatureSM C/O:Bronze Deductible Only EPO NY SignatureSM DEP 30_PLANHEADER_New York Elect Choice w/Pediatric Dental (For Qualified Conversion Plan Members Only)_PLANPREFILL_Platinum $5 Copay EPO NY SignatureSM DEP 30"
									|| planVal == "NYDEP|Gold $10 Copay EPO NY SignatureSM PD:Gold $10 Copay EPO NY SignatureSM C/O:Gold $10 Copay EPO NY SignatureSM DEP 30:Platinum $5 Copay EPO NY SignatureSM PD:Platinum $5 Copay EPO NY SignatureSM C/O:Platinum $5 Copay EPO NY SignatureSM DEP 30:Silver $20 Copay EPO NY SignatureSM PD:Silver $20 Copay EPO NY SignatureSM C/O:Silver $20 Copay EPO NY SignatureSM DEP 30:Bronze Deductible Only EPO NY SignatureSM PD:Bronze Deductible Only EPO NY SignatureSM C/O:Bronze Deductible Only EPO NY SignatureSM DEP 30_PLANHEADER_New York Elect Choice w/Pediatric Dental (For Qualified Conversion Plan Members Only)_PLANPREFILL_Silver $20 Copay EPO NY SignatureSM PD"
										|| planVal == "NYDEP|Gold $10 Copay EPO NY SignatureSM PD:Gold $10 Copay EPO NY SignatureSM C/O:Gold $10 Copay EPO NY SignatureSM DEP 30:Platinum $5 Copay EPO NY SignatureSM PD:Platinum $5 Copay EPO NY SignatureSM C/O:Platinum $5 Copay EPO NY SignatureSM DEP 30:Silver $20 Copay EPO NY SignatureSM PD:Silver $20 Copay EPO NY SignatureSM C/O:Silver $20 Copay EPO NY SignatureSM DEP 30:Bronze Deductible Only EPO NY SignatureSM PD:Bronze Deductible Only EPO NY SignatureSM C/O:Bronze Deductible Only EPO NY SignatureSM DEP 30_PLANHEADER_New York Elect Choice w/Pediatric Dental (For Qualified Conversion Plan Members Only)_PLANPREFILL_Silver $20 Copay EPO NY SignatureSM C/O"
											|| planVal == "NYDEP|Gold $10 Copay EPO NY SignatureSM PD:Gold $10 Copay EPO NY SignatureSM C/O:Gold $10 Copay EPO NY SignatureSM DEP 30:Platinum $5 Copay EPO NY SignatureSM PD:Platinum $5 Copay EPO NY SignatureSM C/O:Platinum $5 Copay EPO NY SignatureSM DEP 30:Silver $20 Copay EPO NY SignatureSM PD:Silver $20 Copay EPO NY SignatureSM C/O:Silver $20 Copay EPO NY SignatureSM DEP 30:Bronze Deductible Only EPO NY SignatureSM PD:Bronze Deductible Only EPO NY SignatureSM C/O:Bronze Deductible Only EPO NY SignatureSM DEP 30_PLANHEADER_New York Elect Choice w/Pediatric Dental (For Qualified Conversion Plan Members Only)_PLANPREFILL_Silver $20 Copay EPO NY SignatureSM DEP 30"
												|| planVal == "NYDEP|Gold $10 Copay EPO NY SignatureSM PD:Gold $10 Copay EPO NY SignatureSM C/O:Gold $10 Copay EPO NY SignatureSM DEP 30:Platinum $5 Copay EPO NY SignatureSM PD:Platinum $5 Copay EPO NY SignatureSM C/O:Platinum $5 Copay EPO NY SignatureSM DEP 30:Silver $20 Copay EPO NY SignatureSM PD:Silver $20 Copay EPO NY SignatureSM C/O:Silver $20 Copay EPO NY SignatureSM DEP 30:Bronze Deductible Only EPO NY SignatureSM PD:Bronze Deductible Only EPO NY SignatureSM C/O:Bronze Deductible Only EPO NY SignatureSM DEP 30_PLANHEADER_New York Elect Choice w/Pediatric Dental (For Qualified Conversion Plan Members Only)_PLANPREFILL_Bronze Deductible Only EPO NY SignatureSM PD"
													|| planVal == "NYDEP|Gold $10 Copay EPO NY SignatureSM PD:Gold $10 Copay EPO NY SignatureSM C/O:Gold $10 Copay EPO NY SignatureSM DEP 30:Platinum $5 Copay EPO NY SignatureSM PD:Platinum $5 Copay EPO NY SignatureSM C/O:Platinum $5 Copay EPO NY SignatureSM DEP 30:Silver $20 Copay EPO NY SignatureSM PD:Silver $20 Copay EPO NY SignatureSM C/O:Silver $20 Copay EPO NY SignatureSM DEP 30:Bronze Deductible Only EPO NY SignatureSM PD:Bronze Deductible Only EPO NY SignatureSM C/O:Bronze Deductible Only EPO NY SignatureSM DEP 30_PLANHEADER_New York Elect Choice w/Pediatric Dental (For Qualified Conversion Plan Members Only)_PLANPREFILL_Bronze Deductible Only EPO NY SignatureSM C/O"
														|| planVal == "NYDEP|Gold $10 Copay EPO NY SignatureSM PD:Gold $10 Copay EPO NY SignatureSM C/O:Gold $10 Copay EPO NY SignatureSM DEP 30:Platinum $5 Copay EPO NY SignatureSM PD:Platinum $5 Copay EPO NY SignatureSM C/O:Platinum $5 Copay EPO NY SignatureSM DEP 30:Silver $20 Copay EPO NY SignatureSM PD:Silver $20 Copay EPO NY SignatureSM C/O:Silver $20 Copay EPO NY SignatureSM DEP 30:Bronze Deductible Only EPO NY SignatureSM PD:Bronze Deductible Only EPO NY SignatureSM C/O:Bronze Deductible Only EPO NY SignatureSM DEP 30_PLANHEADER_New York Elect Choice w/Pediatric Dental (For Qualified Conversion Plan Members Only)_PLANPREFILL_Bronze Deductible Only EPO NY SignatureSM DEP 30"){
			location.href="javascript:popUp('/docfind/cms/html/ivl_ny_plan_popup.html')";
		}
		else if(planVal == "LEAP1|Aetna Leap Everyday - Banner:Aetna Leap Everyday Plus - Banner:Aetna Leap Basic Plus - Banner:Aetna Leap Basic - Banner:Aetna Leap Basic HSA - Banner:Aetna Leap Specialty - Banner:Aetna Leap Diabetes - Banner_PLANHEADER_Arizona Banner Health Network Only Open Access w/Pediatric Dental_PLANPREFILL_Arizona Banner Health Network Only Open Access w/Pediatric Dental" 
			|| planVal == "LEAP1|Aetna Leap Everyday - Banner:Aetna Leap Everyday Plus - Banner:Aetna Leap Basic Plus - Banner:Aetna Leap Basic - Banner:Aetna Leap Basic HSA - Banner:Aetna Leap Specialty - Banner:Aetna Leap Diabetes - Banner_PLANHEADER_Arizona Banner Health Network Only Open Access w/Pediatric Dental_PLANPREFILL_Aetna Leap Everyday - Banner"
				|| planVal == "LEAP1|Aetna Leap Everyday - Banner:Aetna Leap Everyday Plus - Banner:Aetna Leap Basic Plus - Banner:Aetna Leap Basic - Banner:Aetna Leap Basic HSA - Banner:Aetna Leap Specialty - Banner:Aetna Leap Diabetes - Banner_PLANHEADER_Arizona Banner Health Network Only Open Access w/Pediatric Dental_PLANPREFILL_Aetna Leap Everyday Plus - Banner"
					|| planVal == "LEAP1|Aetna Leap Everyday - Banner:Aetna Leap Everyday Plus - Banner:Aetna Leap Basic Plus - Banner:Aetna Leap Basic - Banner:Aetna Leap Basic HSA - Banner:Aetna Leap Specialty - Banner:Aetna Leap Diabetes - Banner_PLANHEADER_Arizona Banner Health Network Only Open Access w/Pediatric Dental_PLANPREFILL_Aetna Leap Basic Plus - Banner"	
						|| planVal == "LEAP1|Aetna Leap Everyday - Banner:Aetna Leap Everyday Plus - Banner:Aetna Leap Basic Plus - Banner:Aetna Leap Basic - Banner:Aetna Leap Basic HSA - Banner:Aetna Leap Specialty - Banner:Aetna Leap Diabetes - Banner_PLANHEADER_Arizona Banner Health Network Only Open Access w/Pediatric Dental_PLANPREFILL_Aetna Leap Basic - Banner"
							|| planVal == "LEAP1|Aetna Leap Everyday - Banner:Aetna Leap Everyday Plus - Banner:Aetna Leap Basic Plus - Banner:Aetna Leap Basic - Banner:Aetna Leap Basic HSA - Banner:Aetna Leap Specialty - Banner:Aetna Leap Diabetes - Banner_PLANHEADER_Arizona Banner Health Network Only Open Access w/Pediatric Dental_PLANPREFILL_Aetna Leap Basic HSA - Banner"
								|| planVal == "LEAP1|Aetna Leap Everyday - Banner:Aetna Leap Everyday Plus - Banner:Aetna Leap Basic Plus - Banner:Aetna Leap Basic - Banner:Aetna Leap Basic HSA - Banner:Aetna Leap Specialty - Banner:Aetna Leap Diabetes - Banner_PLANHEADER_Arizona Banner Health Network Only Open Access w/Pediatric Dental_PLANPREFILL_Aetna Leap Specialty - Banner"
									|| planVal == "LEAP1|Aetna Leap Everyday - Banner:Aetna Leap Everyday Plus - Banner:Aetna Leap Basic Plus - Banner:Aetna Leap Basic - Banner:Aetna Leap Basic HSA - Banner:Aetna Leap Specialty - Banner:Aetna Leap Diabetes - Banner_PLANHEADER_Arizona Banner Health Network Only Open Access w/Pediatric Dental_PLANPREFILL_Aetna Leap Diabetes - Banner"){
			location.href="https://my.aetna.com/#/login?public-search";
		}
		else if(planVal == "LEAP2|Aetna Leap Everyday - Carolinas HealthCare System:Aetna Leap Everyday Plus - Carolinas HealthCare System:Aetna Leap Basic Plus - Carolinas HealthCare System:Aetna Leap Basic HSA - Carolinas HealthCare System:Aetna Leap Diabetes - Carolinas HealthCare System:Aetna Leap Specialty - Carolinas HealthCare System_PLANHEADER_North Carolina Health Network Only Open Access Carolinas HealthCare w/Pediatric Dental_PLANPREFILL_North Carolina Health Network Only Open Access Carolinas HealthCare w/Pediatric Dental"
			|| planVal == "LEAP2|Aetna Leap Everyday - Carolinas HealthCare System:Aetna Leap Everyday Plus - Carolinas HealthCare System:Aetna Leap Basic Plus - Carolinas HealthCare System:Aetna Leap Basic HSA - Carolinas HealthCare System:Aetna Leap Diabetes - Carolinas HealthCare System:Aetna Leap Specialty - Carolinas HealthCare System_PLANHEADER_North Carolina Health Network Only Open Access Carolinas HealthCare w/Pediatric Dental_PLANPREFILL_Aetna Leap Everyday - Carolinas HealthCare System"
				|| planVal == "LEAP2|Aetna Leap Everyday - Carolinas HealthCare System:Aetna Leap Everyday Plus - Carolinas HealthCare System:Aetna Leap Basic Plus - Carolinas HealthCare System:Aetna Leap Basic HSA - Carolinas HealthCare System:Aetna Leap Diabetes - Carolinas HealthCare System:Aetna Leap Specialty - Carolinas HealthCare System_PLANHEADER_North Carolina Health Network Only Open Access Carolinas HealthCare w/Pediatric Dental_PLANPREFILL_Aetna Leap Everyday Plus - Carolinas HealthCare System"
					|| planVal == "LEAP2|Aetna Leap Everyday - Carolinas HealthCare System:Aetna Leap Everyday Plus - Carolinas HealthCare System:Aetna Leap Basic Plus - Carolinas HealthCare System:Aetna Leap Basic HSA - Carolinas HealthCare System:Aetna Leap Diabetes - Carolinas HealthCare System:Aetna Leap Specialty - Carolinas HealthCare System_PLANHEADER_North Carolina Health Network Only Open Access Carolinas HealthCare w/Pediatric Dental_PLANPREFILL_Aetna Leap Basic Plus - Carolinas HealthCare System"
						|| planVal == "LEAP2|Aetna Leap Everyday - Carolinas HealthCare System:Aetna Leap Everyday Plus - Carolinas HealthCare System:Aetna Leap Basic Plus - Carolinas HealthCare System:Aetna Leap Basic HSA - Carolinas HealthCare System:Aetna Leap Diabetes - Carolinas HealthCare System:Aetna Leap Specialty - Carolinas HealthCare System_PLANHEADER_North Carolina Health Network Only Open Access Carolinas HealthCare w/Pediatric Dental_PLANPREFILL_Aetna Leap Basic HSA - Carolinas HealthCare System"
							|| planVal == "LEAP2|Aetna Leap Everyday - Carolinas HealthCare System:Aetna Leap Everyday Plus - Carolinas HealthCare System:Aetna Leap Basic Plus - Carolinas HealthCare System:Aetna Leap Basic HSA - Carolinas HealthCare System:Aetna Leap Diabetes - Carolinas HealthCare System:Aetna Leap Specialty - Carolinas HealthCare System_PLANHEADER_North Carolina Health Network Only Open Access Carolinas HealthCare w/Pediatric Dental_PLANPREFILL_Aetna Leap Diabetes - Carolinas HealthCare System"
								|| planVal == "LEAP2|Aetna Leap Everyday - Carolinas HealthCare System:Aetna Leap Everyday Plus - Carolinas HealthCare System:Aetna Leap Basic Plus - Carolinas HealthCare System:Aetna Leap Basic HSA - Carolinas HealthCare System:Aetna Leap Diabetes - Carolinas HealthCare System:Aetna Leap Specialty - Carolinas HealthCare System_PLANHEADER_North Carolina Health Network Only Open Access Carolinas HealthCare w/Pediatric Dental_PLANPREFILL_Aetna Leap Specialty - Carolinas HealthCare System"){
			//Mona
			location.href="https://my.aetna.com/#/login?public-search";
		}
		else if(planVal == "LEAP3|Aetna Leap Everyday - CaroMont Health:Aetna Leap Everyday Plus - CaroMont Health:Aetna Leap Basic Plus - CaroMont Health:Aetna Leap Basic HSA - CaroMont Health:Aetna Leap Diabetes - CaroMont Health:Aetna Leap Specialty - CaroMont Health_PLANHEADER_North Carolina Health Network Only Open Access CaroMont w/Pediatric Dental_PLANPREFILL_North Carolina Health Network Only Open Access CaroMont w/Pediatric Dental"
			|| planVal == "LEAP3|Aetna Leap Everyday - CaroMont Health:Aetna Leap Everyday Plus - CaroMont Health:Aetna Leap Basic Plus - CaroMont Health:Aetna Leap Basic HSA - CaroMont Health:Aetna Leap Diabetes - CaroMont Health:Aetna Leap Specialty - CaroMont Health_PLANHEADER_North Carolina Health Network Only Open Access CaroMont w/Pediatric Dental_PLANPREFILL_Aetna Leap Everyday - CaroMont Health"
				|| planVal == "LEAP3|Aetna Leap Everyday - CaroMont Health:Aetna Leap Everyday Plus - CaroMont Health:Aetna Leap Basic Plus - CaroMont Health:Aetna Leap Basic HSA - CaroMont Health:Aetna Leap Diabetes - CaroMont Health:Aetna Leap Specialty - CaroMont Health_PLANHEADER_North Carolina Health Network Only Open Access CaroMont w/Pediatric Dental_PLANPREFILL_Aetna Leap Everyday Plus - CaroMont Health"
					|| planVal == "LEAP3|Aetna Leap Everyday - CaroMont Health:Aetna Leap Everyday Plus - CaroMont Health:Aetna Leap Basic Plus - CaroMont Health:Aetna Leap Basic HSA - CaroMont Health:Aetna Leap Diabetes - CaroMont Health:Aetna Leap Specialty - CaroMont Health_PLANHEADER_North Carolina Health Network Only Open Access CaroMont w/Pediatric Dental_PLANPREFILL_Aetna Leap Basic Plus - CaroMont Health"
						|| planVal == "LEAP3|Aetna Leap Everyday - CaroMont Health:Aetna Leap Everyday Plus - CaroMont Health:Aetna Leap Basic Plus - CaroMont Health:Aetna Leap Basic HSA - CaroMont Health:Aetna Leap Diabetes - CaroMont Health:Aetna Leap Specialty - CaroMont Health_PLANHEADER_North Carolina Health Network Only Open Access CaroMont w/Pediatric Dental_PLANPREFILL_Aetna Leap Basic HSA - CaroMont Health"
							|| planVal == "LEAP3|Aetna Leap Everyday - CaroMont Health:Aetna Leap Everyday Plus - CaroMont Health:Aetna Leap Basic Plus - CaroMont Health:Aetna Leap Basic HSA - CaroMont Health:Aetna Leap Diabetes - CaroMont Health:Aetna Leap Specialty - CaroMont Health_PLANHEADER_North Carolina Health Network Only Open Access CaroMont w/Pediatric Dental_PLANPREFILL_Aetna Leap Diabetes - CaroMont Health"
								|| planVal == "LEAP3|Aetna Leap Everyday - CaroMont Health:Aetna Leap Everyday Plus - CaroMont Health:Aetna Leap Basic Plus - CaroMont Health:Aetna Leap Basic HSA - CaroMont Health:Aetna Leap Diabetes - CaroMont Health:Aetna Leap Specialty - CaroMont Health_PLANHEADER_North Carolina Health Network Only Open Access CaroMont w/Pediatric Dental_PLANPREFILL_Aetna Leap Specialty - CaroMont Health"){
			location.href="https://my.aetna.com/#/login?public-search";
		}
		else if(planVal == "LEAP8|Aetna Leap Catastrophic - Carolinas HealthCare System_PLANHEADER_North Carolina Health Network Only Open Access Carolinas HealthCare Catastrophic w/Pediatric Dental_PLANPREFILL_North Carolina Health Network Only Open Access Carolinas HealthCare Catastrophic w/Pediatric Dental"
			|| planVal == "LEAP8|Aetna Leap Catastrophic - Carolinas HealthCare System_PLANHEADER_North Carolina Health Network Only Open Access Carolinas HealthCare Catastrophic w/Pediatric Dental_PLANPREFILL_Aetna Leap Catastrophic - Carolinas HealthCare System"){
			location.href="https://my.aetna.com/#/login?public-search";
		}
		else if(planVal == "LEAP8|Aetna Leap Catastrophic - CaroMont Health_PLANHEADER_North Carolina Health Network Only Open Access CaroMont Catastrophic w/Pediatric Dental_PLANPREFILL_North Carolina Health Network Only Open Access CaroMont Catastrophic w/Pediatric Dental"
			|| planVal == "LEAP8|Aetna Leap Catastrophic - CaroMont Health_PLANHEADER_North Carolina Health Network Only Open Access CaroMont Catastrophic w/Pediatric Dental_PLANPREFILL_Aetna Leap Catastrophic - CaroMont Health"){
			location.href="https://my.aetna.com/#/login?public-search";
		}
		else if(planVal == "LEAP6|Aetna Leap Everyday:Aetna Leap Everyday Plus:Aetna Leap Basic:Aetna Leap Basic Plus:Aetna Leap Basic HSA:Aetna Leap Specialty:Aetna Leap Diabetes_PLANHEADER_Pennsylvania Savings Plus Health Network Only w/Pediatric Dental_PLANPREFILL_Pennsylvania Savings Plus Health Network Only w/Pediatric Dental"
			|| planVal == "LEAP6|Aetna Leap Everyday:Aetna Leap Everyday Plus:Aetna Leap Basic:Aetna Leap Basic Plus:Aetna Leap Basic HSA:Aetna Leap Specialty:Aetna Leap Diabetes_PLANHEADER_Pennsylvania Savings Plus Health Network Only w/Pediatric Dental_PLANPREFILL_Aetna Leap Everyday"
				|| planVal == "LEAP6|Aetna Leap Everyday:Aetna Leap Everyday Plus:Aetna Leap Basic:Aetna Leap Basic Plus:Aetna Leap Basic HSA:Aetna Leap Specialty:Aetna Leap Diabetes_PLANHEADER_Pennsylvania Savings Plus Health Network Only w/Pediatric Dental_PLANPREFILL_Aetna Leap Everyday Plus"
					|| planVal == "LEAP6|Aetna Leap Everyday:Aetna Leap Everyday Plus:Aetna Leap Basic:Aetna Leap Basic Plus:Aetna Leap Basic HSA:Aetna Leap Specialty:Aetna Leap Diabetes_PLANHEADER_Pennsylvania Savings Plus Health Network Only w/Pediatric Dental_PLANPREFILL_Aetna Leap Basic"
						|| planVal == "LEAP6|Aetna Leap Everyday:Aetna Leap Everyday Plus:Aetna Leap Basic:Aetna Leap Basic Plus:Aetna Leap Basic HSA:Aetna Leap Specialty:Aetna Leap Diabetes_PLANHEADER_Pennsylvania Savings Plus Health Network Only w/Pediatric Dental_PLANPREFILL_Aetna Leap Basic Plus"
							|| planVal == "LEAP6|Aetna Leap Everyday:Aetna Leap Everyday Plus:Aetna Leap Basic:Aetna Leap Basic Plus:Aetna Leap Basic HSA:Aetna Leap Specialty:Aetna Leap Diabetes_PLANHEADER_Pennsylvania Savings Plus Health Network Only w/Pediatric Dental_PLANPREFILL_Aetna Leap Basic HSA"
								|| planVal == "LEAP6|Aetna Leap Everyday:Aetna Leap Everyday Plus:Aetna Leap Basic:Aetna Leap Basic Plus:Aetna Leap Basic HSA:Aetna Leap Specialty:Aetna Leap Diabetes_PLANHEADER_Pennsylvania Savings Plus Health Network Only w/Pediatric Dental_PLANPREFILL_Aetna Leap Specialty"
									|| planVal == "LEAP6|Aetna Leap Everyday:Aetna Leap Everyday Plus:Aetna Leap Basic:Aetna Leap Basic Plus:Aetna Leap Basic HSA:Aetna Leap Specialty:Aetna Leap Diabetes_PLANHEADER_Pennsylvania Savings Plus Health Network Only w/Pediatric Dental_PLANPREFILL_Aetna Leap Diabetes"){
			location.href="https://my.aetna.com/#/login?public-search";
		}
		else if(planVal == "LEAP7|Aetna Leap Everyday - Carolinas HealthCare System:Aetna Leap Everyday Plus - Carolinas HealthCare System:Aetna Leap Basic Plus - Carolinas HealthCare System:Aetna Leap Basic HSA - Carolinas HealthCare System:Aetna Leap Diabetes - Carolinas HealthCare System:Aetna Leap Specialty - Carolinas HealthCare System_PLANHEADER_South Carolina Health Network Only Open Access - Carolinas HealthCare w/Pediatric Dental_PLANPREFILL_South Carolina Health Network Only Open Access - Carolinas HealthCare w/Pediatric Dental"
			|| planVal == "LEAP7|Aetna Leap Everyday - Carolinas HealthCare System:Aetna Leap Everyday Plus - Carolinas HealthCare System:Aetna Leap Basic Plus - Carolinas HealthCare System:Aetna Leap Basic HSA - Carolinas HealthCare System:Aetna Leap Diabetes - Carolinas HealthCare System:Aetna Leap Specialty - Carolinas HealthCare System_PLANHEADER_South Carolina Health Network Only Open Access - Carolinas HealthCare w/Pediatric Dental_PLANPREFILL_Aetna Leap Everyday - Carolinas HealthCare System"
				|| planVal == "LEAP7|Aetna Leap Everyday - Carolinas HealthCare System:Aetna Leap Everyday Plus - Carolinas HealthCare System:Aetna Leap Basic Plus - Carolinas HealthCare System:Aetna Leap Basic HSA - Carolinas HealthCare System:Aetna Leap Diabetes - Carolinas HealthCare System:Aetna Leap Specialty - Carolinas HealthCare System_PLANHEADER_South Carolina Health Network Only Open Access - Carolinas HealthCare w/Pediatric Dental_PLANPREFILL_Aetna Leap Everyday Plus - Carolinas HealthCare System"
					|| planVal == "LEAP7|Aetna Leap Everyday - Carolinas HealthCare System:Aetna Leap Everyday Plus - Carolinas HealthCare System:Aetna Leap Basic Plus - Carolinas HealthCare System:Aetna Leap Basic HSA - Carolinas HealthCare System:Aetna Leap Diabetes - Carolinas HealthCare System:Aetna Leap Specialty - Carolinas HealthCare System_PLANHEADER_South Carolina Health Network Only Open Access - Carolinas HealthCare w/Pediatric Dental_PLANPREFILL_Aetna Leap Basic Plus - Carolinas HealthCare System"
						|| planVal == "LEAP7|Aetna Leap Everyday - Carolinas HealthCare System:Aetna Leap Everyday Plus - Carolinas HealthCare System:Aetna Leap Basic Plus - Carolinas HealthCare System:Aetna Leap Basic HSA - Carolinas HealthCare System:Aetna Leap Diabetes - Carolinas HealthCare System:Aetna Leap Specialty - Carolinas HealthCare System_PLANHEADER_South Carolina Health Network Only Open Access - Carolinas HealthCare w/Pediatric Dental_PLANPREFILL_Aetna Leap Basic HSA - Carolinas HealthCare System"
							|| planVal == "LEAP7|Aetna Leap Everyday - Carolinas HealthCare System:Aetna Leap Everyday Plus - Carolinas HealthCare System:Aetna Leap Basic Plus - Carolinas HealthCare System:Aetna Leap Basic HSA - Carolinas HealthCare System:Aetna Leap Diabetes - Carolinas HealthCare System:Aetna Leap Specialty - Carolinas HealthCare System_PLANHEADER_South Carolina Health Network Only Open Access - Carolinas HealthCare w/Pediatric Dental_PLANPREFILL_Aetna Leap Diabetes - Carolinas HealthCare System"
								|| planVal == "LEAP7|Aetna Leap Everyday - Carolinas HealthCare System:Aetna Leap Everyday Plus - Carolinas HealthCare System:Aetna Leap Basic Plus - Carolinas HealthCare System:Aetna Leap Basic HSA - Carolinas HealthCare System:Aetna Leap Diabetes - Carolinas HealthCare System:Aetna Leap Specialty - Carolinas HealthCare System_PLANHEADER_South Carolina Health Network Only Open Access - Carolinas HealthCare w/Pediatric Dental_PLANPREFILL_Aetna Leap Specialty - Carolinas HealthCare System"){
			location.href="https://my.aetna.com/#/login?public-search";
		}
		else if(planVal == "LEAP8|Aetna Leap Catastrophic - Carolinas HealthCare System_PLANHEADER_South Carolina Health Network Only Open Access - Carolinas HealthCare Catastrophic w/Pediatric Dental_PLANPREFILL_South Carolina Health Network Only Open Access - Carolinas HealthCare Catastrophic w/Pediatric Dental"
			|| planVal == "LEAP8|Aetna Leap Catastrophic - Carolinas HealthCare System_PLANHEADER_South Carolina Health Network Only Open Access - Carolinas HealthCare Catastrophic w/Pediatric Dental_PLANPREFILL_Aetna Leap Catastrophic - Carolinas HealthCare System"){
			location.href="https://my.aetna.com/#/login?public-search";
		}
		/*else if(planVal == "LEAP5|Innovation Health Leap Bronze Plus:Innovation Health Leap Bronze Basic:Innovation Health Leap Bronze HSA:Innovation Health Leap Gold Basic:Innovation Health Leap Gold Diabetes:Innovation Health Leap Catastrophic_PLANHEADER_Virginia Managed Choice  Open Access - Innovative Health w/Pediatric Dental_PLANPREFILL_Virginia Managed Choice  Open Access - Innovative Health w/Pediatric Dental"
			|| planVal == "LEAP5|Innovation Health Leap Bronze Plus:Innovation Health Leap Bronze Basic:Innovation Health Leap Bronze HSA:Innovation Health Leap Gold Basic:Innovation Health Leap Gold Diabetes:Innovation Health Leap Catastrophic_PLANHEADER_Virginia Managed Choice  Open Access - Innovative Health w/Pediatric Dental_PLANPREFILL_Innovation Health Leap Bronze Plus"
				|| planVal == "LEAP5|Innovation Health Leap Bronze Plus:Innovation Health Leap Bronze Basic:Innovation Health Leap Bronze HSA:Innovation Health Leap Gold Basic:Innovation Health Leap Gold Diabetes:Innovation Health Leap Catastrophic_PLANHEADER_Virginia Managed Choice  Open Access - Innovative Health w/Pediatric Dental_PLANPREFILL_Innovation Health Leap Bronze Basic"
					|| planVal == "LEAP5|Innovation Health Leap Bronze Plus:Innovation Health Leap Bronze Basic:Innovation Health Leap Bronze HSA:Innovation Health Leap Gold Basic:Innovation Health Leap Gold Diabetes:Innovation Health Leap Catastrophic_PLANHEADER_Virginia Managed Choice  Open Access - Innovative Health w/Pediatric Dental_PLANPREFILL_Innovation Health Leap Bronze HSA"
						|| planVal == "LEAP5|Innovation Health Leap Bronze Plus:Innovation Health Leap Bronze Basic:Innovation Health Leap Bronze HSA:Innovation Health Leap Gold Basic:Innovation Health Leap Gold Diabetes:Innovation Health Leap Catastrophic_PLANHEADER_Virginia Managed Choice  Open Access - Innovative Health w/Pediatric Dental_PLANPREFILL_Innovation Health Leap Gold Basic"
							|| planVal == "LEAP5|Innovation Health Leap Bronze Plus:Innovation Health Leap Bronze Basic:Innovation Health Leap Bronze HSA:Innovation Health Leap Gold Basic:Innovation Health Leap Gold Diabetes:Innovation Health Leap Catastrophic_PLANHEADER_Virginia Managed Choice  Open Access - Innovative Health w/Pediatric Dental_PLANPREFILL_Innovation Health Leap Gold Diabetes"
								|| planVal == "LEAP5|Innovation Health Leap Bronze Plus:Innovation Health Leap Bronze Basic:Innovation Health Leap Bronze HSA:Innovation Health Leap Gold Basic:Innovation Health Leap Gold Diabetes:Innovation Health Leap Catastrophic_PLANHEADER_Virginia Managed Choice  Open Access - Innovative Health w/Pediatric Dental_PLANPREFILL_Innovation Health Leap Catastrophic"){
			location.href="https://buyhealthinsurance.innovation-health.com/?state=VA&network=000001-02VA0001&destination=providersearch";
		}*/
	}
	else if($('#site_id').val()!=null && $('#site_id').val()!=undefined && $('#site_id').val() == 'QualifiedHealthPlanDoctors'){
		if(planVal == "LEAP1|Aetna Leap Everyday - Banner:Aetna Leap Everyday Plus - Banner:Aetna Leap Basic Plus - Banner:Aetna Leap Basic - Banner:Aetna Leap Basic HSA - Banner:Aetna Leap Specialty - Banner:Aetna Leap Diabetes - Banner_PLANHEADER_Arizona Banner Health Network Only Open Access w/Pediatric Dental_PLANPREFILL_Arizona Banner Health Network Only Open Access w/Pediatric Dental"
			|| planVal== "LEAP1|Aetna Leap Everyday - Banner:Aetna Leap Everyday Plus - Banner:Aetna Leap Basic Plus - Banner:Aetna Leap Basic - Banner:Aetna Leap Basic HSA - Banner:Aetna Leap Specialty - Banner:Aetna Leap Diabetes - Banner_PLANHEADER_Arizona Banner Health Network Only Open Access w/Pediatric Dental_PLANPREFILL_Aetna Leap Everyday - Banner"
				|| planVal == "LEAP1|Aetna Leap Everyday - Banner:Aetna Leap Everyday Plus - Banner:Aetna Leap Basic Plus - Banner:Aetna Leap Basic - Banner:Aetna Leap Basic HSA - Banner:Aetna Leap Specialty - Banner:Aetna Leap Diabetes - Banner_PLANHEADER_Arizona Banner Health Network Only Open Access w/Pediatric Dental_PLANPREFILL_Aetna Leap Everyday Plus - Banner"
					|| planVal == "LEAP1|Aetna Leap Everyday - Banner:Aetna Leap Everyday Plus - Banner:Aetna Leap Basic Plus - Banner:Aetna Leap Basic - Banner:Aetna Leap Basic HSA - Banner:Aetna Leap Specialty - Banner:Aetna Leap Diabetes - Banner_PLANHEADER_Arizona Banner Health Network Only Open Access w/Pediatric Dental_PLANPREFILL_Aetna Leap Basic Plus - Banner"
						|| planVal == "LEAP1|Aetna Leap Everyday - Banner:Aetna Leap Everyday Plus - Banner:Aetna Leap Basic Plus - Banner:Aetna Leap Basic - Banner:Aetna Leap Basic HSA - Banner:Aetna Leap Specialty - Banner:Aetna Leap Diabetes - Banner_PLANHEADER_Arizona Banner Health Network Only Open Access w/Pediatric Dental_PLANPREFILL_Aetna Leap Basic - Banner"
							|| planVal == "LEAP1|Aetna Leap Everyday - Banner:Aetna Leap Everyday Plus - Banner:Aetna Leap Basic Plus - Banner:Aetna Leap Basic - Banner:Aetna Leap Basic HSA - Banner:Aetna Leap Specialty - Banner:Aetna Leap Diabetes - Banner_PLANHEADER_Arizona Banner Health Network Only Open Access w/Pediatric Dental_PLANPREFILL_Aetna Leap Basic HSA - Banner"
								|| planVal == "LEAP1|Aetna Leap Everyday - Banner:Aetna Leap Everyday Plus - Banner:Aetna Leap Basic Plus - Banner:Aetna Leap Basic - Banner:Aetna Leap Basic HSA - Banner:Aetna Leap Specialty - Banner:Aetna Leap Diabetes - Banner_PLANHEADER_Arizona Banner Health Network Only Open Access w/Pediatric Dental_PLANPREFILL_Aetna Leap Specialty - Banner"
									|| planVal == "LEAP1|Aetna Leap Everyday - Banner:Aetna Leap Everyday Plus - Banner:Aetna Leap Basic Plus - Banner:Aetna Leap Basic - Banner:Aetna Leap Basic HSA - Banner:Aetna Leap Specialty - Banner:Aetna Leap Diabetes - Banner_PLANHEADER_Arizona Banner Health Network Only Open Access w/Pediatric Dental_PLANPREFILL_Aetna Leap Diabetes - Banner"){
			location.href="https://my.aetna.com/#/login?public-search";
		}
		else if(planVal == "LEAP2|Aetna Leap Everyday - Carolinas HealthCare System:Aetna Leap Everyday Plus - Carolinas HealthCare System:Aetna Leap Basic Plus - Carolinas HealthCare System:Aetna Leap Basic HSA - Carolinas HealthCare System:Aetna Leap Diabetes - Carolinas  HealthCare System:Aetna Leap Specialty - Carolinas HealthCare System_PLANHEADER_North Carolina Health Network Only Open Access Carolinas HealthCare w/Pediatric Dental_PLANPREFILL_North Carolina Health Network Only Open Access Carolinas HealthCare w/Pediatric Dental"
			|| planVal == "LEAP2|Aetna Leap Everyday - Carolinas HealthCare System:Aetna Leap Everyday Plus - Carolinas HealthCare System:Aetna Leap Basic Plus - Carolinas HealthCare System:Aetna Leap Basic HSA - Carolinas HealthCare System:Aetna Leap Diabetes - Carolinas  HealthCare System:Aetna Leap Specialty - Carolinas HealthCare System_PLANHEADER_North Carolina Health Network Only Open Access Carolinas HealthCare w/Pediatric Dental_PLANPREFILL_Aetna Leap Everyday - Carolinas HealthCare System"
				|| planVal == "LEAP2|Aetna Leap Everyday - Carolinas HealthCare System:Aetna Leap Everyday Plus - Carolinas HealthCare System:Aetna Leap Basic Plus - Carolinas HealthCare System:Aetna Leap Basic HSA - Carolinas HealthCare System:Aetna Leap Diabetes - Carolinas  HealthCare System:Aetna Leap Specialty - Carolinas HealthCare System_PLANHEADER_North Carolina Health Network Only Open Access Carolinas HealthCare w/Pediatric Dental_PLANPREFILL_Aetna Leap Everyday Plus - Carolinas HealthCare System"
					|| planVal == "LEAP2|Aetna Leap Everyday - Carolinas HealthCare System:Aetna Leap Everyday Plus - Carolinas HealthCare System:Aetna Leap Basic Plus - Carolinas HealthCare System:Aetna Leap Basic HSA - Carolinas HealthCare System:Aetna Leap Diabetes - Carolinas  HealthCare System:Aetna Leap Specialty - Carolinas HealthCare System_PLANHEADER_North Carolina Health Network Only Open Access Carolinas HealthCare w/Pediatric Dental_PLANPREFILL_Aetna Leap Basic Plus - Carolinas HealthCare System"
						|| planVal == "LEAP2|Aetna Leap Everyday - Carolinas HealthCare System:Aetna Leap Everyday Plus - Carolinas HealthCare System:Aetna Leap Basic Plus - Carolinas HealthCare System:Aetna Leap Basic HSA - Carolinas HealthCare System:Aetna Leap Diabetes - Carolinas  HealthCare System:Aetna Leap Specialty - Carolinas HealthCare System_PLANHEADER_North Carolina Health Network Only Open Access Carolinas HealthCare w/Pediatric Dental_PLANPREFILL_Aetna Leap Basic HSA - Carolinas HealthCare System"
							|| planVal == "LEAP2|Aetna Leap Everyday - Carolinas HealthCare System:Aetna Leap Everyday Plus - Carolinas HealthCare System:Aetna Leap Basic Plus - Carolinas HealthCare System:Aetna Leap Basic HSA - Carolinas HealthCare System:Aetna Leap Diabetes - Carolinas  HealthCare System:Aetna Leap Specialty - Carolinas HealthCare System_PLANHEADER_North Carolina Health Network Only Open Access Carolinas HealthCare w/Pediatric Dental_PLANPREFILL_Aetna Leap Diabetes - Carolinas  HealthCare System"
								|| planVal == "LEAP2|Aetna Leap Everyday - Carolinas HealthCare System:Aetna Leap Everyday Plus - Carolinas HealthCare System:Aetna Leap Basic Plus - Carolinas HealthCare System:Aetna Leap Basic HSA - Carolinas HealthCare System:Aetna Leap Diabetes - Carolinas  HealthCare System:Aetna Leap Specialty - Carolinas HealthCare System_PLANHEADER_North Carolina Health Network Only Open Access Carolinas HealthCare w/Pediatric Dental_PLANPREFILL_Aetna Leap Specialty - Carolinas HealthCare System"){
			//Mona
			location.href="https://my.aetna.com/#/login?public-search";
		}
		else if(planVal == "LEAP3|Aetna Leap Everyday - CaroMont Health:Aetna Leap Everyday Plus - CaroMont Health:Aetna Leap Basic Plus - CaroMont Health:Aetna Leap Basic HSA - CaroMont Health:Aetna Leap Diabetes - CaroMont Health:Aetna Leap Specialty - CaroMont Health_PLANHEADER_North Carolina Health Network Only Open Access CaroMont w/Pediatric Dental_PLANPREFILL_North Carolina Health Network Only Open Access CaroMont w/Pediatric Dental"
			|| planVal == "LEAP3|Aetna Leap Everyday - CaroMont Health:Aetna Leap Everyday Plus - CaroMont Health:Aetna Leap Basic Plus - CaroMont Health:Aetna Leap Basic HSA - CaroMont Health:Aetna Leap Diabetes - CaroMont Health:Aetna Leap Specialty - CaroMont Health_PLANHEADER_North Carolina Health Network Only Open Access CaroMont w/Pediatric Dental_PLANPREFILL_Aetna Leap Everyday - CaroMont Health"
				|| planVal == "LEAP3|Aetna Leap Everyday - CaroMont Health:Aetna Leap Everyday Plus - CaroMont Health:Aetna Leap Basic Plus - CaroMont Health:Aetna Leap Basic HSA - CaroMont Health:Aetna Leap Diabetes - CaroMont Health:Aetna Leap Specialty - CaroMont Health_PLANHEADER_North Carolina Health Network Only Open Access CaroMont w/Pediatric Dental_PLANPREFILL_Aetna Leap Everyday Plus - CaroMont Health"
					|| planVal == "LEAP3|Aetna Leap Everyday - CaroMont Health:Aetna Leap Everyday Plus - CaroMont Health:Aetna Leap Basic Plus - CaroMont Health:Aetna Leap Basic HSA - CaroMont Health:Aetna Leap Diabetes - CaroMont Health:Aetna Leap Specialty - CaroMont Health_PLANHEADER_North Carolina Health Network Only Open Access CaroMont w/Pediatric Dental_PLANPREFILL_Aetna Leap Basic Plus - CaroMont Health"
						|| planVal == "LEAP3|Aetna Leap Everyday - CaroMont Health:Aetna Leap Everyday Plus - CaroMont Health:Aetna Leap Basic Plus - CaroMont Health:Aetna Leap Basic HSA - CaroMont Health:Aetna Leap Diabetes - CaroMont Health:Aetna Leap Specialty - CaroMont Health_PLANHEADER_North Carolina Health Network Only Open Access CaroMont w/Pediatric Dental_PLANPREFILL_Aetna Leap Basic HSA - CaroMont Health"
							|| planVal == "LEAP3|Aetna Leap Everyday - CaroMont Health:Aetna Leap Everyday Plus - CaroMont Health:Aetna Leap Basic Plus - CaroMont Health:Aetna Leap Basic HSA - CaroMont Health:Aetna Leap Diabetes - CaroMont Health:Aetna Leap Specialty - CaroMont Health_PLANHEADER_North Carolina Health Network Only Open Access CaroMont w/Pediatric Dental_PLANPREFILL_Aetna Leap Diabetes - CaroMont Health"
								|| planVal == "LEAP3|Aetna Leap Everyday - CaroMont Health:Aetna Leap Everyday Plus - CaroMont Health:Aetna Leap Basic Plus - CaroMont Health:Aetna Leap Basic HSA - CaroMont Health:Aetna Leap Diabetes - CaroMont Health:Aetna Leap Specialty - CaroMont Health_PLANHEADER_North Carolina Health Network Only Open Access CaroMont w/Pediatric Dental_PLANPREFILL_Aetna Leap Specialty - CaroMont Health"){
			//Mona
			location.href="https://my.aetna.com/#/login?public-search";
		}
		
		else if(planVal == "LEAP8|Aetna Leap Catastrophic - Carolinas HealthCare System_PLANHEADER_North Carolina Health Network Only Open Access Carolinas HealthCare Catastrophic w/Pediatric Dental_PLANPREFILL_North Carolina Health Network Only Open Access Carolinas HealthCare Catastrophic w/Pediatric Dental"
			|| planVal == "LEAP8|Aetna Leap Catastrophic - Carolinas HealthCare System_PLANHEADER_North Carolina Health Network Only Open Access Carolinas HealthCare Catastrophic w/Pediatric Dental_PLANPREFILL_Aetna Leap Catastrophic - Carolinas HealthCare System")
		{
			location.href="https://my.aetna.com/#/login?public-search";
		}
		else if(planVal == "LEAP8|Aetna Leap Catastrophic - CaroMont Health_PLANHEADER_North Carolina Health Network Only Open Access CaroMont Catastrophic w/Pediatric Dental_PLANPREFILL_North Carolina Health Network Only Open Access CaroMont Catastrophic w/Pediatric Dental"
			|| planVal == "LEAP8|Aetna Leap Catastrophic - CaroMont Health_PLANHEADER_North Carolina Health Network Only Open Access CaroMont Catastrophic w/Pediatric Dental_PLANPREFILL_Aetna Leap Catastrophic - CaroMont Health"){
			location.href="https://my.aetna.com/#/login?public-search";
		}	
		else if(planVal == "LEAP7|Aetna Leap Everyday - Carolinas HealthCare System:Aetna Leap Everyday Plus - Carolinas HealthCare System:Aetna Leap Basic Plus - Carolinas HealthCare System:Aetna Leap Basic HSA - Carolinas HealthCare System:Aetna Leap Diabetes - Carolinas HealthCare System:Aetna Leap Specialty - Carolinas HealthCare System_PLANHEADER_South Carolina Health Network Only Open Access - Carolinas HealthCare w/Pediatric Dental_PLANPREFILL_South Carolina Health Network Only Open Access - Carolinas HealthCare w/Pediatric Dental"
			|| planVal == "LEAP7|Aetna Leap Everyday - Carolinas HealthCare System:Aetna Leap Everyday Plus - Carolinas HealthCare System:Aetna Leap Basic Plus - Carolinas HealthCare System:Aetna Leap Basic HSA - Carolinas HealthCare System:Aetna Leap Diabetes - Carolinas HealthCare System:Aetna Leap Specialty - Carolinas HealthCare System_PLANHEADER_South Carolina Health Network Only Open Access - Carolinas HealthCare w/Pediatric Dental_PLANPREFILL_Aetna Leap Everyday - Carolinas HealthCare System"
				|| planVal == "LEAP7|Aetna Leap Everyday - Carolinas HealthCare System:Aetna Leap Everyday Plus - Carolinas HealthCare System:Aetna Leap Basic Plus - Carolinas HealthCare System:Aetna Leap Basic HSA - Carolinas HealthCare System:Aetna Leap Diabetes - Carolinas HealthCare System:Aetna Leap Specialty - Carolinas HealthCare System_PLANHEADER_South Carolina Health Network Only Open Access - Carolinas HealthCare w/Pediatric Dental_PLANPREFILL_Aetna Leap Everyday Plus - Carolinas HealthCare System"
					|| planVal == "LEAP7|Aetna Leap Everyday - Carolinas HealthCare System:Aetna Leap Everyday Plus - Carolinas HealthCare System:Aetna Leap Basic Plus - Carolinas HealthCare System:Aetna Leap Basic HSA - Carolinas HealthCare System:Aetna Leap Diabetes - Carolinas HealthCare System:Aetna Leap Specialty - Carolinas HealthCare System_PLANHEADER_South Carolina Health Network Only Open Access - Carolinas HealthCare w/Pediatric Dental_PLANPREFILL_Aetna Leap Basic Plus - Carolinas HealthCare System"
						|| planVal == "LEAP7|Aetna Leap Everyday - Carolinas HealthCare System:Aetna Leap Everyday Plus - Carolinas HealthCare System:Aetna Leap Basic Plus - Carolinas HealthCare System:Aetna Leap Basic HSA - Carolinas HealthCare System:Aetna Leap Diabetes - Carolinas HealthCare System:Aetna Leap Specialty - Carolinas HealthCare System_PLANHEADER_South Carolina Health Network Only Open Access - Carolinas HealthCare w/Pediatric Dental_PLANPREFILL_Aetna Leap Basic HSA - Carolinas HealthCare System"
							|| planVal == "LEAP7|Aetna Leap Everyday - Carolinas HealthCare System:Aetna Leap Everyday Plus - Carolinas HealthCare System:Aetna Leap Basic Plus - Carolinas HealthCare System:Aetna Leap Basic HSA - Carolinas HealthCare System:Aetna Leap Diabetes - Carolinas HealthCare System:Aetna Leap Specialty - Carolinas HealthCare System_PLANHEADER_South Carolina Health Network Only Open Access - Carolinas HealthCare w/Pediatric Dental_PLANPREFILL_Aetna Leap Diabetes - Carolinas HealthCare System"
								|| planVal == "LEAP7|Aetna Leap Everyday - Carolinas HealthCare System:Aetna Leap Everyday Plus - Carolinas HealthCare System:Aetna Leap Basic Plus - Carolinas HealthCare System:Aetna Leap Basic HSA - Carolinas HealthCare System:Aetna Leap Diabetes - Carolinas HealthCare System:Aetna Leap Specialty - Carolinas HealthCare System_PLANHEADER_South Carolina Health Network Only Open Access - Carolinas HealthCare w/Pediatric Dental_PLANPREFILL_Aetna Leap Specialty - Carolinas HealthCare System"){
			location.href="https://my.aetna.com/#/login?public-search";
		}	
		else if(planVal == "LEAP8|Aetna Leap Catastrophic - Carolinas HealthCare System_PLANHEADER_South Carolina Health Network Only Open Access - Carolinas HealthCare Catastrophic w/Pediatric Dental_PLANPREFILL_South Carolina Health Network Only Open Access - Carolinas HealthCare Catastrophic w/Pediatric Dental"
			|| planVal == "LEAP8|Aetna Leap Catastrophic - Carolinas HealthCare System_PLANHEADER_South Carolina Health Network Only Open Access - Carolinas HealthCare Catastrophic w/Pediatric Dental_PLANPREFILL_Aetna Leap Catastrophic - Carolinas HealthCare System"){
			location.href="https://my.aetna.com/#/login?public-search";
		}	
		else if(planVal == "LEAP6|Aetna Leap Everyday:Aetna Leap Everyday Plus:Aetna Leap Basic:Aetna Leap Basic Plus:Aetna Leap Basic HSA:Aetna Leap Specialty:Aetna Leap Diabetes_PLANHEADER_Pennsylvania Savings Plus Health Network Only w/Pediatric Dental_PLANPREFILL_Pennsylvania Savings Plus Health Network Only w/Pediatric Dental"
			|| planVal == "LEAP6|Aetna Leap Everyday:Aetna Leap Everyday Plus:Aetna Leap Basic:Aetna Leap Basic Plus:Aetna Leap Basic HSA:Aetna Leap Specialty:Aetna Leap Diabetes_PLANHEADER_Pennsylvania Savings Plus Health Network Only w/Pediatric Dental_PLANPREFILL_Aetna Leap Everyday"
				|| planVal == "LEAP6|Aetna Leap Everyday:Aetna Leap Everyday Plus:Aetna Leap Basic:Aetna Leap Basic Plus:Aetna Leap Basic HSA:Aetna Leap Specialty:Aetna Leap Diabetes_PLANHEADER_Pennsylvania Savings Plus Health Network Only w/Pediatric Dental_PLANPREFILL_Aetna Leap Everyday Plus"
					|| planVal == "LEAP6|Aetna Leap Everyday:Aetna Leap Everyday Plus:Aetna Leap Basic:Aetna Leap Basic Plus:Aetna Leap Basic HSA:Aetna Leap Specialty:Aetna Leap Diabetes_PLANHEADER_Pennsylvania Savings Plus Health Network Only w/Pediatric Dental_PLANPREFILL_Aetna Leap Basic"
						|| planVal == "LEAP6|Aetna Leap Everyday:Aetna Leap Everyday Plus:Aetna Leap Basic:Aetna Leap Basic Plus:Aetna Leap Basic HSA:Aetna Leap Specialty:Aetna Leap Diabetes_PLANHEADER_Pennsylvania Savings Plus Health Network Only w/Pediatric Dental_PLANPREFILL_Aetna Leap Basic Plus"
							|| planVal == "LEAP6|Aetna Leap Everyday:Aetna Leap Everyday Plus:Aetna Leap Basic:Aetna Leap Basic Plus:Aetna Leap Basic HSA:Aetna Leap Specialty:Aetna Leap Diabetes_PLANHEADER_Pennsylvania Savings Plus Health Network Only w/Pediatric Dental_PLANPREFILL_Aetna Leap Basic HSA"
								|| planVal == "LEAP6|Aetna Leap Everyday:Aetna Leap Everyday Plus:Aetna Leap Basic:Aetna Leap Basic Plus:Aetna Leap Basic HSA:Aetna Leap Specialty:Aetna Leap Diabetes_PLANHEADER_Pennsylvania Savings Plus Health Network Only w/Pediatric Dental_PLANPREFILL_Aetna Leap Specialty"
									|| planVal == "LEAP6|Aetna Leap Everyday:Aetna Leap Everyday Plus:Aetna Leap Basic:Aetna Leap Basic Plus:Aetna Leap Basic HSA:Aetna Leap Specialty:Aetna Leap Diabetes_PLANHEADER_Pennsylvania Savings Plus Health Network Only w/Pediatric Dental_PLANPREFILL_Aetna Leap Diabetes"){
			location.href="https://my.aetna.com/#/login?public-search";
		}	
	}
	else if($('#site_id').val()!=null && $('#site_id').val()!=undefined && $('#site_id').val() == 'innovationhealth'){
		if(planVal == "LEAP5|Innovation Health Leap Silver Basic" || planVal == "LEAP5|Innovation Health Leap Silver Plus" || planVal == "LEAP5|Innovation Health Leap Bronze Plus"
			|| planVal == "LEAP5|Innovation Health Leap Bronze Basic" || planVal == "LEAP5|Innovation Health Leap Bronze HSA" || planVal == "LEAP5|Innovation Health Leap Gold Basic"
				|| planVal == "LEAP5|Innovation Health Leap Gold Diabetes" || planVal == "LEAP5|Innovation Health Leap Catastrophic"){
			location.href="https://my.innovation-health.com/#/login?public-search";
		}	
	}
}
function setDSEDialogFocus(id){
	if(id != ""){
	    if($('.dialog-close-button_'+id).is(':visible')){
	           $(".dialog-close-button_"+id).keypress(function (e) {
	               if (e.keyCode == 13) {
	                  $(".dialog-close-button_"+id).click();
	               }
	           });
	           var x = document.getElementsByClassName("dialog-close-button_"+id);
	           var i;
	           for(i=0; i<x.length; i++){
	             x[i].tabIndex = "0";
	           }
	    }
	}else{
		//if($('.dialog-close-button').is(':visible')){
	           $(".dialog-close-button").keypress(function (e) {
	               if (e.keyCode == 13) {
	                  $(".dialog-close-button").click();
	               }
	           });
	           var x = document.getElementsByClassName("dialog-close-button");
	           var i;
	           for(i=0; i<x.length; i++){
	             x[i].tabIndex = "0";
	           }
	    //}
	}
}

function getDisplayNameForSelectedPlan(productPlanName){
	var selectedPlanToDisplay;
	var detailsUrl = window.location.href;
	var isDetailsPage = (detailsUrl != null && detailsUrl.indexOf('search/detail') != -1);
	var proxyUrl;
	if(isDetailsPage){
		proxyUrl = "forDetailsPage/getDisplayNameForAPlan";
	}
	else{
		proxyUrl = "search/getDisplayNameForAPlan";
	}
	if(productPlanName != undefined && productPlanName != null && productPlanName != "" && productPlanName.indexOf('include:') > -1){
		//use plan name from URL for sites like IVL and QHP
		selectedPlanToDisplay = productPlanName;
	}
	else if(selectedPlanToDisplay == null || selectedPlanToDisplay == undefined){
		var selectedPlanPipeName = getCookie("selectedPlan");
		if(selectedPlanPipeName == null || selectedPlanPipeName == undefined || selectedPlanPipeName == ""){
			//dont make AJAX call, display plan name form URL
			selectedPlanToDisplay = productPlanName;
		}
		else{
			//make an AJAX call for fetching plan name as per it's pipe name
			$.ajax( {
				type : "GET",
				url : proxyUrl,
				data : 'selectedPlanPipeName=' + selectedPlanPipeName,
				dataType : "text",
				async: false,
				success : function(response) {
				if (response == "") {
					selectedPlanToDisplay = selectedPlanPipeName;
				} else {
					selectedPlanToDisplay = response;
				}
			},
			});
		}
	}
	return selectedPlanToDisplay;
}

//content change - 0420
function redirectLogic(searchQuery){
	var searchTermArray = searchQuery.split(' ');
	for (var i = 0; i < searchTermArray.length; i++) {
		if(searchTermArray[i] != null){
			//redirect to aetnapharmacy site for all non custom sites
			if($('#site_id').val() == 'provider' || $.getUrlVar('site_id') == 'provider'
				|| $('#site_id').val() == 'dse' || $.getUrlVar('site_id') == 'dse'
					|| $('#site_id').val() == '' || $.getUrlVar('site_id') == ''){
				if(searchTermArray[i].toLowerCase() == 'pharmacy' || searchTermArray[i].toLowerCase() == 'pharmacies'){
					location.href = "http://www.aetna.com/docfind/home.do?site_id=aetnapharmacy&langpref=en";
				}
			}
		} 
	}
	return false;
}