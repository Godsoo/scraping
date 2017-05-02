// ********* This plugin depends on JQeury core. **********//

//This method starts by going through all of the active 'select' tags on a page (form inputs) and replaces them 
// with mocked up 'Fake' selects. The selects are smooth and good looking. 
// The style for the select boxes are defined in 'fakeSelects.css'. 
//These selects also include the capability to drive other select boxes. For example, if there are multiple 
//family members who each have a seperate set of data in a second dropdown box, then one box may drive the other. 
// For an example, please see claimSearchBox.jsp.
function convertFormsToDynamicForms(divId) {
	
		var $select = $('#'+divId);
		if ($select.parents('.' + divId + '_select').length > 0) {
			//return;
		}
		$select.css("display", "none");
		var selectSize = !isNaN(parseInt($select.width())) ? $select.width() + "px" : "auto";
		if(divId == 'otherResultsSelect'){
			var $wrapper = $select.wrap('<div tabindex=0 class=' + divId + '_select value=' + $('option:selected', $select).attr("value") + '" style="width: 136px;"></div>').parent();
		}else{
			var $wrapper = $select.wrap('<div tabindex="0" class=' + divId + '_select value=' + $('option:selected', $select).attr("value") + '" style="width: '+ selectSize +'"></div>').parent();
		}
		
		//build html inside wrapper
		// Use the text from 'option:selected' as the initial value for the span. 
		var selectId = $select.attr("id");
		
		if(divId == 'otherResultsSelect'){
				$wrapper.prepend('<span style="width: 136px;">' + $('option:selected', $select).text() + '</span><ul id="' + selectId + '_prim" style="width: ' + $select.width() + 'px;"/>');
		}else{
				$wrapper.prepend('<span style="width: ' + ($select.width() - 5) + 'px;">' + $('option:selected', $select).text() + '</span><ul tabindex="0" id="' + selectId + '_prim" style="width: ' + $select.width() + 'px;"/>');	
		}
		
		
		var $ul = $('ul', $wrapper);
		$('option', $select).each(function(){
			
			var oLi = $('<li class="' + $(this).attr("class") + '" idToFilter="' + $(this).attr("idToFilter") + '" classToDisplay="' + $(this).attr("classToDisplay") + '"><a tabindex="0" href="#" index="'+'" value="' + $(this).attr("value") + '">'+ $(this).html() +'</a></li>');
			if ($(this).css("display") == 'none') {
				oLi.addClass('hiddenDropdown');
			} else {
				oLi.addClass('visibleDropdown');
			}
			if ($(this).attr("value") == "please select") {
				oLi.css("display", "none");
			}
			$ul.append(oLi);
			setDropdownWidth($ul);
		});

		$('.' + divId + '_select li').keydown(function(event){ 
		    var keyCode = (event.keyCode ? event.keyCode : event.which);   
		    if (keyCode == 13) {
		       $(this).trigger('mouseup');
		    }
		});
		$('.' + divId + '_select li').bind('mousedown', function(evt) {
		evt.stopPropagation();
		
		return false;
	});
	
	$('.' + divId + '_select li').bind('click', function(evt) {
		evt.stopPropagation();
		
		return false;
	});
		
	//This method gets called when we select a dropdown and 'mouse up' on the dropdown. 
	// In effect, this method defines the behaviour for when an element is selected. 
	$('.' + divId + '_select li').bind('mouseup', function(evt) {
		evt.stopPropagation();
		$('.' + divId + '_select').removeClass('CurrentSelectBox').find('ul').hide();
		$("body").unbind("click");
		
		//Find the original combo box and set the input. Get the form with the name the same as 
			// the id of the parent div tag. 
		if(divId == 'narrowSearchResultsSelect'){
			var valueToSet = $(this).find('a').attr("value");
			if(valueToSet == "" || valueToSet == undefined){
				valueToSet = $(this).children().attr("value");
			}
		}else{
		var valueToSet = $(this).children().attr("value");
		}
		//This is the real select box
		$(this).parents('.' + divId + '_select').find(divId + '_select:first').val(valueToSet);
		//This is the fake select box - se the attribute
		$(this).parents('.' + divId + '_select').attr("value", valueToSet);
		//Set the text in the fake box. 
		$(this).parents('.' + divId + '_select').find("span:first").text($(this).text());
		$(this).parents('.' + divId + '_select').css('overflow', 'hidden');
		
		//If this controller drives another box - filter that other box. 
		var idToFilter = $(this).attr("idToFilter");
		var classToDisplay = $(this).attr("classToDisplay");
		if (idToFilter != "undefined" && idToFilter != "" 
				&& classToDisplay != "undefined" && classToDisplay != "") 
		{
			$divSelectTag = $('#' + idToFilter + "_prim");
			// If there is no secondary dropdown for this item, then hide the secondary menu.
			if ($divSelectTag.children("." + classToDisplay).length <= 0) {
				$divSelectTag.parent().css('display', 'none');
			} else {
				//If there IS a secondary dropdown for this item, then show the secondary menu.
				$divSelectTag.parent().css('display', 'block');
			}
			var textToSelect = $divSelectTag.children("." + classToDisplay).children(":first").text();
			var valueToSet = $divSelectTag.children("." + classToDisplay).children(":first").attr("value");
			$divSelectTag.children("li").removeClass('visibleDropdown');
			$divSelectTag.children("li").addClass('hiddenDropdown');
			$divSelectTag.children("." + classToDisplay).removeClass('hiddenDropdown');
			$divSelectTag.children("." + classToDisplay).addClass('visibleDropdown');
			
			//This is the real select box
			$divSelectTag.parent().children(divId + '_select:first').val(valueToSet);
			//This is the fake select box - se the attribute
			$divSelectTag.parent().attr("value", valueToSet);
			//Set the text in the fake box. 
			$divSelectTag.parent().find("span:first").text(textToSelect);
		}
		return false;
	});
	
	$('.' + divId + '_select').bind("mousedown", function(evt) {
		evt.stopPropagation();
		return false;
	});
	
	// When we click a fake select box either expand the options or roll them back up. 
	$('.narrowSearchResultsSelect_select').keydown(function(event){ 
	    var keyCode = (event.keyCode ? event.keyCode : event.which);   
	    if (keyCode == 13) {
	       $('.narrowSearchResultsSelect_select').trigger('click');
	    }
	});
	
	$('div#otherResultsSelectDiv').keydown(function(event){ 
		 var keyCode = (event.keyCode ? event.keyCode : event.which);   
		if (keyCode == 13) {
				$('div#otherResultsSelectDiv').blur();
				$('select#otherResultsSelect').focus();
		      $('div.otherResultsSelect_select').trigger('click');
		   }
	});	
	
	$('div#bestResultsSelectDiv').keydown(function(event){ 
		 var keyCode = (event.keyCode ? event.keyCode : event.which);   
		if (keyCode == 13) {
				$('div#bestResultsSelectDiv').blur();
				$('select#bestResultsSelect').focus();
		      $('div.bestResultsSelect_select').trigger('click');
		   }
	});	
	
	$('.' + divId + '_select').bind("click", function(evt) {
		evt.stopPropagation();
		var $ul = $(this).find('ul');
		if($(this).find("ul:hidden").length) {
			$(this).css("overflow", "visible");
			$('.' + divId + '_select').removeClass('CurrentSelectBox').find('ul').hide();
			$ul.slideDown('fast');
			$ul.parent('.' + divId + '_select').addClass('CurrentSelectBox');
			$('.' + divId + '_select span').css("position", "absolute");
		}
		else {
			$(this).css("overflow", "hidden");
			$('.' + divId + '_select').removeClass('CurrentSelectBox').find('ul').hide();
		}
		
		$('body').bind("mousedown", function() {
			$('.' + divId + '_select').removeClass('CurrentSelectBox').find('ul').hide();
			$("body:not(li)").unbind("mousedown");
			$('.' + divId + '_select').css("overflow", "hidden");
		});
		
	});
}

