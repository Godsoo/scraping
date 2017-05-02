/**
 * Custom jQuery dialog plugin to display the dialog box on a page.
 */

/*P8423a Sprint17 - Story4558 Changes  
  Resource_Type_Infosys_Offshore 
  Resource_ID_N206318 */

$.fn.doDialogDse = function(options, buttons,id){
	//base z-index;
	var z = 10000;
	var $this = $(this);
	$this.addClass('dialog-content_'+id);
	var $wrap = $this.wrap("<div class='dialog-content-wrap_" + id + "'></div>").parent();
	var $main_wrapper = $wrap.wrap("<div class='dialog-main-wrapper_" + id + "'></div>").parent();
	var $trans = $main_wrapper.prepend("<div class=dialog-transparent-border_" + id + "></div>").children(".dialog-transparent-border_" + id);
	
	var $subtitle = $wrap.prepend("<div class='dialog-subtitle_" + id + "'>"+$this.attr("subtitle_" + id)+"</div>").children(".dialog-subtitle_" + id);
	var $title = $subtitle.prepend("<div id='diaTitle_" + id + "' class=dialog-title_" + id + ">"+$this.attr("title_" + id)+"</div>").children(".dialog-title_" + id);
	
	//var $title = $wrap.prepend("<div class='dialog-title'>"+$this.attr('title')+"</div>").children('.dialog-title');
	
	var $close_button = $main_wrapper.prepend('<div class=dialog-close-button_' + id + '>&nbsp;</div>').children(".dialog-close-button_" + id);
	//var $dialogText = $close_button.prepend("<div class='dialog-dialogText'>"+$this.attr('dialogText')+"</div>").children('.dialog-dialogText');

	$wrap.append("<div class=dialog-dialogText_" + id + ">"+$this.attr("dialogText_" + id)+"</div>");
	if(id != null && id == 'planModal'){
		$wrap.append("<hr id='horizontalLineInPlanModal'>");
	}
	$wrap.append("<div class=dialog-button-holder_" + id + "><table><tr></tr></table></div>");
	if(id != null && id == 'planModal'){
		$wrap.append($('#textBelowButtonsModalBox').html());
	}

	var $buttonHolder = $(".dialog-button-holder_" + id + " table tr", $wrap);
	
	var calculated_width = 0;
	var calculated_height = 0;
	var button;

	for(var i=0; i < buttons.length; i++){
		button = buttons[i];
		$button = createButtonDse(button.id,button.value, button.url, button.onClick, button.arrow,id);
		$buttonHolder.append($button);
	}
	
	var o = options || {};
	var width = o.width || "360";
		
	width = parseFloat(width);
	
	var wrapHeight;
	var top = o.top || ($(window).height() - $wrap.height()) / 2 + $(window).scrollTop();
	var left = o.left || ($(window).width() - $wrap.width()) / 2 + $(window).scrollLeft() - 150;
	
	$main_wrapper.css("position","absolute");
	$wrap.css("position","absolute");
	$trans.css("position","absolute");
	$close_button.css("position","absolute");

	$main_wrapper.css("top",top + "px");
	$main_wrapper.css("left",left + "px");
	$wrap.css('top','15px');
	$wrap.css('left','15px');
	
	$main_wrapper.css("z-index",z);
	$trans.css("z-index",z+1);
	$wrap.css("z-index",z+2);
	$close_button.css("z-index",z+3);
	
	$this.width(width);
	if(o.height){
		$this.height(parseFloat(o.height));
	}
	
	$wrap.width(width + 64);
	$trans.width($wrap.width() + 30);
	/*-- START CHANGES P20751b ACO Branding - n596307 --*/
	if($.browser.msie && (buttons[0].id == "btnChoosePreSearchHL" || buttons[0].id == 'btnCancelPreSearchHL')){
		$trans.height($wrap.height()-132);
		$trans.width($wrap.width() + 41);
		$('.dialog-button-holder_preSearchHLDialogBox').css("padding-bottom","0px");
	}else if(buttons[0].id == "btnChoosePreSearchHL" || buttons[0].id == 'btnCancelPreSearchHL'){
		$trans.height($wrap.height()-132);
		$trans.width($wrap.width() + 41);
		if($.browser.msie){
			$trans.height($wrap.height()-152);
		}
	}
	/*-- END CHANGES P20751b ACO Branding - n596307 --*/
	/*P8423a Sprint17 - Story4558 Changes Start*/
	if($.browser.msie && (buttons[0].id == "btnChoosePreSearch" || buttons[0].id == 'btnCancelPreSearch')){
		$trans.height($wrap.height()-132);
		$trans.width($wrap.width() + 41);
		$('.dialog-button-holder_preSearchDialogBox').css("padding-bottom","0px");
	}else if($.browser.msie && (buttons[0].id == "btnChoosePreSearchSec" || buttons[0].id == 'btnCancelPreSearchSec')){
		$trans.height($wrap.height()-142);
		$trans.width($wrap.width() + 32);
		$('.dialog-button-holder_preSearchDialogBox').css("padding-bottom","0px");
	}else if(buttons[0].id == "btnChoosePreSearch" || buttons[0].id == 'btnCancelPreSearch'){
		$trans.height($wrap.height()-132);
		$trans.width($wrap.width() + 41);
		if($.browser.msie){
			$trans.height($wrap.height()-152);
		}
	}else if(buttons[0].id == "btnChoosePreSearchSec" || buttons[0].id == 'btnCancelPreSearchSec'){
		$trans.height($wrap.height()-145);
		$trans.width($wrap.width() + 30);
	}else if(buttons[0].id == "btnNo" || buttons[0].id == 'btnYes'){
		$wrap.width($wrap.width()+50);
		$trans.height($wrap.height()-136);
		$trans.width($wrap.width() + 30);
	}else if(buttons[0].id == "btnCloseAck"){
		$wrap.width($wrap.width()+50);
		$trans.height($wrap.height()-136);
		$trans.width($wrap.width() + 30);
		/*P8423a Sprint23 - Story9282 Changes Start*/
	}else if($.browser.msie && (buttons[0].id == "btnClearFilterDialogSec" || buttons[0].id == 'btnSearchFilterDialogSec')){
		$trans.height($('.dialog-dialogText_' + id).height() + 167);
		$trans.width($('.dialog-content-wrap_' + id).width() +30);
	}else if($.browser.msie && (buttons[0].id == "btnClearFilterDialog" || buttons[0].id == 'btnSearchFilterDialog')){
		$trans.height($('.dialog-dialogText_' + id).height() + 177);
		$trans.width($('.dialog-content-wrap_' + id).width() +40);
	}else if(buttons[0].id == "btnClearFilterDialogSec" || buttons[0].id == 'btnSearchFilterDialogSec'){
		$trans.height($('.dialog-dialogText_'+ id).height() + 167);
	}else if(buttons[0].id == "btnClearFilterDialog" || buttons[0].id == 'btnSearchFilterDialog'){
		$trans.height($wrap.height()-133);
	}else if($.browser.msie){
		$trans.height($wrap.height()+ 34);
	}
	else{
		$trans.height($wrap.height()+30);
    }
	/*P8423a Sprint17 - Story4558 Changes End*/
	
	$close_button.css("top", (30) + "px");
	$close_button.css("left", ($wrap.width() - 25) + "px");
	
	calculated_width =$trans.width();
	calculated_height =$trans.height();
	calculated_offset =$trans.offsetParent().offset().left;
	
	if(o.modal){
		var $modal = $("<div id=dialog_modal_id_" + id + " class=dialog-modal_" + id + "></div>");
		$main_wrapper.parent().append($modal);
		$modal.css('position','absolute');
		$modal.css('z-index',z-1);
		$modal.css('background-color','#000000');
		$modal.width($(document).width());
		$modal.height($(document).height() + 50);
		//$modal.css('top',"-" + ($modal.offsetParent().offset().top) + "px");
		//$modal.css('left',"-" + ($modal.offsetParent().offset().left) + "px");
		$modal.css('top',"-" + 0 + "px");
		$modal.css('left',"-" + 0 + "px");
		$modal.hide();
	}
	
	$close_button.click(function(){
		if($modal){
			$("html").css("overflow", "auto"); 
			$modal.hide();
		}
		$("html").css("overflow", "auto"); 
		$main_wrapper.hide();
		setAnnPlanSelCancel();
	});
	
	$this.bind('show',function(e, myName, myValue){
		//re-calcuate the top and left to show when the show event is called.
		var r_top = o.top || ($(window).height() - calculated_height) / 2 + $(window).scrollTop();
		var	r_left = o.left || ($(window).width() - calculated_width) / 2 + $(window).scrollLeft();
		$main_wrapper.css("top",r_top + "px");
		$main_wrapper.css("left",r_left + "px");
		$main_wrapper.show();
		
		if(o.modal && $modal){	
			$modal.show();
		}
		$this.css({display: 'block'});

		/*P8423a Sprint17 - Story4558 Changes Start*/
		if(buttons[0].id == "btnChoosePreSearch" || buttons[0].id == 'btnCancelPreSearch'){
			$trans.height($wrap.height()-132);
			if($.browser.msie){
				$trans.height($wrap.height()-152);
			}
		}else if(buttons[0].id == "btnChoosePreSearchSec" || buttons[0].id == 'btnCancelPreSearchSec'){
			$trans.height($wrap.height()-139);
		}else if(buttons[0].id == "btnClearFilterDialogSec" || buttons[0].id == 'btnSearchFilterDialogSec'){
			$trans.height($('.dialog-dialogText_'+ id).height() + 167);
			$trans.width($('.dialog-content-wrap_' + id).width() +30);
		}else if(buttons[0].id == "btnClearFilterDialog" || buttons[0].id == 'btnSearchFilterDialog'){
			$trans.height($('.dialog-dialogText_' + id).height() + 177);
			$trans.width($('.dialog-content-wrap_' + id).width() +40);
		}else if(buttons[0].id == "btnNo" || buttons[0].id == 'btnYes'){
			$trans.height($wrap.height()- 130);
		}else if(buttons[0].id == "btnCloseAck"){
			$trans.height($wrap.height()- 130);
		}else{
			$trans.height($wrap.height()+30);
	    }
		/*P8423a Sprint17 - Story4558 Changes End*/
	});
	
	$this.bind('hide',function(e, myName, myValue){
		$close_button.click();
	});
	
	if(o.draggable){
		$title.css('cursor','move');
		$title.bind('mousedown',function(){
			$main_wrapper.draggable();
		});
		
		$title.bind('mouseup',function(){
			$main_wrapper.draggable("destroy");
		});
	}
	// Need to be checked for browser compatibilty
	if(o.closeOnEscape){
	      document.onkeydown = function(e){
	          if (e == null) { // ie
	            keycode = event.keyCode;
	          } else { // mozilla
	            keycode = e.which;
	          }
	          if(keycode == 27){ // escape, close box
	      		$close_button.click();
	          }
	        }; 
	}
	$main_wrapper.hide();

	return $this;
};

