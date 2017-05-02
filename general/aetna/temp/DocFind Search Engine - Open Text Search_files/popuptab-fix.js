AetnaCom_popuptab = function() {

	var that = this;
	var selectTypePopup;
	var popupElements = [];
	var actualSelectedElement = 0;
	
	var init = function() {
		bindKeydownEvent();		
	}

	var initPopupElements = function() {
		popupElements = [];
		if ($('.dialog-main-wrapper_preSearchDialogBox').length > 0
				&& $('.dialog-main-wrapper_preSearchDialogBox').css('display') === 'block') {
			selectTypePopup = $('.dialog-main-wrapper_preSearchDialogBox');
			if($('#quickSearchSelection').length>0){
			popupElements.push($('#quickSearchSelection'));
			}
			if($('#quickSearchMultipleSelection').length>0){
				popupElements.push($('#quickSearchMultipleSelection'));
			}
			if($('#btnCancelPreSearch').length>0){
				popupElements.push($('#btnCancelPreSearch'));
			}
			if($('#btnChoosePreSearch').length>0){
				popupElements.push($('#btnChoosePreSearch'));
			}
			
			
		}
		/*-- START CHANGES P20751b ACO Branding - n596307 --*/
		else if ($('.dialog-main-wrapper_preSearchHLDialogBox').length > 0
				&& $('.dialog-main-wrapper_preSearchHLDialogBox').css('display') === 'block') {
			selectTypePopup = $('.dialog-main-wrapper_preSearchHLDialogBox');
			popupElements.push($('#quickSearchHLSelection'));
			popupElements.push($('#btnCancelPreSearchHL'));
			popupElements.push($('#btnChoosePreSearchHL'));
			if ($('.dialog-close-button_preSearchHLDialogBox').is(':visible')){
				popupElements.push($('.dialog-close-button_preSearchHLDialogBox'));
			}
		}
		/*-- END CHANGES P20751b ACO Branding - n596307 --*/
		else if ($('.dialog-main-wrapper_planModal').length > 0
				&& $('.dialog-main-wrapper_planModal').css('display') === 'block') {
			selectTypePopup = $('.dialog-main-wrapper_planModal');
			
			if($('#logInStatePopup_es').is(':visible')){
				popupElements.push($('#logInStatePopup_es'));
			}
			if($('#logInStatePopup').is(':visible')){
				popupElements.push($('#logInStatePopup'));
			}
			if($('#stateDD').is(':visible')){
				popupElements.push($('#stateDD'));
			}
			if($('#modal_aetna_plans').is(':visible')){
				popupElements.push($('#modal_aetna_plans'));
			}
			if($('#btnChooseStatePlan').is(':visible')){
				popupElements.push($('#btnChooseStatePlan'));
			}
			if($('#contWOPlan_ft').is(':visible')){
				popupElements.push($('#contWOPlan_ft'));
			}
			if($('#btnChoosePlan').is(':visible')){
				popupElements.push($('#btnChoosePlan'));
			}
			if($('#medicareTop').is(':visible')){
				popupElements.push($('#medicareTop'));
			}
			if($('#medicaidTop').is(':visible')){
				popupElements.push($('#medicaidTop'));
			}
			if ($('.dialog-close-button_planModal').is(':visible')){
				popupElements.push($('.dialog-close-button_planModal'));
			}
		}
		else if ($('#locationDialogBox').parents('.dialog-main-wrapper').length > 0
				&& $('#locationDialogBox').parents('.dialog-main-wrapper').css('display') === 'block'){
			selectTypePopup = $('#locationDialogBox').parents('.dialog-main-wrapper');
			popupElements.push($('#hl-location-autocomplete-search'));
			popupElements.push($('#cancelWHLocCriteria'));
			popupElements.push($('#searchWHLocCriteria'));
			popupElements.push($('#locationDialogBox').parents('.dialog-main-wrapper').children('.dialog-close-button'));
			
		}
		else if ($('#locationHLDialogBox').parents('.dialog-main-wrapper').length > 0
				&& $('#locationHLDialogBox').parents('.dialog-main-wrapper').css('display') === 'block'){
			selectTypePopup = $('#locationHLDialogBox').parents('.dialog-main-wrapper');
			if($('#hl-location-autocomplete-search').is(':visible')){
				popupElements.push($('#hl-location-autocomplete-search'));
			}
			else if($('#hl-no-location-autocomplete-search').is(':visible')){
				popupElements.push($('#hl-no-location-autocomplete-search'));
			}
			popupElements.push($('#cancelWHLocHLCriteria'));
			popupElements.push($('#searchWHLocHLCriteria'));
			popupElements.push($('#locationHLDialogBox').parents('.dialog-main-wrapper').children('.dialog-close-button'));
		}
		else if ($('#noPlanAlertDialogBox').parents('.dialog-main-wrapper').length > 0
				&& $('#noPlanAlertDialogBox').parents('.dialog-main-wrapper').css('display') === 'block'){
			selectTypePopup = $('#noPlanAlertDialogBox').parents('.dialog-main-wrapper');
			popupElements.push($('#selectAPlan'));
			popupElements.push($('#iUnderstand'));
			popupElements.push($('#noPlanAlertDialogBox').parents('.dialog-main-wrapper').children('.dialog-close-button'));
		}
		else if ($('#printDirectoryDialogBox').parents('.dialog-main-wrapper').length > 0
				&& $('#printDirectoryDialogBox').parents('.dialog-main-wrapper').css('display') === 'block'){
			selectTypePopup = $('#printDirectoryDialogBox').parents('.dialog-main-wrapper');
			popupElements.push($('#cancelPDButton'));
			popupElements.push($('#printPDButton'));
			popupElements.push($('#printDirectoryDialogBox').parents('.dialog-main-wrapper').children('.dialog-close-button'));
		}else if($('.dialog-main-wrapper_planSelection').length > 0
				&& $('.dialog-main-wrapper_planSelection').css('display') === 'block'){
			selectTypePopup = $('.dialog-main-wrapper_planSelection');
			popupElements.push($('#cplanStatus'));
			popupElements.push($('#fplanStatus'));
			popupElements.push($('#btnCancel2'));
			popupElements.push($('.dialog-main-wrapper_planSelection').find('#btnContinue2'));
			if ($('.dialog-close-button_planSelection').is(':visible')){
				popupElements.push($('.dialog-close-button_planSelection'));
			}
		}
		else if($('#softMessageDialog').parents('.dialog-main-wrapper').length > 0
				&& $('#softMessageDialog').parents('.dialog-main-wrapper').css('display') === 'block'){
			selectTypePopup = $('#softMessageDialog').parents('.dialog-main-wrapper');
			popupElements.push($('#softMessage_OK'));
			popupElements.push($('#softMessageDialog').parents('.dialog-main-wrapper').children('.dialog-close-button'));
		}
		else if($('#filterDialog').parents('.dialog-main-wrapper').length > 0
				&& $('#filterDialog').parents('.dialog-main-wrapper').css('display') === 'block'){
			selectTypePopup = $('#filterDialog').parents('.dialog-main-wrapper');
			if($('#filterTabLink1').length > 0){
				popupElements.push($('#filterTabLink1'));
			}
			if($('#filterTabLink2').length > 0){
				popupElements.push($('#filterTabLink2'));
			}
			if($('#languagenavigator').length > 0){
				$('#filterDialog').children('#languagenavigator').children('input').each(function () {
					popupElements.push($(this)); // "this" is the current element in the loop
				});
			}
			if($('#gendernavigator').length > 0){
				$('#filterDialog').children('#gendernavigator').children('input').each(function () {
					popupElements.push($(this)); // "this" is the current element in the loop
				});
			}
			if($('#hospitalnavigator').length > 0){
				$('#filterDialog').children('#hospitalnavigator').children('input').each(function () {
					popupElements.push($(this)); // "this" is the current element in the loop
				});
			}
			// office details left
			if($('#categorynavigator').length > 0){
				$('#filterDialog').children('#categorynavigator').children('input').each(function () {
					popupElements.push($(this)); // "this" is the current element in the loop
				});
			}
			if($('#acceptingnewpatientsnavigator').length > 0){
				$('#filterDialog').children('#acceptingnewpatientsnavigator').children('input').each(function () {
					popupElements.push($(this)); // "this" is the current element in the loop
				});
			}
			if($('#flagnavigator').length > 0){
				$('#filterDialog').children('#flagnavigator').children('input').each(function () {
					popupElements.push($(this)); // "this" is the current element in the loop
				});
			}
			if($('#groupnavigator').length > 0){
				$('#filterDialog').children('#groupnavigator').children('input').each(function () {
					popupElements.push($(this)); // "this" is the current element in the loop
				});
			}
			if($('#classificationnavigator').length > 0){
				$('#filterDialog').children('#classificationnavigator').children('input').each(function () {
					popupElements.push($(this)); // "this" is the current element in the loop
				});
			}
			if($('#rollupnavigator').length > 0){
				$('#filterDialog').children('#rollupnavigator').children('input').each(function () {
					popupElements.push($(this)); // "this" is the current element in the loop
				});
			}
			if($('#orgnavigator').length > 0){
				$('#filterDialog').children('#orgnavigator').children('input').each(function () {
					popupElements.push($(this)); // "this" is the current element in the loop
				});
			}
			if($('#medicaldentalnavigator').length > 0){
				$('#filterDialog').children('#medicaldentalnavigator').children('input').each(function () {
					popupElements.push($(this)); // "this" is the current element in the loop
				});
			}
			if($('#specialtynavigator').length > 0){
				$('#filterDialog').children('#specialtynavigator').children('input').each(function () {
					popupElements.push($(this)); // "this" is the current element in the loop
				});
			}
			popupElements.push($('#Clear'));
			popupElements.push($('#Search'));
			popupElements.push($('#filterDialog').parents('.dialog-main-wrapper').children('.dialog-close-button'));
		}
	}

	var bindKeydownEvent = function() {
		$(document).keydown(function(evt) {
			if ((evt.shiftKey && evt.keyCode == 9) || evt.keyCode === 9) {
				initPopupElements();
				var activeElemFound = false;
				for(i = 0; i < popupElements.length; i++){
					if($.inArray(document.activeElement, popupElements[i]) > -1){
						activeElemFound = true;
						break;
					}
				}
				if(!activeElemFound){
					actualSelectedElement = -1;
				}
				if (selectTypePopup && selectTypePopup.css('display') === 'block') {
					evt.preventDefault();

					// Recreate the obj related to the select. It is refreshed when the dialog is closed
					// Check if active element is not the type selection
					if(evt.shiftKey && evt.keyCode == 9){
						if (actualSelectedElement > 0) {
							popupElements[--actualSelectedElement][0].focus();
							setFocusToWeirdElements();
						}
						else{
							actualSelectedElement = popupElements.length;
							popupElements[--actualSelectedElement][0].focus();
							setFocusToWeirdElements();
						}
					}
					else if(evt.keyCode === 9){
						if (actualSelectedElement < popupElements.length - 1) {
							popupElements[++actualSelectedElement][0].focus();
							setFocusToWeirdElements();
						}
						else{
							actualSelectedElement = -1;
							popupElements[++actualSelectedElement][0].focus();
							setFocusToWeirdElements();
						}
					}
				}
			}
		});
	}

	init();
}

