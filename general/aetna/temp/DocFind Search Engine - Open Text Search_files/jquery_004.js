/**
 * Custom jQuery dialog plugin to display the dialog box on a page.
 */

jQuery.fn.doDialog = function(options, buttons){
	//base z-index;
	var z = 10000;
	
	var $this = $(this);
	$this.addClass('dialog-content');
	var $wrap = $this.wrap("<div class='dialog-content-wrap'></div>").parent();
	var $main_wrapper = $wrap.wrap("<div class='dialog-main-wrapper'></div>").parent();
	var $trans = $main_wrapper.prepend('<div class="dialog-transparent-border"></div>').children('.dialog-transparent-border');
	
	
	var $subtitle = $wrap.prepend("<div class='dialog-subtitle'>"+$this.attr('subtitle')+"</div>").children('.dialog-subtitle');
	var $title = $subtitle.prepend("<div id='diaTitle' class='dialog-title'>"+$this.attr('title')+"</div>").children('.dialog-title');
	
	//var $title = $wrap.prepend("<div class='dialog-title'>"+$this.attr('title')+"</div>").children('.dialog-title');
	

	var $close_button = $main_wrapper.prepend('<div class="dialog-close-button">&nbsp;</div>').children('.dialog-close-button');
	//var $dialogText = $close_button.prepend("<div class='dialog-dialogText'>"+$this.attr('dialogText')+"</div>").children('.dialog-dialogText');
	
	$wrap.append("<div class='dialog-dialogText'>"+$this.attr('dialogText')+"</div>");

	$wrap.append("<div class='dialog-button-holder'><table><tr></tr></table></div>");

	var $buttonHolder = $('.dialog-button-holder table tr', $wrap);
	
	var calculated_width = 0;
	var calculated_height = 0;
	var button;

	for(var i=0; i < buttons.length; i++){
		button = buttons[i];
		$button = createButton(button.id,button.value, button.url, button.onClick, button.arrow);
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
		var $modal = $("<div id='dialog_modal_id' class='dialog-modal'></div>");
		$main_wrapper.parent().append($modal);
		$modal.css('position','absolute');
		$modal.css('z-index',z-1);
		$modal.css('background-color','#000000');
		$modal.width($(document).width());
		$modal.height($(document).height());
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
		//goNavHome();				
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
			
			$('#dialog_modal_id').bgiframe();
			$("html").css("overflow", "hidden"); 
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
/* Changes for Types of services*/
jQuery.fn.doDialogflag = function(options, buttons){
	//base z-index;
	var z = 10000;
	
	var $this = $(this);
	$this.addClass('dialog-content');
	var $wrap = $this.wrap("<div class='dialog-content-wrap'></div>").parent();
	var $main_wrapper = $wrap.wrap("<div class='dialog-main-wrapper'></div>").parent();
	var $trans = $main_wrapper.prepend('<div class="dialog-transparent-border"></div>').children('.dialog-transparent-border');
	
	
	var $subtitle = $wrap.prepend("<div class='dialog-subtitle'>"+$this.attr('subtitle')+"</div>").children('.dialog-subtitle');
	var $title = $subtitle.prepend("<div id='diaTitle' class='dialog-title'>"+$this.attr('title')+"</div>").children('.dialog-title');
	
	//var $title = $wrap.prepend("<div class='dialog-title'>"+$this.attr('title')+"</div>").children('.dialog-title');
	

	var $close_button = $main_wrapper.prepend('<div class="dialog-close-button">&nbsp;</div>').children('.dialog-close-button');
	//var $dialogText = $close_button.prepend("<div class='dialog-dialogText'>"+$this.attr('dialogText')+"</div>").children('.dialog-dialogText');
	
	$wrap.append("<div class='dialog-dialogText'>"+$this.attr('dialogText')+"</div>");

	$wrap.append("<div class='dialog-button-holder'><table><tr></tr></table></div>");

	var $buttonHolder = $('.dialog-button-holder table tr', $wrap);
	
	var calculated_width = 0;
	var calculated_height = 0;
	var button;

	for(var i=0; i < buttons.length; i++){
		button = buttons[i];
		$button = createButtonflag(button.id,button.value, button.url, button.onClick, button.arrow);
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
		var $modal = $("<div id='dialog_modal_id' class='dialog-modal'></div>");
		$main_wrapper.parent().append($modal);
		$modal.css('position','absolute');
		$modal.css('z-index',z-1);
		$modal.css('background-color','#000000');
		$modal.width($(document).width());
		$modal.height($(document).height());
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
		//goNavHome();				
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
			
			$('#dialog_modal_id').bgiframe();
			$("html").css("overflow", "hidden"); 
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
function createButtonflag(id, name, url, onClick, arrow){
	if(arrow){
		right_class = "gold_button_right";
	}else{
		right_class = "gold_button_right";
	}
	var tdButtonClass="gold_button_left";
	if (name == 'CANCEL'){
		tdButtonClass="cancelGoldButton_rd";
	}
	if (name == 'CONTINUE'){
		tdButtonClass="continueGoldButton_rd";
	}
      /*P08-8423a Sprint08-2013 - Story10133 Changes Start*/ 
	if (name == 'CLOSE'){
		tdButtonClass="closebutton_rd";
	}
	/*P08-8423a Sprint08-2013 - Story10133 Changes End*/	
	var $button = $('<td class="dialog-button-cell"><a id="'+ id +'" class="GoldButtonLink" onclick="'+onClick+'" href="' + url + '" ></a></td>');
	
	$button_link = $('a' , $button);
	
		$button_link.prepend('<table cellpadding="0" cellspacing="0" style="position: relative; left: 2px">' + 
				'<tr>'+
				'<td class='+tdButtonClass+'>&nbsp;</td>'+
			'</tr>'+
		'</table>');
	
	return $button;
}
/* Changes for Types of services end*/
function createButton(id, name, url, onClick, arrow){
	if(arrow){
		right_class = "gold_button_right";
	}else{
		right_class = "gold_button_right";
	}
	var tdButtonClass="gold_button_left";
	if (name == 'CANCEL'){
		tdButtonClass="cancelGoldButton_rd";
	}
	if (name == 'CONTINUE'){
		tdButtonClass="continueGoldButton_rd";
	}
      /*P08-8423a Sprint08-2013 - Story10133 Changes Start*/ 
	if (name == 'CLOSE'){
		tdButtonClass="closebutton_rd";
	}
	/*P08-8423a Sprint08-2013 - Story10133 Changes End*/	
	var $button = $('<td class="dialog-button-cell"><a id="'+ id +'" class="GoldButtonLink" onclick="'+onClick+'" href="' + url + '" ></a></td>');
	
	$button_link = $('a' , $button);
	
		$button_link.prepend('<table cellpadding="0" cellspacing="0" style="position: relative; left: 2px">' + 
				'<tr>'+
				'<td class='+tdButtonClass+'>&nbsp;</td>'+
			'</tr>'+
		'</table>');
	
	return $button;
}function goNavHome(){	history.back();	return false;}