function createButtonDse(id, name, url, onClick, arrow,divId){
	if(arrow){
		right_class = "gold_button_right_" + divId;
	}else{
		right_class = "gold_button_right_" + divId;
	}
	var tdButtonClass="gold_button_left_" + divId;
	
	if (name == 'CANCEL'){
		tdButtonClass="cancelGoldButton_rd";
	}
	if (name == 'CONTINUE'){
		tdButtonClass="continueGoldButton_rd";
	}
	/*P8423a Sprint15 - StoryNew Start*/
	if (name == 'CHOOSE PLAN'){
		tdButtonClass="choosePlanGoldButton";
	}
	/*P8423a Sprint15 - StoryNew End*/
	

//	pshydv
	var showContinueWithoutPlan = false;
	if($('#switchForContinueWithOutPlanLink')!=null && $.trim($('#switchForContinueWithOutPlanLink').text()) == 'ON')
	{
		showContinueWithoutPlan = true;
	}
	if((id == "btnChoosePlan" && showContinueWithoutPlan) || id == "btnChooseStatePlan"){
		var $button = $('<td class=dialog-button-cell_' + divId + '></td>');
		$button_link = $('td' , $button);
	}else{
		var $button = $('<td class=dialog-button-cell_' + divId + '><a id="'+ id +'" class=GoldButtonLink_' + divId + ' onclick="'+onClick+'" href="' + url + '" ></a></td>');
		$button_link = $('a' , $button);
	}
	var ua= $.browser;
	var withoutPlanOption = $('#withoutPlanOptionDiv').html();
	/*P8423a Sprint15 - StoryNew Start */
	if(ua.version < 7.0 && id == "btnChoosePlan"){
		if(showContinueWithoutPlan){
			if($.getUrlVar('site_id') == 'dse' && $.getUrlVar('langPref') == 'sp'){
				$button.prepend('<table cellpadding="0" cellspacing="0" style="position: static; left: 30px;z-index:99999999;">' + 
						'<tr style="z-index:99999999;">'+
						'<td style="z-index:99999999;"><a style="color:#005CA1;font-size:13px;text-decoration: underline;z-index:99999999;" href="javascript:closeGenericModalBox();setAnnPlanSelCancel();" id="contWOPlan_ft">'+withoutPlanOption+'</a></td>'+
						'<td style="z-index:99999999;">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</td>'+
						'<td style="z-index:99999999;" class='+tdButtonClass+'><a style="display: block; width:105px; height:30px;" id="'+ id +'" class=GoldButtonLink_' + divId + ' onclick="'+onClick+'" href="' + url + '"><img src="/dse/cms/codeAssets/images/continue_button_spanish.png" alt="Continuar"/></a></td>'+
						'</tr>'+
				'</table>');				
			}
			else{
			$button.prepend('<table cellpadding="0" cellspacing="0" style="position: static; left: 40px;z-index:99999999;">' + 
					'<tr style="z-index:99999999;">'+
					'<td style="z-index:99999999;"><a style="color:#005CA1;font-size:13px;text-decoration: underline;z-index:99999999;" href="javascript:closeGenericModalBox();setAnnPlanSelCancel();" id="contWOPlan_ft">Continue without choosing a plan</a></td>'+
					'<td style="z-index:99999999;">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</td>'+
					'<td style="z-index:99999999;" class='+tdButtonClass+'><a style="display: block; width:105px; height:30px;" id="'+ id +'" class=GoldButtonLink_' + divId + ' onclick="'+onClick+'" href="' + url + '"><img src="/dse/cms/codeAssets/images/continue_button.png" alt="Continue"/></a></td>'+
					'</tr>'+
			'</table>');
			}
		}
		else{
			$button_link.prepend('<table cellpadding="0" cellspacing="0" style="position: static; left: 150px;z-index:99999999;">' + 
					'<tr style="z-index:99999999;">'+
					'<td style="z-index:99999999;" class='+tdButtonClass+'><img src="/dse/cms/codeAssets/images/continue_button.png" alt="Continue"/></td>'+
					'</tr>'+
			'</table>');
		}
	}else if(id == "btnChoosePlan")
	{
		if(showContinueWithoutPlan){
			if($.getUrlVar('site_id') == 'dse' && $.getUrlVar('langPref') == 'sp'){
				$button.prepend('<table cellpadding="0" cellspacing="0" style="position: relative; left: 30px">' + 
						'<tr>'+
						'<td><a style="color:#005CA1;font-size:13px;text-decoration: underline;" href="javascript:closeGenericModalBox();setAnnPlanSelCancel();" id="contWOPlan_ft">'+withoutPlanOption+'</a></td>'+
						'<td>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</td>'+
						'<td class='+tdButtonClass+'><a style="display: block; width:105px; height:30px;" id="'+ id +'" class=GoldButtonLink_' + divId + ' onclick="'+onClick+'" href="' + url + '" ><img src="/dse/cms/codeAssets/images/continue_button_spanish.png" alt="Continuar"/></a></td>'+
						'</tr>'+
				'</table>');	
			}
			else{
			$button.prepend('<table cellpadding="0" cellspacing="0" style="position: relative; left: 40px">' + 
					'<tr>'+
					'<td><a style="color:#005CA1;font-size:13px;text-decoration: underline;" href="javascript:closeGenericModalBox();setAnnPlanSelCancel();" id="contWOPlan_ft">Continue without choosing a plan</a></td>'+
					'<td>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</td>'+
					'<td class='+tdButtonClass+'><a style="display: block; width:105px; height:30px;" id="'+ id +'" class=GoldButtonLink_' + divId + ' onclick="'+onClick+'" href="' + url + '" ><img src="/dse/cms/codeAssets/images/continue_button.png" alt="Continue"/></a></td>'+
					'</tr>'+
			'</table>');
			}
		}
		else{
			$button_link.prepend('<table cellpadding="0" cellspacing="0" style="position: relative; left: 150px">' + 
					'<tr>'+
					'<td class='+tdButtonClass+'><img src="/dse/cms/codeAssets/images/continue_button.png" alt="Continue"/></td>'+
					'</tr>'+
			'</table>');

		}
	}
	/*-- START CHANGES P20941a August2014 - Medicare Advantage - n596307 --*/
	else if(id == "btnChooseStatePlan")
	{
		/*--- START CHANGES P23695 Medicare Spanish Translation - n596307 ---*/
		var withPlanOption = $('#withPlanOptionDiv').html();
		var withoutPlanOption = $('#withoutPlanOptionDiv').html();
		/*-- START CHANGES P8551c QHP_IVL PCR - n204189 --*/
		if($.getUrlVar('site_id') == 'medicare' && $.getUrlVar('langPref') == 'sp'){
			redButton = 'choosePlanNewGoldButtonSpanish';
		}
		else{
			redButton = 'choosePlanNewGoldButton';
		}
		if(showContinueWithoutPlan)
		{
			if($.getUrlVar('site_id') == 'medicare' && $.getUrlVar('langPref') == 'sp'){
				$button.prepend('<table cellpadding="0" cellspacing="0" style="position: relative; left: 2px">' + 
						'<tr>'+
						'<td class="'+redButton+'"><a style="display: block; width:105px; height:30px;" id="'+ id +'" class=GoldButtonLink_' + divId + ' onclick="'+onClick+'" href="' + url + '"><img src="/dse/cms/codeAssets/images/continue_button_spanish.png" alt="Continue"/></a></td>'+
						'<td class="orTextModal_ft">&nbsp;</td>'+
						'<td id="withoutPlan">'+withoutPlanOption+'</td>'+
						'</tr>'+
				'</table>');
			}else{
				$button.prepend('<table cellpadding="0" cellspacing="0" style="position: relative; left: 2px">' + 
						'<tr>'+
						'<td class="'+redButton+'"><a style="display: block; width:105px; height:30px;" id="'+ id +'" class=GoldButtonLink_' + divId + ' onclick="'+onClick+'" href="' + url + '"><img src="/dse/cms/codeAssets/images/continue_button.png" alt="Continue"/></a></td>'+
						'<td class="orTextModal_ft">&nbsp;</td>'+
						'<td id="withoutPlan">'+withoutPlanOption+'</td>'+
						'</tr>'+
				'</table>');
			}
		}
		else
		{
			$button.prepend('<table cellpadding="0" cellspacing="0" style="position: relative; left: 2px">' + 
					'<tr>'+
					'<td class="'+redButton+'"><a style="display: block; width:100px; height:20px;" id="'+ id +'" class=GoldButtonLink_' + divId + ' onclick="'+onClick+'" href="' + url + '"><img src="/dse/cms/codeAssets/images/continue_button.png" alt="Continue"/></a></td>'+
					'</tr>'+
			'</table>');
		
		}
		/*-- END CHANGES P8551c QHP_IVL PCR - n204189 --*/
	}
	/*-- END CHANGES P20941a August2014 - Medicare Advantage - n596307 --*/
	else if(id == "btnChoosePreSearchSec" || id == 'btnCancelPreSearchSec'){
		/*P8423a Sprint17 - Story4558 Changes Start*/
		$button_link.prepend('<table cellpadding="0" cellspacing="0" style="position: relative; left: 2px">' + 
				'<tr>'+
				'<td class="preSearch_select_button_secure"><label style="cursor: pointer">' + name + '</label></td>'+
			'</tr>'+
		'</table>');
		/*P8423a Sprint17 - Story4558 Changes End*/
		/*P8423a Sprint23 - Story9282 Changes Start*/
	}else if(id == "btnClearFilterDialogSec" || id == 'btnSearchFilterDialogSec'){
		$button_link.prepend('<table cellpadding="0" cellspacing="0" style="position: relative; left: 2px">' + 
				'<tr>'+
				'<td class="gold_button_filterDialog_left"><img style="cursor: pointer;text-align: center;padding-bottom:3px;border:medium none;" src="/dse/assets/images/BTN_gold_left.gif" alt=""></td>'+
				'<td class="filter_gender_buttonSec"><label style="cursor: pointer">' + name + '</label></td>'+
				'<td class="gold_button_filterDialog_right"><img style="cursor: pointer;text-align: center;padding-bottom:3px;border:medium none;" src="/dse/assets/images/BTN_gold_right.gif" alt=""></td>'+
			'</tr>'+
		'</table>');
		
	}else if(id == "btnClearFilterDialog" || id == 'btnSearchFilterDialog'){
		$button_link.prepend('<table cellpadding="0" cellspacing="0" style="position: relative; left: 2px">' + 
				'<tr>'+
				'<td><img style="cursor: pointer;text-align: center;padding-bottom:3px;border:medium none;" src="/dse/assets/images/go_btn_left.jpg" alt=""></td>'+
				'<td class="filter_gender_button"><label style="cursor: pointer">' + name + '</label></td>'+
				'<td><img style="cursor: pointer;text-align: center;padding-bottom:3px;border:medium none;" src="/dse/assets/images/go_btn_right.jpg" alt=""></td>'+
			'</tr>'+
		'</table>');
		/*P8423a Sprint23 - Story9282 Changes End*/
	}
	/*-- START CHANGES P20751b ACO Branding - n596307 --*/
	else if(id == "btnChoosePreSearchHL" || id == 'btnCancelPreSearchHL'){
		$button_link.prepend('<table cellpadding="0" cellspacing="0" style="position: relative; left: 2px">' + 
				'<tr>'+
				'<td class="preSearch_select_button"><label style="cursor: pointer">' + name + '</label></td>'+
			'</tr>'+
		'</table>');
	}
	/*-- END CHANGES P20751b ACO Branding - n596307 --*/
	else if(id == "btnChoosePreSearch" || id == 'btnCancelPreSearch'){
		$button_link.prepend('<table cellpadding="0" cellspacing="0" style="position: relative; left: 2px">' + 
				'<tr>'+
				'<td class="preSearch_select_button"><label style="cursor: pointer">' + name + '</label></td>'+
			'</tr>'+
		'</table>');
	}else if(id == "btnNo" || id== 'btnYes'){
		$button_link.prepend('<table cellpadding="0" cellspacing="0" style="position: relative; left: 2px">' + 
				'<tr>'+
				'<td class="gold_button_noPat_left"><img style="cursor: pointer;text-align: center;padding-bottom:3px;border:medium none;" src="/dse/assets/images/BTN_gold_left.gif" alt=""></td>'+
				'<td class="noPat_select_button"><label style="cursor: pointer">' + name + '</label></td>'+
				'<td class="gold_button_noPat_right"><img style="cursor: pointer;text-align: center;padding-bottom:3px;border:medium none;" src="/dse/assets/images/BTN_gold_right.gif" alt=""></td>'+
			'</tr>'+
		'</table>');
	}else if(id == "btnCloseAck"){
		$button_link.prepend('<table cellpadding="0" cellspacing="0" style="position: relative; left: 2px">' + 
				'<tr>'+
				'<td class="gold_button_noPat_left"><img style="cursor: pointer;text-align: center;padding-bottom:3px;border:medium none;" src="/dse/assets/images/BTN_gold_left.gif" alt=""></td>'+
				'<td class="noPat_select_button"><label style="cursor: pointer">' + name + '</label></td>'+
				'<td class="gold_button_noPat_right"><img style="cursor: pointer;text-align: center;padding-bottom:3px;border:medium none;" src="/dse/assets/images/BTN_gold_right.gif" alt=""></td>'+
			'</tr>'+
		'</table>');
	}else if(id == "btnCancel2"){
		$button_link.prepend('<table cellpadding="0" cellspacing="0" style="position: relative; left: 2px">' + 
				'<tr>'+
				'<td class='+tdButtonClass+'>Cancel</td>'+
			'</tr>'+
		'</table>');
	}
	else if(id == "btnContinue2"){
		$button_link.prepend('<table cellpadding="0" cellspacing="0" style="position: relative; left: 2px">' + 
				'<tr>'+
				'<td class='+tdButtonClass+'>Continue</td>'+
			'</tr>'+
		'</table>');
	}else{
		$button_link.prepend('<table cellpadding="0" cellspacing="0" style="position: relative; left: 2px">' + 
				'<tr>'+
				'<td class='+tdButtonClass+'>&nbsp;</td>'+
			'</tr>'+
		'</table>');
	}
	/*P8423a Sprint15 - StoryNew End */
	
	/* Original Button Code
	 * $button_link.prepend('<table cellpadding="0" cellspacing="0" style="position: relative; left: 2px">' + 
			'<tr>'+
			'<td class="gold_button_left">&nbsp;</td>'+
			'<td class="gold_button"><label style="cursor: pointer">' + name + '</label></td>'+
			'<td class="' + right_class + '">&nbsp;</td>'+
		'</tr>'+
	'</table>');
	 */
	return $button;
}