// Sets the width for dropdown options. 
function setDropdownWidth( $ul ) {

	var origUlWidth = $ul.css("width").slice(0, $ul.css("width").length - 2 ) - 0;
	
	// measure each option, if greater than the UL width then set UL width to it
	$ul.css( "width", "auto" );
	var newUlWidth = origUlWidth;
	var LIs = $ul.find("li");
	$ul.show();
	for(var n=0; n<LIs.length; n++) {
	    var liWidth = $(LIs[n]).width();
	    if( newUlWidth < liWidth )
	        newUlWidth = liWidth;
	}
	$ul.hide();

    $ul.css( "width", newUlWidth + "px" );
}

// This method will display the $divToPopup element in a popup box. If the browser can handle fixed 
// positioning then the popup box will be displayed in the center of the browser window using fixed positioning. 
// Othewise it will display using absolute positioning. 
function displayInModalPopupBox($divToPopup) {

	//Get the screen height and width  
	var maskHeight = $(window).height();  
	var maskWidth = $(window).width(); 
	$mask = $('#mask');
	
	$modalWindow = wrapElementWithTransparentBorder($divToPopup);
	
	//If the div is hidden the hide the modal window and show the hidden div. 
	// The effect is that the div still stays hidden but it will show when the modal box shows. 
	if ($divToPopup.css('display') == 'none') {
		$modalWindow.hide();
		$divToPopup.show();
	}
	// Add the modal Popup class to the modal window. 
	$modalWindow.addClass('ModalPopupBox');
	// Append the modal window to the body element. This helps us to get around z-ordering issues. 
	$modalWindow.appendTo('body');
	// Now we start positioning. Our CSS should set the positioning as 'Fixed'. IE6 does not handle fixed. 
	// In IE6 the position will be set to absolute. That's OK since we're attached to the 'body' element. 
	// The modal window will not scroll with us, but it will be about where it should be for most cases.
	
	$modalWindow.css('top',  (maskHeight-$modalWindow.height()) / 2);
	$modalWindow.css('left', (maskWidth-$modalWindow.width()) / 2);
	// Hide the window. If anyone wants to display this, then they can call the 'show' method. 
	$modalWindow.hide();
	return $modalWindow;
}