$(document).ready(function(){
	
	
});
$(function() {
	var popuptab = new AetnaCom_popuptab();
});

function setFocusToWeirdElements(){
	$("#btnCancelPreSearch").focus(function(){
		$("#btnCancelPreSearch").parent().css({'outline':'thin dotted black'});
	});
	$("#btnCancelPreSearch").blur(function(){
		$("#btnCancelPreSearch").parent().css({'outline':''});
	});
	$("#btnChoosePreSearch").focus(function(){
		$("#btnChoosePreSearch").parent().css({'outline':'thin dotted black'});
	});
	$("#btnChoosePreSearch").blur(function(){
		$("#btnChoosePreSearch").parent().css({'outline':''});
	});
	$("#cancelWHLocCriteria").focus(function(){
		$("#cancelWHLocCriteria").parent().css({'outline':'thin dotted black'});
	});
	$("#cancelWHLocCriteria").blur(function(){
		$("#cancelWHLocCriteria").parent().css({'outline':''});
	});
	$("#searchWHLocCriteria").focus(function(){
		$("#searchWHLocCriteria").parent().css({'outline':'thin dotted black'});
	});
	$("#searchWHLocCriteria").blur(function(){
		$("#searchWHLocCriteria").parent().css({'outline':''});
	});
	$("#cancelWHLocHLCriteria").focus(function(){
		$("#cancelWHLocHLCriteria").parent().css({'outline':'thin dotted black'});
	});
	$("#cancelWHLocHLCriteria").blur(function(){
		$("#cancelWHLocHLCriteria").parent().css({'outline':''});
	});
	$("#searchWHLocHLCriteria").focus(function(){
		$("#searchWHLocHLCriteria").parent().css({'outline':'thin dotted black'});
	});
	$("#searchWHLocHLCriteria").blur(function(){
		$("#searchWHLocHLCriteria").parent().css({'outline':''});
	});
	$("#btnCancelPreSearchHL").focus(function(){
		$("#btnCancelPreSearchHL").parent().css({'outline':'thin dotted black'});
	});
	$("#btnCancelPreSearchHL").blur(function(){
		$("#btnCancelPreSearchHL").parent().css({'outline':''});
	});
	$("#btnChoosePreSearchHL").focus(function(){
		$("#btnChoosePreSearchHL").parent().css({'outline':'thin dotted black'});
	});
	$("#btnChoosePreSearchHL").blur(function(){
		$("#btnChoosePreSearchHL").parent().css({'outline':''});
	});
	$("#btnCancel2").focus(function(){
		$("#btnCancel2").parent().css({'outline':'thin dotted black'});
	});
	$("#btnCancel2").blur(function(){
		$("#btnCancel2").parent().css({'outline':''});
	});
	$('.dialog-main-wrapper_planSelection').find('#btnContinue2').focus(function(){
		$('.dialog-main-wrapper_planSelection').find('#btnContinue2').parent().css({'outline':'thin dotted black'});
	});
	$('.dialog-main-wrapper_planSelection').find('#btnContinue2').blur(function(){
		$('.dialog-main-wrapper_planSelection').find('#btnContinue2').parent().css({'outline':''});
	});
	$("#iUnderstand").focus(function(){
		$("#iUnderstand").parent().css({'outline':'thin dotted black'});
	});
	$("#iUnderstand").blur(function(){
		$("#iUnderstand").parent().css({'outline':''});
	});
$("#cancelPDButton").focus(function(){
		$("#cancelPDButton").parent().css({'outline':'thin dotted black'});
	});
	$("#cancelPDButton").blur(function(){
		$("#cancelPDButton").parent().css({'outline':''});
	});
	
	$("#printPDButton").focus(function(){
		$("#printPDButton").parent().css({'outline':'thin dotted black'});
	});
	$("#printPDButton").blur(function(){
		$("#printPDButton").parent().css({'outline':''});
	});
	$("#Clear").focus(function(){
		$("#Clear").parent().css({'outline':'thin dotted black'});
	});
	$("#Clear").blur(function(){
		$("#Clear").parent().css({'outline':''});
	});
	$("#Search").focus(function(){
		$("#Search").parent().css({'outline':'thin dotted black'});
	});
	$("#Search").blur(function(){
		$("#Search").parent().css({'outline':''});
	});
	$("#softMessage_OK").focus(function(){
		$("#softMessage_OK").parent().css({'outline':'thin dotted black'});
	});
	$("#softMessage_OK").blur(function(){
		$("#softMessage_OK").parent().css({'outline':''});
	});
	$("#filterTabLink1").focus(function(){
		$("#filterTabLink1").parent().css({'outline':'thin dotted black'});
	});
	$("#filterTabLink1").blur(function(){
		$("#filterTabLink1").parent().css({'outline':''});
	});
	$("#filterTabLink2").focus(function(){
		$("#filterTabLink2").parent().css({'outline':'thin dotted black'});
	});
	$("#filterTabLink2").blur(function(){
		$("#filterTabLink2").parent().css({'outline':''});
	});
	$('#filterDialog').children('#languagenavigator').children('input').each(function () {
		$(this).focus(function(){
			$(this).parent().css({'outline':'thin dotted black'});
		});
		$(this).blur(function(){
			$(this).parent().css({'outline':''});
		});
	});
	$('#filterDialog').children('#gendernavigator').children('input').each(function () {
		$(this).focus(function(){
			$(this).parent().css({'outline':'thin dotted black'});
		});
		$(this).blur(function(){
			$(this).parent().css({'outline':''});
		});
	});
	$('#filterDialog').children('#hospitalnavigator').children('input').each(function () {
		$(this).focus(function(){
			$(this).parent().css({'outline':'thin dotted black'});
		});
		$(this).blur(function(){
			$(this).parent().css({'outline':''});
		});
	});
	$('#filterDialog').children('#categorynavigator').children('input').each(function () {
		$(this).focus(function(){
			$(this).parent().css({'outline':'thin dotted black'});
		});
		$(this).blur(function(){
			$(this).parent().css({'outline':''});
		});
	});
	$('#filterDialog').children('#acceptingnewpatientsnavigator').children('input').each(function () {
		$(this).focus(function(){
			$(this).parent().css({'outline':'thin dotted black'});
		});
		$(this).blur(function(){
			$(this).parent().css({'outline':''});
		});
	});
	$('#filterDialog').children('#flagnavigator').children('input').each(function () {
		$(this).focus(function(){
			$(this).parent().css({'outline':'thin dotted black'});
		});
		$(this).blur(function(){
			$(this).parent().css({'outline':''});
		});
	});
	$('#filterDialog').children('#groupnavigator').children('input').each(function () {
		$(this).focus(function(){
			$(this).parent().css({'outline':'thin dotted black'});
		});
		$(this).blur(function(){
			$(this).parent().css({'outline':''});
		});
	});
	$('#filterDialog').children('#rollupnavigator').children('input').each(function () {
		$(this).focus(function(){
			$(this).parent().css({'outline':'thin dotted black'});
		});
		$(this).blur(function(){
			$(this).parent().css({'outline':''});
		});
	});
	$('#filterDialog').children('#classificationnavigator').children('input').each(function () {
		$(this).focus(function(){
			$(this).parent().css({'outline':'thin dotted black'});
		});
		$(this).blur(function(){
			$(this).parent().css({'outline':''});
		});
	});
	$('#filterDialog').children('#medicaldentalnavigator').children('input').each(function () {
		$(this).focus(function(){
			$(this).parent().css({'outline':'thin dotted black'});
		});
		$(this).blur(function(){
			$(this).parent().css({'outline':''});
		});
	});
	$('#filterDialog').children('#specialtynavigator').children('input').each(function () {
		$(this).focus(function(){
			$(this).parent().css({'outline':'thin dotted black'});
		});
		$(this).blur(function(){
			$(this).parent().css({'outline':''});
		});
	});
	$('#filterDialog').children('#orgnavigator').children('input').each(function () {
		$(this).focus(function(){
			$(this).parent().css({'outline':'thin dotted black'});
		});
		$(this).blur(function(){
			$(this).parent().css({'outline':''});
		});
	});
	$('.dialog-main-wrapper').children('.dialog-close-button').focus(function(){
		$(this).css({'outline':'thin dotted black'});
	});
	$('.dialog-main-wrapper').children('.dialog-close-button').blur(function(){
		$(this).css({'outline':''});
	});
	$("select#stateDD").focus(function(){
		$("select#stateDD").parent().css({'outline':'thin dotted black'});
	});
	$("select#stateDD").blur(function(){
		$("select#stateDD").parent().css({'outline':''});
	});
	$('#logInStatePopup').focus(function(){
		$('#logInStatePopup').css({'outline':'thin dotted black'});
	});
	$('#logInStatePopup').blur(function(){
		$('#logInStatePopup').css({'outline':''});
	});
	$('#logInStatePopup_es').focus(function(){
		$('#logInStatePopup_es').css({'outline':'thin dotted black'});
	});
	$('#logInStatePopup_es').blur(function(){
		$('#logInStatePopup_es').css({'outline':''});
	});
	
	$('td#imageDivLink2').focus(function(){
		$('td#imageDivLink2').parent().css({'outline':'thin dotted black'});
	});
	$('td#imageDivLink2').blur(function(){
		$('td#imageDivLink2').parent().css({'outline':''});
	});
	$('td#imageDivLink3').focus(function(){
		$('td#imageDivLink3').css({'outline':'thin dotted black'});
		
	});
	$('td#imageDivLink3').blur(function(){
		$('td#imageDivLink3').css({'outline':''});
	});
	$('td#imageDivLink4').focus(function(){
		$('td#imageDivLink4').parent().css({'outline':'thin dotted black'});
		
	});
	$('td#imageDivLink4').blur(function(){
		$('td#imageDivLink4').parent().css({'outline':''});
	});
	$('td#imageDivLink7').blur(function(){
		$('td#imageDivLink7').parent().css({'outline':''});
	});
	$('td#imageDivLink7').focus(function(){
		$('td#imageDivLink7').parent().css({'outline':'thin dotted black'});
		
	});
	$('td#imageDivLink6').blur(function(){
		$('td#imageDivLink6').parent().css({'outline':''});
	});
	$('td#imageDivLink6').focus(function(){
		$('td#imageDivLink6').parent().css({'outline':'thin dotted black'});
	});
$('#btnChooseStatePlan').blur(function(){
		$('#btnChooseStatePlan').parent().css({'outline':''});
	});
	$('#btnChooseStatePlan').focus(function(){
		$('#btnChooseStatePlan').parent().css({'outline':'thin dotted black'});
	});
$('#contWOPlan_ft').blur(function(){
		$('#contWOPlan_ft').css({'outline':''});
	});
	$('#contWOPlan_ft').focus(function(){
		$('#contWOPlan_ft').css({'outline':'thin dotted black'});
	});
}