/***************************************************************************************************************
* Below function will create Modal popup with default UI and there should not be any changes made in below
* code in future. If any unique change requires in modal box then please do it in respective javascript file. 
* 									  PLEASE DO NOT MODIFY BELOW FUNCTIONS.
/**************************************************************************************************************/

$.fn.doDialogDefault = function(options, buttons){
	var z = 10000;
	
	var $this = $(this);
	$this.addClass('dialog-content');
	var $wrap = $this.wrap("<div class='dialog-content-wrap'></div>").parent();
	var $main_wrapper = $wrap.wrap("<div class='dialog-main-wrapper'></div>").parent();
	var $trans = $main_wrapper.prepend('<div class="dialog-transparent-border"></div>').children('.dialog-transparent-border');
	var $title = $wrap.prepend("<div class='dialog-title'>"+$this.attr('title')+"</div>").children('.dialog-title');
	var $close_button = $main_wrapper.prepend('<div class="dialog-close-button">&nbsp;</div>').children('.dialog-close-button');
	$wrap.append("<div class='dialog-button-holder'><table><tr></tr></table></div>");

	var $buttonHolder = $('.dialog-button-holder table tr', $wrap);
	
	var calculated_width = 0;
	var calculated_height = 0;
	var button;

	for(var i=0; i < buttons.length; i++){
		button = buttons[i];
		$button = createButtonDefault(button.id,button.value, button.url, button.onClick, button.arrow);
		$buttonHolder.append($button);
	}
	
	var o = options || {};
	var width = o.width || "360";
		
	width = parseFloat(width);
	
	var wrapHeight;
	if($.browser.msie)
	{
		
	}
	var top = o.top || ($(window).height() - $wrap.height()) / 2 + $(window).scrollTop();
	var left = o.left || ($(window).width() - $wrap.width()) / 2 + $(window).scrollLeft() - 150;
	
	$main_wrapper.css("position","absolute");
	$wrap.css("position","absolute");
	$trans.css("position","absolute");
	$close_button.css("position","absolute");

	$main_wrapper.css("top",top + "px");
	$main_wrapper.css("left",left + "px");
	$wrap.css('top','15px');
	$wrap.css('left','15px');
	
	$main_wrapper.css("z-index",z);
	$trans.css("z-index",z+1);
	$wrap.css("z-index",z+2);
	$close_button.css("z-index",z+3);
	
	$this.width(width);
	if(o.height){
		$this.height(parseFloat(o.height));
	}
	
	$wrap.width(width + 64);
	$trans.width($wrap.width() + 30);
	if($.browser.msie){
		$trans.height($wrap.height()+ 34);
	}
	else
	{
		$trans.height($wrap.height()+30);
    }
	$close_button.css("top", (30) + "px");
	$close_button.css("left", ($wrap.width() - 25) + "px");
	
	calculated_width =$trans.width();
	calculated_height =$trans.height();
	calculated_offset =$trans.offsetParent().offset().left;
	
	if(o.modal){
		var $modal = $("<div class='dialog-modal'></div>");
		$main_wrapper.parent().append($modal);
		$modal.css('position','absolute');
		$modal.css('z-index',z-1);
		$modal.css('background-color','#000000');
		$modal.width($(document).width());
		$modal.height($(document).height());
		$modal.css('top',"-" + ($modal.offsetParent().offset().top) + "px");
		$modal.css('left',"-" + ($modal.offsetParent().offset().left) + "px");
		$modal.hide();
	}
	
	$close_button.click(function(){
		if($modal){
			$modal.hide();
		}
		$main_wrapper.hide();
	});
	
	$this.bind('show',function(e, myName, myValue){
		//re-calcuate the top and left to show when the show event is called.
		
		var r_top = o.top || ($(window).height() - calculated_height) / 2 + $(window).scrollTop();
		var	r_left = o.left || ($(window).width() - calculated_width) / 2 + $(window).scrollLeft();

		$main_wrapper.css("top",r_top + "px");
		$main_wrapper.css("left",r_left + "px");
		$main_wrapper.show();
		if(o.modal && $modal)
		{
			$modal.show();

		}
		$this.css({display: 'block'});
		if($.browser.msie){
			$trans.height($wrap.height()+ 34);
		}
		else
		{
			$trans.height($wrap.height()+30);
	    }
	});
	
	$this.bind('hide',function(e, myName, myValue){
		$close_button.click();
	});
	
	if(o.draggable){
		$title.css('cursor','move');
		$title.bind('mousedown',function(){
			$main_wrapper.draggable();
		});
		
		$title.bind('mouseup',function(){
			$main_wrapper.draggable("destroy");
		});
	}
	$main_wrapper.hide();
	
	return $this;
};