// This method will display a waiting box. It accepts a single parameter that is the element that 
//it will display over. The style of this box is defined in Base.css The class name is
//BusyIndicatorBoxBorder (for the border) and BusyIndicatorBox (for the box.).
// It returns the modal popup box. 
function showBusyModalPopupBox($divToDisplayIn) {
	/*-- START CHANGES P23695 Medicare Spanish Translation - n596307 --*/
	var loadingText;
	if(site_id == 'medicare' && langPref == 'sp'){
		loadingText = "Cargando... Espere."
	}
	else{
		loadingText = "Loading... please wait."
	}
	/*-- END CHANGES P23695 Medicare Spanish Translation - n596307 --*/
	$busyBox = $divToDisplayIn.append('<div class="BusyIndicatorBox"><label>'+loadingText+'</label></div>');
	$busyBox = $divToDisplayIn.children('.BusyIndicatorBox');
	$busyBoxWrapper = wrapElementWithTransparentBorder($busyBox);
	$busyBoxWrapper.attr('id', 'BusyIndicator');
	return $busyBoxWrapper;
}

function showAndPlaceBusyModalPopupBox($divToDisplayIn, top, left) {
	var $positionedBusyBoxWrapper = showBusyModalPopupBox($divToDisplayIn);
	$positionedBusyBoxWrapper.css("top", top + "px");
	$positionedBusyBoxWrapper.css("left", left + "px");	
	$positionedBusyBoxWrapper.css("z-index","1000");
	return $positionedBusyBoxWrapper;
}

// This method wraps a div in a transparent border. 
// It returns the parent element that wraps the border and the original element. 
function wrapElementWithTransparentBorder($divElementThatNeedsBorder){
	$borderBox = $divElementThatNeedsBorder.wrap('<div class="TransparentBorderBox"></div>').parent();
	$border = $borderBox.prepend('<div class="TransparentBorder">&nbsp;</div>').children('.TransparentBorder');
	$border.width($divElementThatNeedsBorder.width() + 30);
	$border.height($divElementThatNeedsBorder.height() + 30);
	$divElementThatNeedsBorder.css('margin', '15px');
	$divElementThatNeedsBorder.css('position', 'absolute');
	$divElementThatNeedsBorder.css('top', '0px');
	$divElementThatNeedsBorder.css('left', '0px');
	$divElementThatNeedsBorder.css('z-index', $border.css('z-index') + 1);
	return $borderBox;
}