function createButtonDefault(id, name, url, onClick, arrow){
	if(arrow){
		right_class = "gold_button_right_arrow";
	}else{
		right_class = "gold_button_right";
	}
	var $button = $('<td class="dialog-button-cell"><a id="'+ id +'" class="GoldButtonLink" onclick="'+onClick+'" href="' + url + '" ></a></td>');
	
	$button_link = $('a' , $button);
	$button_link.prepend('<table cellpadding="0" cellspacing="0" style="position: relative; left: 2px">' + 
			'<tr>'+
			'<td class="gold_button_left">&nbsp;</td>'+
			'<td class="gold_button"><label style="cursor: pointer">' + name + '</label></td>'+
			'<td class="' + right_class + '">&nbsp;</td>'+
		'</tr>'+
	'</table>');
	return $button;
}

/*-- START CHANGES P20941a August2014 - Medicare Advantage - n596307 --*/
$.fn.doDialogCustomDse = function(options, buttons,id){
	//base z-index;
	var z = 10000;
	var $this = $(this);
	$this.addClass('dialog-content_'+id);
	var $wrap = $this.wrap("<div class='dialog-content-wrap_" + id + "'></div>").parent();
	var $main_wrapper = $wrap.wrap("<div class='dialog-main-wrapper_" + id + "'></div>").parent();
	var $trans = $main_wrapper.prepend("<div class=dialog-transparent-border_" + id + "></div>").children(".dialog-transparent-border_" + id);

	var $subtitle = $wrap.prepend("<div class='dialog-subtitle_" + id + "'>"+$this.attr("subtitle_" + id)+"</div>").children(".dialog-subtitle_" + id);
	var $title = $subtitle.prepend("<div id='diaTitle_" + id + "' class=dialog-title_" + id + ">"+$this.attr("title_" + id)+"</div>").children(".dialog-title_" + id);

//	var $title = $wrap.prepend("<div class='dialog-title'>"+$this.attr('title')+"</div>").children('.dialog-title');

	var $close_button = $main_wrapper.prepend('<div class=dialog-close-button_' + id + '>&nbsp;</div>').children(".dialog-close-button_" + id);
//	var $dialogText = $close_button.prepend("<div class='dialog-dialogText'>"+$this.attr('dialogText')+"</div>").children('.dialog-dialogText');

	$wrap.append("<div class=dialog-dialogText_" + id + ">"+$this.attr("dialogText_" + id)+"</div>");
	//Create div for new section of state plans
	$wrap.append("<div class=dialog-dialogDynamicText_" + id + ">"+$this.attr("dialogDynamicText_" + id)+"</div>");
	$wrap.append("<div class=dialog-button-holder_" + id + "><table><tr></tr></table></div>");

	var $buttonHolder = $(".dialog-button-holder_" + id + " table tr", $wrap);

	var calculated_width = 0;
	var calculated_height = 0;
	var button;

	for(var i=0; i < buttons.length; i++){
		button = buttons[i];
		$button = createButtonDse(button.id,button.value, button.url, button.onClick, button.arrow,id);
		$buttonHolder.append($button);
	}

	var o = options || {};
	var width = o.width || "360";

	width = parseFloat(width);

	var wrapHeight;
	var top = o.top || ($(window).height() - $wrap.height()) / 2 + $(window).scrollTop();
	var left = o.left || ($(window).width() - $wrap.width()) / 2 + $(window).scrollLeft() - 150;

	$main_wrapper.css("position","absolute");
	$wrap.css("position","absolute");
	$trans.css("position","absolute");
	$close_button.css("position","absolute");

	$main_wrapper.css("top",top + "px");
	$main_wrapper.css("left",left + "px");
	$wrap.css('top','15px');
	$wrap.css('left','15px');

	$main_wrapper.css("z-index",z);
	$trans.css("z-index",z+1);
	$wrap.css("z-index",z+2);
	$close_button.css("z-index",z+3);

	$this.width(width);
	if(o.height){
		$this.height(parseFloat(o.height));
	}

	$wrap.width(width + 64);
	$trans.width($wrap.width() + 30);
	/*P8423a Sprint17 - Story4558 Changes Start*/
	if($.browser.msie && (buttons[0].id == "btnChoosePreSearch" || buttons[0].id == 'btnCancelPreSearch')){
		$trans.height($wrap.height()-132);
		$trans.width($wrap.width() + 41);
		$('.dialog-button-holder_preSearchDialogBox').css("padding-bottom","0px");
	}else if($.browser.msie && (buttons[0].id == "btnChoosePreSearchSec" || buttons[0].id == 'btnCancelPreSearchSec')){
		$trans.height($wrap.height()-142);
		$trans.width($wrap.width() + 32);
		$('.dialog-button-holder_preSearchDialogBox').css("padding-bottom","0px");
	}else if(buttons[0].id == "btnChoosePreSearch" || buttons[0].id == 'btnCancelPreSearch'){
		$trans.height($wrap.height()-132);
		$trans.width($wrap.width() + 41);
		if($.browser.msie){
			$trans.height($wrap.height()-152);
		}
	}else if(buttons[0].id == "btnChoosePreSearchSec" || buttons[0].id == 'btnCancelPreSearchSec'){
		$trans.height($wrap.height()-145);
		$trans.width($wrap.width() + 30);
	}else if(buttons[0].id == "btnNo" || buttons[0].id == 'btnYes'){
		$wrap.width($wrap.width()+50);
		$trans.height($wrap.height()-136);
		$trans.width($wrap.width() + 30);
	}else if(buttons[0].id == "btnCloseAck"){
		$wrap.width($wrap.width()+50);
		$trans.height($wrap.height()-136);
		$trans.width($wrap.width() + 30);
		/*P8423a Sprint23 - Story9282 Changes Start*/
	}else if($.browser.msie && (buttons[0].id == "btnClearFilterDialogSec" || buttons[0].id == 'btnSearchFilterDialogSec')){
		$trans.height($('.dialog-dialogText_' + id).height() + 167);
		$trans.width($('.dialog-content-wrap_' + id).width() +30);
	}else if($.browser.msie && (buttons[0].id == "btnClearFilterDialog" || buttons[0].id == 'btnSearchFilterDialog')){
		$trans.height($('.dialog-dialogText_' + id).height() + 177);
		$trans.width($('.dialog-content-wrap_' + id).width() +40);
	}else if(buttons[0].id == "btnClearFilterDialogSec" || buttons[0].id == 'btnSearchFilterDialogSec'){
		$trans.height($('.dialog-dialogText_'+ id).height() + 167);
	}else if(buttons[0].id == "btnClearFilterDialog" || buttons[0].id == 'btnSearchFilterDialog'){
		$trans.height($wrap.height()-133);
	}else if($.browser.msie){
		$trans.height($wrap.height()+ 34);
	}
	else{
		$trans.height($wrap.height()+30);
	}
	/*P8423a Sprint17 - Story4558 Changes End*/

	$close_button.css("top", (30) + "px");
	$close_button.css("left", ($wrap.width() - 25) + "px");

	calculated_width =$trans.width();
	calculated_height =$trans.height();
	calculated_offset =$trans.offsetParent().offset().left;

	if(o.modal){
		var $modal = $("<div id=dialog_modal_id_" + id + " class=dialog-modal_" + id + "></div>");
		$main_wrapper.parent().append($modal);
		$modal.css('position','absolute');
		$modal.css('z-index',z-1);
		$modal.css('background-color','#000000');
		$modal.width($(document).width());
		$modal.height($(document).height() + 50);
		//$modal.css('top',"-" + ($modal.offsetParent().offset().top) + "px");
		//$modal.css('left',"-" + ($modal.offsetParent().offset().left) + "px");
		$modal.css('top',"-" + 0 + "px");
		$modal.css('left',"-" + 0 + "px");
		$modal.hide();
	}

	$close_button.click(function(){
		if($modal){
			$("html").css("overflow", "auto"); 
			$modal.hide();
		}
		$("html").css("overflow", "auto"); 
		$main_wrapper.hide();
		setAnnPlanSelCancel();
	});

	$this.bind('show',function(e, myName, myValue){
		//re-calcuate the top and left to show when the show event is called.
		var r_top = o.top || ($(window).height() - calculated_height) / 2 + $(window).scrollTop();
		//var r_top =($(document).height() - calculated_height) / 2;
		var	r_left = o.left || ($(window).width() - calculated_width) / 2 + $(window).scrollLeft();
		$main_wrapper.css("top",r_top + "px");
		$main_wrapper.css("left",r_left + "px");
		$main_wrapper.show();

		if(o.modal && $modal){	
			$modal.show();
		}
		$this.css({display: 'block'});

		/*P8423a Sprint17 - Story4558 Changes Start*/
		if(buttons[0].id == "btnChoosePreSearch" || buttons[0].id == 'btnCancelPreSearch'){
			$trans.height($wrap.height()-132);
			if($.browser.msie){
				$trans.height($wrap.height()-152);
			}
		}else if(buttons[0].id == "btnChoosePreSearchSec" || buttons[0].id == 'btnCancelPreSearchSec'){
			$trans.height($wrap.height()-139);
		}else if(buttons[0].id == "btnClearFilterDialogSec" || buttons[0].id == 'btnSearchFilterDialogSec'){
			$trans.height($('.dialog-dialogText_'+ id).height() + 167);
			$trans.width($('.dialog-content-wrap_' + id).width() +30);
		}else if(buttons[0].id == "btnClearFilterDialog" || buttons[0].id == 'btnSearchFilterDialog'){
			$trans.height($('.dialog-dialogText_' + id).height() + 177);
			$trans.width($('.dialog-content-wrap_' + id).width() +40);
		}else if(buttons[0].id == "btnNo" || buttons[0].id == 'btnYes'){
			$trans.height($wrap.height()- 130);
		}else if(buttons[0].id == "btnCloseAck"){
			$trans.height($wrap.height()- 130);
		}else{
			$trans.height($wrap.height()+30);
		}
		/*P8423a Sprint17 - Story4558 Changes End*/
	});

	$this.bind('hide',function(e, myName, myValue){
		$close_button.click();
	});

	if(o.draggable){
		$title.css('cursor','move');
		$title.bind('mousedown',function(){
			$main_wrapper.draggable();
		});

		$title.bind('mouseup',function(){
			$main_wrapper.draggable("destroy");
		});
	}
	// Need to be checked for browser compatibilty
	if(o.closeOnEscape){
		document.onkeydown = function(e){
			if (e == null) { // ie
				keycode = event.keyCode;
			} else { // mozilla
				keycode = e.which;
			}
			if(keycode == 27){ // escape, close box
				$close_button.click();
			}
		}; 
	}
	$main_wrapper.hide();

	return $this;
};
/*-- END CHANGES P20941a August2014 - Medicare Advantage - n596307 --*/