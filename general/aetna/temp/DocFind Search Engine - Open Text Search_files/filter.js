var totalTime = 0;
var startTime = 0;
var urlProtocolSecure = "https:";
var urlProtocolNonSecure = "http:";

function startTimer() {
	startTime = new Date().getTime();
}
function endTimer() {
	var endTime = new Date().getTime();
	totalTime += endTime - startTime;
}
function displayTimer() {
	alert(totalTime / 1000);
}

/*
 * Helper method to get a piece of HTML.  If none is found, return blank string.
 * Keeps things from blowing up if data is missing
 */
function getHtml(target,defaultValue) {
	if (!defaultValue) defaultValue = '';
	if (!target) return defaultValue;
	if (target.size() == 0) return defaultValue;
	return $.trim(target.html());
}

/* Function to add filter data returned from the search engine to the filter menu.
 * - for every filter value in the menu, find the corresponding value in the data
 * - add the count, the active flag, and the action from the data to the menu
 * - delete any menu filter items are filter values that are not in the data
 */
function addFilterValues() {
	totalTime = 0;
	/*-- START CHANGES P20751b ACO Branding - n596307 --*/
	var switchURL ;
	if($('#suppressAexcelPlanFromFilterDiv').html() != null && $('#suppressAexcelPlanFromFilterDiv').html() == 'true'){
		/*-- START CHANGES P23695 Medicare Spanish Translation - n709197 --*/
		if(site_id == 'medicare' && langPref == 'sp'){
			switchURL = "/dse/cms/codeAssets/html/es/filter_menu_JSON_SuppressAexcel.html";
		}
		else{
			switchURL = "/dse/cms/codeAssets/html/filter_menu_JSON_SuppressAexcel.html";
		}
	}
	else{
		if(site_id == 'medicare' && langPref == 'sp'){
			switchURL = "/dse/cms/codeAssets/html/es/filter_menu_JSON.html";
		}
		else if(site_id == 'banneraetna' && langPref == 'en'){
			switchURL = "/dse/cms/codeAssets/html/filter_menu_JSON_JV.html";
			}
		else if(site_id == 'hartfordhealthcare' && langPref == 'en'){
			switchURL = "/dse/cms/codeAssets/html/filter_menu_JSON_hartfordhealthcare.html";
			}
		else if(site_id == 'hermanmiller' && langPref == 'en'){
			switchURL = "/dse/cms/codeAssets/html/filter_menu_JSON_hermanmiller.html";
			}
		else{
			switchURL = "/dse/cms/codeAssets/html/filter_menu_JSON.html";
		}
		/*-- END CHANGES P23695 Medicare Spanish Translation - n709197 --*/
	}
	/*-- END CHANGES P20751b ACO Branding - n596307 --*/
	// get the static menu data
	var menuJson = $.ajax({
		url: switchURL,		async: false
	}).responseText;
	var menuData = $.parseJSON(menuJson);
	
	// get data from the search engine
	var engineJson = $('#filter-json').html();
	var engineData = $.parseJSON(engineJson);
	
	// add search engine data to the menu
	var selectedValues = $("#filterValues").val();
	updateMenu(menuData,engineData,selectedValues);

	menuHtml = $('#filter-menu');

	// load the filter menu HTML onto the page.  When it is loaded, process it.
	var fixedActiveFilter = false;  // if a filter with a fix parm has active values
	
	/*-- START CHANGES P23695 Medicare Spanish Translation - n709197 --*/
	var filterHTMLPath;
	if(site_id == 'medicare' && langPref == 'sp'){
		filterHTMLPath = '/dse/cms/codeAssets/html/es/filter_menu.html .filter-top-level';
	}
	
	else if(site_id == 'shc'){
		filterHTMLPath = '/dse/cms/codeAssets/html/filter_menu_shc.html .filter-top-level';
	}
	else{
		filterHTMLPath = '/dse/cms/codeAssets/html/filter_menu.html .filter-top-level';
	}
	menuHtml.load(filterHTMLPath, function() {
		/*-- END CHANGES P23695 Medicare Spanish Translation - n709197 --*/
		// update the menu HTML with the menu data
		addMenuValues(menuHtml, menuData);
		
		// for any menu items that have to be fixed (the counts are wrong), make sure
		// that there are actually filter values of that fix type.  If not, then when
		// the menu is fixed, all counts will be zero and it cannot be used.
		menuHtml.find('div.filter-fix-parm').each(function(index) {
			var filter = $(this).parents('.filter-item');  // filter needing fixing
			var fixParm = $(this).html();
			
			// the fix parm is of the form navigator=value
			// to look up this value in the filter data, we need it in the form
			// navigator.value
			fixParm = fixParm.replace("=",".");
			var k = lookup[fixParm];
			
			// if no values returned by search engine for this type of fix, delete the
			// filter menu in the HTML
			if (!k) {
				var htmlLocation = filter.find('ul.filter-sub-level');
				htmlLocation.html('');
			}

		}); // fix filters
		
		// handle any active menu items
		menuHtml.find('li.filter-selected').each(function(index) {
			makeMenuItemActive($(this));
			var filter = $(this).parents('.filter-item');
			
			/* Filter Ui Design Changes  Start */
			filter.find('.filter-check-default').attr('checked','true');
			if($(this).parents('#ProviderTypeFilter').size() > 0 && $('#filterOpenImg').is(':visible')){
				$('#provTypeFilContent').show();
				$('#filterOpenImg').hide();
				$('#filterCloseImg').show();
				/* Filter Ui Design Changes  Start */
				/* $('.providerTypeFilterTableDisplayName').css("margin-left","-12px"); */
				/* $('#provtypePleatLabel').css("color","#ffffff"); */
				/* Filter Ui Design Changes  End */
			}
			/* Filter Ui Design Changes  End */
			
			// if this filter is a filter that needs fixing, remove any other filters that
			// need fixing so the user cannot select values from them.  
			// Only one fixed filter can be active at a time.
			if (filter.find('.filter-fix-parm').size() > 0) {
				// remove the fix parameter from this filter so we can find and remove
				// all other fix filters
				filter.find('.filter-fix-parm').removeClass('filter-fix-parm').addClass('filter-fix-parm-temp');
				menuHtml.find('div.filter-fix-parm').closest('li.filter-item').remove();

				// put back the fix parm for this filter
				filter.find('.filter-fix-parm-temp').removeClass('filter-fix-parm-temp').addClass('filter-fix-parm');
			}
		}); // active values

		// remove any menu values that don't have a count div.
		menuHtml.find('li.filter-value').not(menuHtml.find('div.filter-count').parent()).remove();
		
		// remove any menu items that don't have any values below them.  Nothing to choose
		menuHtml.find('li.filter-item').not(menuHtml.find('li.filter-value').closest('li.filter-item')).remove();
		
		// all link tags in the menu will be processed by the filter_click function.
		// and we will add a void link so the browser doesn't load anything when clicked
		menuHtml.find('a').attr('href','javaScript:void(0);');
		menuHtml.find('input,a').click(filter_click);
		//menuHtml.click(filter_click);
		// put the cached menu on the page
		//P8423a Sprint23 - Story9282 Changes Start
		menuHtml.find('ul.filter-sub-level').each(function(index){
			$(this).hide();
		});
		//P8423a Sprint23 - Story9282 Changes End
	});
}

/*
 * Make a menu value active (show as already selected)
 */
 /* Filter Ui Design Changes  Start */
function makeMenuItemActive(filterMenuValue) {
		var filterMenuDisplayable = filterMenuValue.find('div.filter-display').html();	
		var filterMenuItem = filterMenuValue.closest('li.filter-item');
		/* Filter Ui Design Changes  Start */
		/* Make Name Link Working for Filters Start */
		var html = "<div style='padding-top: 5px; padding-left:23px;'>" +
				   "<input class='filter-active-value' type='checkbox' checked='checked'/>"+
		           //"< class='filter-active-value' style='float:left;padding-top:10px;'>" +		          
		           //"</a>" +
		           //"<span style='padding-left: 5px;'>" +
		           "<a class='filter-active-value'>"+filterMenuDisplayable+"</a>"+
		           //"</span>" +
		           "<div class='filter-match'>" +
		           filterMenuValue.find('div.filter-match').html() +
		           "</div>" +
		           "</div>";
		/* Make Name Link Working for Filters Start */
		/* Filter Ui Design Changes  End */
		filterMenuItem.find('div.filter-active-values').append(html);
			
		// since this filter is active, we don't want the user to ever
		// open up the sub-menu of values.
		filterMenuItem.find('ul.filter-sub-level').hide();
			
		// on the filter menu item, show all the active values added
		// and the ability to clear the filter
		filterMenuItem.find('div.filter-active-values').show();
		//filterMenuItem.find('div.filter-edit').show();
		$('#clearAllLink').show();
}
 /* Filter Ui Design Changes  End */
/*
 * Function to process a click on a filter menu item
 * A menu item has a class that describes what happens when the item is clicked
 * - filter-select-nothing:
 *   When the menu item is selected, nothing happens.  This is appropriate when this is
 *   just a menu item that opens a sub-menu.  In this case, the user must click
 *   an item in the sub-menu.
 * - filter-select-toggle:
 *   When the menu item is selected, the item toggles between filter-selected and
 *   filter-unselected.
 * - filter-select-search:
 *   When the menu is selected, a new search is done with the selected filter item.
 *   This is appropriate for filters where only one item in the menu can be selected,
 *   and the items are mutually exclusive (like Male, Female)
 * - filter-clear:
 *   This is the clear menu item for a menu of filter-select-search items.
 *   For this menu item to be present, there must be an active filter value in the
 *   menu.  To clear that filter from the search, we just search again on that active
 *   filter item, because it will remove it.  The search engine provides the filter action
 *   to remove an item when that item is active.
 */
 /* Filter Ui Design Changes  Start*/
function filter_click(e) {
	/* Filter Ui Design Changes  Start*/
	/* Make Name Link Working for Filters Start */
	if (e.target.nodeName !== 'INPUT' && e.target.nodeName !== 'A') {
	/* Filter Ui Design Changes  End*/
		return;  // ignore this click
	}
	/* Make Name Link Working for Filters End */
	var target = $(e.target);  // make it a jquery object
	 
	// get the type of menu that got clicked
	var currentClass = target.attr('class');
	var menuType = target.parents('.filter-item').find('.filter-menu-type').html();
	var menuName = target.parents('.filter-item').find('.filter-name').html();
	var selectedValues = $("#filterValues").val();
	
	/* Make Name Link Working for Filters Start */
	if(currentClass == 'filter-name-show' && target.parents('.filter-item').children('.filter-active-values').css('display') === 'none' && (!(target.parents('.filter-item').find('.filter-check-default').is(':checked')))){
		$(e.target).parents('.filter-item').find('.filter-check-default').attr('checked','true');
	}
	
	if(currentClass == 'filter-name-show' && target.parents('.filter-item').children('.filter-active-values').css('display') === 'block' && (target.parents('.filter-item').find('.filter-check-default').is(':checked'))){
		$(e.target).parents('.filter-item').find('.filter-check-default').prop('checked', false);
	}
	
	/* Make Name Link Working for Filters End */
	
	/* Filter Ui Design Changes  Start*/
	/* Make Name Link Working for Filters Start */
	if((target.attr('type') == 'checkbox' && (!(target.is(':checked'))) && target.attr('class')== 'filter-check-default') ||(e.target.nodeName == 'A' && target.attr('class')== 'filter-name-show' && (!target.parents('.filter-item').find('.filter-check-default').is(':checked')))){
		if(target.parents('.filter-item').children('.filter-active-values').css('display') === 'block'){
			currentClass='filter-clear';
		}
		else{
			menuType='';
		}
	}
	/* Make Name Link Working for Filters End */
	/* Filter Ui Design Changes  End*/
	
	// first we process a specific class that was clicked on
	switch (currentClass) {
		case 'filter-clear':
			// we deselect all of the values in this menu and search again
			target.parents('.filter-item').find('.filter-selected').each(function(index) {
				var parentId = $(this).children('.filter-nav').text();
				var data = $(this).children('.filter-match').text();
				var dataset = menuName+':'+parentId+':'+data;
				var present = false;
				$.each(vals,function(index){
					 if (this == dataset) {
						 present = true;
					}		 
				 });
				if(present){
					vals.remove(dataset);
				}
				
				// we unselect this filter value if it is an any other filter
				target.parents('.filter-top-level').find('.filter-selected').each(function(index) {
					var parentId = '';
					if(data == $(this).children('.filter-match').text()){
						$(this).removeClass('filter-selected').addClass('filter-unselected');
					}
				});
				
			});
			filter_search();
			return;

		case 'filter-active-value':
			// selected a value being filtered on - stop filtering on that value
			var match = target.parent().find('.filter-match').html();
			
			// find anywhere the menu value has this value and deselect it
			target.parents('.filter-top-level').find('.filter-selected').each(function(index) {
				var parentId = '';
				if(match == $(this).children('.filter-match').text()){
					parentId = $(this).children('.filter-nav').text();
					vals.remove(menuName+':'+parentId+':'+match);
					$(this).removeClass('filter-selected').addClass('filter-unselected');
				}
			});
			
			filter_search();
			return;
	}
	
	// then we process the general menu type if no specific class processed
	var filterName = target.parents('.filter-item').find('.filter-name').html();
	var active = target.parents('.filter-item').find('.filter-active-values').html();
	
	if ($(active).find("div").length != 0){  // filter already selected
		return;  // don't reprocess it
	}

	switch (menuType) {
		case 'click-search':  
			// we mark this filter value as being selected
			// and do an immediate search
//			target.parents('.filter-value').addClass('filter-selected');
			//P8423a Sprint23 - Story9282 Changes Start
			target.parents('.filter-item').find('.filter-name').addClass('filter-selected');
			if (target.parents('.filter-item').find('a').attr('id') == "prov_type")
				{
				target.parents('.filter-item').find('a').css("color","#b7b7b7");
				}
			
			buildPopUp(filterName);
			$('input[type=checkbox]').each(function(){ 
		    	checkIdToClear = $(this).closest('li').attr('id');  
		    	if(checkIdToClear == filterName){
		    		this.checked = false;
		    	}
			});
			return;
			//P8423a Sprint23 - Story9282 Changes End		

		case 'click-fix':  
			var fixParm = getHtml(target.parents('.filter-item').find('.filter-fix-parm'));
			/*-- START CHANGES P20751b ACO Branding - n596307 --*/
			var switchURL ;
			if($('#suppressAexcelPlanFromFilterDiv').html() != null && $('#suppressAexcelPlanFromFilterDiv').html() == 'true'){
				/*-- START CHANGES P23695 Medicare Spanish Translation - n709197 --*/
				if(site_id == 'medicare' && langPref == 'sp'){
					switchURL = "/dse/cms/codeAssets/html/es/filter_menu_JSON_SuppressAexcel.html";
				}
				else{
					switchURL = "/dse/cms/codeAssets/html/filter_menu_JSON_SuppressAexcel.html";
				}
			}
			else{
				if(site_id == 'medicare' && langPref == 'sp'){
				switchURL = "/dse/cms/codeAssets/html/es/filter_menu_JSON.html";
				}
			else{
			switchURL = "/dse/cms/codeAssets/html/filter_menu_JSON.html";
				}
				/*-- END CHANGES P23695 Medicare Spanish Translation - n709197 --*/
			}
			/*-- END CHANGES P20751b ACO Branding - n596307 --*/
			// get the static menu data
			var menuJson = $.ajax({
				url: switchURL,		async: false
			}).responseText;
			var menuData = $.parseJSON(menuJson);

			menuHtml = $('#filter-menu');

			// we do a search to fix all filter values under this filter.  To do this, we
			// take the original search engine URL and add on the fix parameter.
			var fixURL = searchURL + '&' + fixParm;
			var ajaxData = {};
			ajaxData.searchOverrideURL = fixURL;
			ajaxData.searchQuery = '';  // need something for search to work
			$.ajax({
		    	beforeSend:function(){
					loadSpinner()
				},
		        type: "GET",
		        data: ajaxData,
		        url: "search/results",
		        success: function(response)
		        {
					hideSpinner();

					// get data from the search engine and overlay existing
					engineJson = $(response).filter('#filter-json').text();
					engineData = $.parseJSON(engineJson);
					
					// fix menu data from new search engine data
					updateMenu(menuData,engineData,selectedValues,filterName);
					
					// fix the menu HTML with the fixed menu data
					addMenuValues(menuHtml, menuData, filterName);

					buildPopUp(filterName);
					$('input[type=checkbox]').each(function(){ 
				    	checkIdToClear = $(this).closest('li').attr('id');  
				    	if(checkIdToClear == filterName){
				    		this.checked = false;
				    	}
					});
		        }
		    });
			
			// we mark this filter value as being selected
//			target.parents('.filter-value').addClass('filter-selected');
			//P8423a Sprint23 - Story9282 Changes Start
			target.parents('.filter-item').find('.filter-name').addClass('filter-selected');
			if (target.parents('.filter-item').find('a').attr('id') == "prov_type")
				{
				target.parents('.filter-item').find('a').css("color","#b7b7b7");
				}
			
			return;
			//P8423a Sprint23 - Story9282 Changes End		
	
	}
}
 /* Filter Ui Design Changes  End*/

/*
 * Function to do the search, filtering on all values selected in the filter menu
 */

function filter_search() {
	var filterValues = "";  // all filter name/value pairs to be passed to search engine
	var extraValue = null;  // set for filters that require additional filter value

	// loop through each selected value
	$('#filter-menu li.filter-value.filter-selected').each(function(index) {
		if (index > 0) {
			filterValues += '|';  // separator
		}
		
		var filterName = $(this).parents('.filter-item').find('.filter-name').html();
		var fieldNav = $(this).find('.filter-nav').html();
		var filterValue = $(this).find('.filter-match').html();
		filterValues += filterName + ':' + fieldNav + ':' + filterValue;
		
		var fixParm = getHtml($(this).parents('.filter-item').find('.filter-fix-parm'));
		if (fixParm.length > 0) {
			extraValue = '|' + filterName + ':' + fixParm.replace("=",":");
		}
	});
	//P8423a Sprint23 - Story9282 Changes Start	
	
	if (extraValue) {
		filterValues += extraValue;
	}
	
	filterValues = tweakFilterValues(filterValues);
	clickedFilter(filterValues);
}

function buildFilterModalBox(data,filterRealName,filterDisplayName,filterDialogTab1Label,filterDialogTab2Label,shortList){
	/*Start changes for sprint 25 story 9196 */
	$('#filterDialog.dialog-content').parents('div.dialog-main-wrapper').children('div.dialog-content-wrap').children('div.dialog-title').text(filterDisplayName).css({ 'font-weight': 'bold', "color": "#7d3f98", 'font-size': '18pt' });
	 /*End changes for sprint 25 story 9196 */
	if(filterDialogTab1Label != null && filterDialogTab1Label != ''){
		var $title=$('#filterDialog.dialog-content').parents('div.dialog-main-wrapper').children('div.dialog-content-wrap').children('div.dialog-title');
		$title.append('<table class="filterDialogTabs"><tr><td id="filterTab1"><a id="filterTabLink1" href="javascript:void(0);">' + filterDialogTab1Label + '</a></td><td id="filterTab2"><a id="filterTabLink2" href="javascript:void(0);">' + filterDialogTab2Label + '</a></td></tr></table>');
	}
	/*-- START CHANGES P23695 Medicare Spanish Translation - n596307 --*/
	var hospSubText;
	if(site_id == 'medicare' && langPref == 'sp'){
		hospSubText = "Consulte las afiliaciones a hospitales correspondientes a su plan mediante la página de información de cada proveedor";
	}
	else{
		hospSubText = "Please verify the hospital affiliations for your plan using the details page for any provider";
	}
	if(filterRealName!=null && filterRealName!= '' && filterRealName!= undefined && filterRealName == 'HospitalAffiliations'){
		var $title=$('#filterDialog.dialog-content').parents('div.dialog-main-wrapper').children('div.dialog-content-wrap').children('div.dialog-title');
		$title.append('<div id ="filterHospitalSubtitleText">'+hospSubText+'</div>');
	}
	/*-- END CHANGES P23695 Medicare Spanish Translation - n596307 --*/
	
	if(shortList == null || shortList == ''){
		$('#filterDialog').html(data);
	}else{
		$('#filterDialog').html(shortList);
	}
	
	adjustFilterModelHeight();
	
	$('#Clear').click(function(){
		clearSelected(filterRealName);
		return false;
	});
	
	$('#Search').bind('click',function(event){
		/* Filter Ui Design Changes  Start */
		var gotResultsorNot=getResults(filterRealName);
		if(gotResultsorNot!=false){
			filterRealName='';
		}
		/* Filter Ui Design Changes  End */
		$('#filterDialog').trigger('hide');
		$('#Search').unbind('click');
		return false;
	});
	
	$('#filterTabLink1').click(function(){
		$('#filterDialog').html(shortList);
		adjustFilterModelHeight();
		$('#filterTabLink1').css("color","gray");
		$('#filterTabLink2').css("color","black");		
		$('#filterTabLink1').css("text-decoration","none");
		$('#filterTabLink2').css("text-decoration","underline");
	});
	
	$('#filterTabLink2').click(function(){
		$('#filterDialog').html(data);
		adjustFilterModelHeight();
		$('#filterTabLink2').css("color","gray");
		$('#filterTabLink1').css("color","black");		
		$('#filterTabLink2').css("text-decoration","none");
		$('#filterTabLink1').css("text-decoration","underline");
	});
	
	/* Filter Ui Design Changes  Start*/
	$('#filterDialog').parents('div.dialog-main-wrapper').children('div.dialog-close-button').click(function(){
		//alert(filterRealName);
		/*$('#'+filterRealName).attr('checked','false');*/
		if(filterRealName!=null && $.trim(filterRealName) != ''){
			$('#'+filterRealName).prop('checked', false);
			filterRealName='';
		}
		/*$('#'+filterRealName).attr('checked','unchecked');*/
		/*$('#'+filterRealName).removeAttr('checked');*/
	});
	
	/*$('.dialog-close-button').click(function(){
		 //closeButtonFilterName=filterRealName;
		 $(this).parents('#container').find('#'+filterRealName).attr('checked','false');
	});*/ 
	/* Filter Ui Design Changes  End*/
	
	$('#filterDialog').trigger('show');
	$('#filterDialog.dialog-content').parents('div.dialog-main-wrapper').children('div.dialog-close-button').css("left","400px");
	$('#filterDialog.dialog-content').parents('div.dialog-main-wrapper').children('div.dialog-close-button').css("top","23px");
	adjustModalLayerDimentions();
}

function adjustFilterModelHeight(){
	if($('#filterDialog.dialog-content > li').length > 14){
        $('#filterDialog').css("height","250px");
        var adjustBorderHeight = $('#filterDialog.dialog-content').parents('div.dialog-main-wrapper').children('div.dialog-content-wrap').height();
        $('#filterDialog.dialog-content').parents('div.dialog-main-wrapper').children('div.dialog-transparent-border').css("height",adjustBorderHeight + 30);
	}else{
        $('#filterDialog').css("height","auto");
        var adjustBorderHeight = $('#filterDialog.dialog-content').parents('div.dialog-main-wrapper').children('div.dialog-content-wrap').height();
        $('#filterDialog.dialog-content').parents('div.dialog-main-wrapper').children('div.dialog-transparent-border').css("height",adjustBorderHeight + 30);
	}
}

function buildPopUp(selectedVal){
        var name=selectedVal;
		var menuHtml = "";
		var shortList ="";
		var longCount = 0;
			
		var filterMenu1 = $('#filter-menu');
		filterMenu1.find('li.filter-item').each(function(index) {
			var filterMenuItem = $(this);
			var filterName = filterMenuItem.find('.filter-name').html();
			if(name == filterName){
				filterMenuItem.find('li.filter-value').each(function(index3) {
					var filterMenuValue = $(this);
					var filterMatch = filterMenuValue.find('div.filter-match').html();

					if (filterMenuValue.hasClass("filter-shortlist")) {
						shortList += buildPopUpData(filterMenuValue);
					}
					longCount++;
					menuHtml += buildPopUpData(filterMenuValue);
				});

				var menuTitle = filterMenuItem.find('.filter-title').text();
				
				var shortListTitle = getHtml(filterMenuItem.find('.filter-title-shortlist'));
				var longListTitle = getHtml(filterMenuItem.find('.filter-title-longlist'));
				var minLongCount = getHtml(filterMenuItem.find('.filter-longlist-count'), '0');
				
				if (longCount < minLongCount) {  // long list too short
					shortListTitle = longListTitle = shortList = '';  // get rid of lists
				}
				
				buildFilterModalBox(menuHtml,name,menuTitle,shortListTitle,longListTitle,shortList);
				renderFilterUIForNonSecure();
			}
		});
}

function renderFilterUIForNonSecure(){
	if(urlProtocol == urlProtocolNonSecure){
		$('.dialog-content-wrap').css("background-color","#ffffff");
		$('.dialog-content-wrap').css("border-color","#D1D1D1");
		$('.gold_button_left').html('');
		$('.gold_button_left').css("background-image","none");
		$('.gold_button_right').css("background-image","none");
		$('.gold_button_right').html('');
		//$('.gold_button').css("background-image","url(/dse/assets/images/go_btn_center.jpg)");
		$('.gold_button').css("height","25px");
		$('.gold_button').css("width","70px");
	}
}

function buildPopUpData(filterMenuValue) {
	var filterName = filterMenuValue.parents('.filter-item').find('.filter-name').html();
	var filterMatch = filterMenuValue.find('div.filter-match').html();
	var filterNav = filterMenuValue.find('div.filter-nav').html();
	var filterDisplay = filterMenuValue.find('div.filter-display').html();
	var filterCount = filterMenuValue.find('div.filter-count').html();
	var filterActive = filterMenuValue.hasClass('filter-selected');
	var activeClass = filterActive ? 'filter-selected' : 'filter-unselected';
	
	// wipe out count if this value is going to be tweaked
	var tweak = getHtml($('div.filter-search-tweak'));
	var tweakSearch = filterName + ':' + filterNav + ':' + filterMatch;
	if (tweak.indexOf(tweakSearch) >= 0) {
		// remove the count DIV from the display
		filterDisplay = filterDisplay.substring(0,filterDisplay.toUpperCase().indexOf('<DIV'));
	}

	var html = 
			'<li id='+ filterNav +' class="filter-value ' + activeClass + '">\n' +
			'<input class="case" type="checkbox" value="'+filterMatch+'" onClick="javaScript:valuesSelected();">'+ filterDisplay+
			'<div class="filter-name">' + filterName + '</div>\n' +
			'</li>'		
		;

	return html;
}

var vals = [];
function getResults(popup){
	var filterValues = "";
	var filterName = null;
	var fieldName = popup;
	var parentId = '';
	$('input[type=checkbox]').each(function(){
		/* Filter Ui Design Changes  Start */
		var classOfResultCheckBox = $(this).attr('class');
		if( $(this).is(':checked') && classOfResultCheckBox != 'filter-check-default' && $(this).closest('li').attr('id') != undefined){
		/* Filter Ui Design Changes  End */
			parentId = $(this).closest('li').attr('id');
			filterName = $(this).closest('li').find('.filter-name').html();
			if(($.inArray(filterName+':'+parentId+':'+$(this).val(), vals))== -1 ){
				vals.push(filterName+':'+parentId+':'+$(this).val());
			}
		}
	});
	
	if (!filterName) {  // nothing was checked
		return false;
	}
	
	// find this same filter in the menu HTML
	var filterHtml = menuHtml.find("div.filter-name").filter(function (index) {
	    return $(this).text() == filterName;
	}).parent();

	// if this filter has an extra value that needs to be sent with the search, add it
	var fixParm = getHtml(filterHtml.find('.filter-fix-parm'));
	if (fixParm.length > 0) {
		var extraValue = filterName + ':' + fixParm.replace("=",":");
		vals.push(extraValue);
	}
	
	$.each(vals,function(index){
		 
		 if (index > 0) {
				filterValues += '|';  // separator
			}
		 		 
		 filterValues += this;
	 });
	 
	filterValues = tweakFilterValues(filterValues);
	clickedFilter(filterValues);
}

function clearSelected(idToClear){
	var checkIdToClear = '';
     $('input[type=checkbox]').each(function(){
     		if($(this).attr('class') == 'case'){
    			this.checked = false;
		}	
     });
}

function valuesSelected(e){
	// var target = $(e.target);
	// target.find('.case').attr('checked', e.target.checked);
	 $(this).attr('checked');
} 

function clearAll(){
	var filterValues = "";
	$('input[type=checkbox]').each(function(){ 
   		this.checked = false;
	});
	vals = [];
	clickedFilter(filterValues);
}
	
//P8423a Sprint23 - Story9282 Changes End

// determine if a filter value is active given a filter name, a value, and the string of
// all selected filters
// The selected values string has the format
// filterName1:navigatorName1:value1|filterName2:navigatorName2:value2...
function isActiveValue(filterName, filterValue, selectedValues) {
	// get all filters that were selected
	var selectedFilters = selectedValues.split('|');
	for (var i=0; i<selectedFilters.length; i++) {
		// get value of filter - the third token of the filter
		var selectedFilter = selectedFilters[i].split(':')[0];
		var selectedValue = selectedFilters[i].split(':')[2];
		if (filterName == selectedFilter && filterValue == selectedValue) {
			return true;  // found it
		}
	}
	return false;  // never found it
}

// see if filter value should be skipped - a conditional value
function skipFilterValue(filterVal) {
	var cond = filterVal.cond;
	if (!cond) {  // not a conditional value
		return false;  // always use it
	}

	if (cond == 'public') {
		return urlProtocol == urlProtocolSecure;
	} else if (cond == 'secure') {
		return urlProtocol == urlProtocolNonSecure;
	}
}
/*-- START CHANGES P23695 Medicare Spanish Translation - n709197 --*/
var engineDataVal;

function translateToSpanish(engineDataVal){
	if(engineDataVal == 'Male'){
		engineDataVal = 'Masculino';
	}
	else if(engineDataVal == 'Female'){
		engineDataVal = 'Femenino';
	}
	else if(engineDataVal == 'Afrikaans'){
		engineDataVal = 'Afrikáans';
	}
	else if(engineDataVal == 'Arabic'){
		engineDataVal = 'Árabe';
	}
	else if(engineDataVal == 'French'){
		engineDataVal = 'Francés';
	}
	else if(engineDataVal == 'German'){
		engineDataVal = 'Alemán';
	}
	else if(engineDataVal == 'Malayalam'){
		engineDataVal = 'Malayalam';
	}
	else if(engineDataVal == 'Spanish'){
		engineDataVal = 'Español';
	}
	else if(engineDataVal == 'Tagalog'){
		engineDataVal = 'Tagalo';
	}
	else if(engineDataVal == 'Vietnamese'){
		engineDataVal = 'Vietnamita';
	}
	else if (engineDataVal == 'Achinese') {
		engineDataVal = 'Achenés';
	}
	else if (engineDataVal == 'Acoli') {
		engineDataVal = 'Acoli';
	}
	else if (engineDataVal == 'Adangme') {
		engineDataVal = 'Adangme';
	}
	else if (engineDataVal == 'Afrihili (Artifical Lang)') {
		engineDataVal = 'Afrihili (idioma artificial)';
	}
	else if (engineDataVal == 'Afrikaans') {
		engineDataVal = 'Afrikáans';
	}
	else if (engineDataVal == 'Afroasiatic (Other)') {
		engineDataVal = 'Lenguas afroasiáticas (otras)';
	}
	else if (engineDataVal == 'Akan') {
		engineDataVal = 'Akan';
	}
	else if (engineDataVal == 'Akkadian') {
		engineDataVal = 'Acadio';
	}
	else if (engineDataVal == 'Albanian') {
		engineDataVal = 'Albanés';
	}
	else if (engineDataVal == 'Aleut') {
		engineDataVal = 'Aleutiano';
	}
	else if (engineDataVal == 'Algonquian (Other)') {
		engineDataVal = 'Algonquiano (otro)';
	}
	else if (engineDataVal == 'Altaic (Other)') {
		engineDataVal = 'Altáico (otro)';
	}
	else if (engineDataVal == 'Amharic') {
		engineDataVal = 'Amhárico';
	}
	else if (engineDataVal == 'Apache Languages') {
		engineDataVal = 'Lenguas apaches';
	}
	else if (engineDataVal == 'Arabic') {
		engineDataVal = 'Árabe';
	}
	else if (engineDataVal == 'Aramaic') {
		engineDataVal = 'Arameo';
	}
	else if (engineDataVal == 'Arapahp') {
		engineDataVal = 'Arapaho';
	}
	else if (engineDataVal == 'Arawak') {
		engineDataVal = 'Araucano';
	}
	else if (engineDataVal == 'Armenian') {
		engineDataVal = 'Armenio';
	}
	else if (engineDataVal == 'Artificial (Other)') {
		engineDataVal = 'Artificial (otro)';
	}
	else if (engineDataVal == 'Assamese') {
		engineDataVal = 'Asamés';
	}
	else if (engineDataVal == 'Athapascan (Other)') {
		engineDataVal = 'Atabascano (otro)';
	}
	else if (engineDataVal == 'Austonesian (Other)') {
		engineDataVal = 'Lenguas austronesias (otro)';
	}
	else if (engineDataVal == 'Avestan') {
		engineDataVal = 'Avéstico';
	}
	else if (engineDataVal == 'Awadhi') {
		engineDataVal = 'Awadhi';
	}
	else if (engineDataVal == 'Aymara') {
		engineDataVal = 'Aimara';
	}
	else if (engineDataVal == 'Azerbaijani') {
		engineDataVal = 'Azerí';
	}
	else if (engineDataVal == 'Balinese') {
		engineDataVal = 'Balinés';
	}
	else if (engineDataVal == 'Baltic') {
		engineDataVal = 'Báltico';
	}
	else if (engineDataVal == 'Baluchi') {
		engineDataVal = 'Baluchi';
	}
	else if (engineDataVal == 'Bambara') {
		engineDataVal = 'Bambara';
	}
	else if (engineDataVal == 'Bamileke Languages') {
		engineDataVal = 'Lenguas bamileke';
	}
	else if (engineDataVal == 'Bantu (Other)') {
		engineDataVal = 'Bantú (otro)';
	}
	else if (engineDataVal == 'Basa') {
		engineDataVal = 'Bassa';
	}
	else if (engineDataVal == 'Bashkir') {
		engineDataVal = 'Bashkir';
	}
	else if (engineDataVal == 'Basque') {
		engineDataVal = 'Euskera';
	}
	else if (engineDataVal == 'Batak') {
		engineDataVal = 'Batak';
	}
	else if (engineDataVal == 'Belarusian') {
		engineDataVal = 'Bielorruso';
	}
	else if (engineDataVal == 'Bemba') {
		engineDataVal = 'Bemba';
	}
	else if (engineDataVal == 'Bengali') {
		engineDataVal = 'Bengalí';
	}
	else if (engineDataVal == 'Berber') {
		engineDataVal = 'Bereber';
	}
	else if (engineDataVal == 'Bhopuri') {
		engineDataVal = 'Bopurí';
	}
	else if (engineDataVal == 'Bikol') {
		engineDataVal = 'Bikol';
	}
	else if (engineDataVal == 'Bini') {
		engineDataVal = 'Bini';
	}
	else if (engineDataVal == 'Bislama') {
		engineDataVal = 'Bislama';
	}
	else if (engineDataVal == 'Braj') {
		engineDataVal = 'Braj';
	}
	else if (engineDataVal == 'Breton') {
		engineDataVal = 'Bretón';
	}
	else if (engineDataVal == 'Bugis') {
		engineDataVal = 'Buginés';
	}
	else if (engineDataVal == 'Bulgarian') {
		engineDataVal = 'Búlgaro';
	}
	else if (engineDataVal == 'Burmese') {
		engineDataVal = 'Birmano';
	}
	else if (engineDataVal == 'Caddo') {
		engineDataVal = 'Caddo';
	}
	else if (engineDataVal == 'Cantonese') {
		engineDataVal = 'Cantonés';
	}
	else if (engineDataVal == 'Carib') {
		engineDataVal = 'Caribeño';
	}
	else if (engineDataVal == 'Catalan') {
		engineDataVal = 'Catalán';
	}
	else if (engineDataVal == 'Caucasian') {
		engineDataVal = 'Lenguas caucásicas';
	}
	else if (engineDataVal == 'Cebuano') {
		engineDataVal = 'Cebuano';
	}
	else if (engineDataVal == 'Celtic (Other)') {
		engineDataVal = 'Celta (otro)';
	}
	else if (engineDataVal == 'Central American Indian') {
		engineDataVal = 'Lengua de los indígenas de Centroamérica';
	}
	else if (engineDataVal == 'Chaldean') {
		engineDataVal = 'Caldeo';
	}
	else if (engineDataVal == 'Chamorro') {
		engineDataVal = 'Chamorro';
	}
	else if (engineDataVal == 'Chechen') {
		engineDataVal = 'Checheno';
	}
	else if (engineDataVal == 'Cherokee') {
		engineDataVal = 'Cherokee';
	}
	else if (engineDataVal == 'Cheyenne') {
		engineDataVal = 'Cheyene';
	}
	else if (engineDataVal == 'Chibcha') {
		engineDataVal = 'Chibcha';
	}
	else if (engineDataVal == 'Chinese') {
		engineDataVal = 'Chino';
	}
	else if (engineDataVal == 'Church Slavic') {
		engineDataVal = 'Eslavo eclesiástico';
	}
	else if (engineDataVal == 'Chuvash') {
		engineDataVal = 'Chuvash';
	}
	else if (engineDataVal == 'Coptic') {
		engineDataVal = 'Copto';
	}
	else if (engineDataVal == 'Cornish') {
		engineDataVal = 'Córnico';
	}
	else if (engineDataVal == 'Cree') {
		engineDataVal = 'Cree';
	}
	else if (engineDataVal == 'Creek') {
		engineDataVal = 'Creek';
	}
	else if (engineDataVal == 'Creoles & Pidgins (Oth)') {
		engineDataVal = 'Criollo y pidgin (otro)';
	}
	else if (engineDataVal == 'Creoles and Pidgins (Eng)') {
		engineDataVal = 'Criollo y pidgin (inglés)';
	}
	else if (engineDataVal == 'Creoles and Pidgins (Fre)') {
		engineDataVal = 'Criollo y pidgin (francés)';
	}
	else if (engineDataVal == 'Creoles and Pidgins (Por)') {
		engineDataVal = 'Criollo y pidgin (portugués)';
	}
	else if (engineDataVal == 'Cushitic') {
		engineDataVal = 'Cusita';
	}
	else if (engineDataVal == 'Czech') {
		engineDataVal = 'Checo';
	}
	else if (engineDataVal == 'Dakota') {
		engineDataVal = 'Dakota';
	}
	else if (engineDataVal == 'Danish') {
		engineDataVal = 'Danés';
	}
	else if (engineDataVal == 'Dayak') {
		engineDataVal = 'Dayak';
	}
	else if (engineDataVal == 'Divehi') {
		engineDataVal = 'Divehi';
	}
	else if (engineDataVal == 'Dogri') {
		engineDataVal = 'Dogri';
	}
	else if (engineDataVal == 'Dravidian') {
		engineDataVal = 'Dravídico';
	}
	else if (engineDataVal == 'Duala') {
		engineDataVal = 'Duala';
	}
	else if (engineDataVal == 'Dutch') {
		engineDataVal = 'Holandés';
	}
	else if (engineDataVal == 'Dutch, Middle (1050-1350)') {
		engineDataVal = 'Holandés medio (1050-1350)';
	}
	else if (engineDataVal == 'Dyula') {
		engineDataVal = 'Diula';
	}
	else if (engineDataVal == 'Efik') {
		engineDataVal = 'Efik';
	}
	else if (engineDataVal == 'Egyptian') {
		engineDataVal = 'Egipcio';
	}
	else if (engineDataVal == 'Ekajuk') {
		engineDataVal = 'Ekajuk';
	}
	else if (engineDataVal == 'Elamite') {
		engineDataVal = 'Elamita';
	}
	else if (engineDataVal == 'Eskimo Languages') {
		engineDataVal = 'Lenguas esquimales';
	}
	else if (engineDataVal == 'Esperanto') {
		engineDataVal = 'Esperanto';
	}
	else if (engineDataVal == 'Estonian') {
		engineDataVal = 'Estonio';
	}
	else if (engineDataVal == 'Ethiopic') {
		engineDataVal = 'Etíope';
	}
	else if (engineDataVal == 'Ewe') {
		engineDataVal = 'Ewe';
	}
	else if (engineDataVal == 'Ewondo') {
		engineDataVal = 'Ewondo';
	}
	else if (engineDataVal == 'Fang') {
		engineDataVal = 'Fang';
	}
	else if (engineDataVal == 'Fanti') {
		engineDataVal = 'Fante';
	}
	else if (engineDataVal == 'Faroese') {
		engineDataVal = 'Feroés';
	}
	else if (engineDataVal == 'Farsi') {
		engineDataVal = 'Farsi';
	}
	else if (engineDataVal == 'Fijian') {
		engineDataVal = 'Fiji';
	}
	else if (engineDataVal == 'Finnish') {
		engineDataVal = 'Finlandés';
	}
	else if (engineDataVal == 'Finno-Ugric') {
		engineDataVal = 'Ugrofinés';
	}
	else if (engineDataVal == 'Flemish') {
		engineDataVal = 'Flamenco';
	}
	else if (engineDataVal == 'Fon') {
		engineDataVal = 'Fon';
	}
	else if (engineDataVal == 'French') {
		engineDataVal = 'Francés';
	}
	else if (engineDataVal == 'Friesian') {
		engineDataVal = 'Frisón';
	}
	else if (engineDataVal == 'Fula') {
		engineDataVal = 'Fula';
	}
	else if (engineDataVal == 'Ga') {
		engineDataVal = 'Ga';
	}
	else if (engineDataVal == 'Gaelic (Scots)') {
		engineDataVal = 'Gaélico escocés';
	}
	else if (engineDataVal == 'Gallegan') {
		engineDataVal = 'Gallego';
	}
	else if (engineDataVal == 'Ganda') {
		engineDataVal = 'Luganda';
	}
	else if (engineDataVal == 'Gayo') {
		engineDataVal = 'Gayo';
	}
	else if (engineDataVal == 'Gbaya') {
		engineDataVal = 'Gbaya';
	}
	else if (engineDataVal == 'Georgian') {
		engineDataVal = 'Georgiano';
	}
	else if (engineDataVal == 'German') {
		engineDataVal = 'Alemán';
	}
	else if (engineDataVal == 'Germanic') {
		engineDataVal = 'Germano';
	}
	else if (engineDataVal == 'Gilbertese') {
		engineDataVal = 'Gilbertés';
	}
	else if (engineDataVal == 'Gorontalo') {
		engineDataVal = 'Gorontalo';
	}
	else if (engineDataVal == 'Greek, Modern') {
		engineDataVal = 'Griego moderno';
	}
	else if (engineDataVal == 'Greenlandic') {
		engineDataVal = 'Groenlandés';
	}
	else if (engineDataVal == 'Guarani') {
		engineDataVal = 'Guaraní';
	}
	else if (engineDataVal == 'Gujarati') {
		engineDataVal = 'Guyaratí';
	}
	else if (engineDataVal == 'Haida') {
		engineDataVal = 'Haida';
	}
	else if (engineDataVal == 'Hausa') {
		engineDataVal = 'Hausa';
	}
	else if (engineDataVal == 'Hawaiian') {
		engineDataVal = 'Hawaiano';
	}
	else if (engineDataVal == 'Hebrew') {
		engineDataVal = 'Hebreo';
	}
	else if (engineDataVal == 'Herero') {
		engineDataVal = 'Herero';
	}
	else if (engineDataVal == 'Hiligaynon') {
		engineDataVal = 'Hiligainón';
	}
	else if (engineDataVal == 'Himachali') {
		engineDataVal = 'Himachali';
	}
	else if (engineDataVal == 'Hindi') {
		engineDataVal = 'Hindi';
	}
	else if (engineDataVal == 'Hiri Motu') {
		engineDataVal = 'Hiri motu';
	}
	else if (engineDataVal == 'Hmong') {
		engineDataVal = 'Hmong';
	}
	else if (engineDataVal == 'Hungarian') {
		engineDataVal = 'Húngaro';
	}
	else if (engineDataVal == 'Iban') {
		engineDataVal = 'Ibano';
	}
	else if (engineDataVal == 'Icelandic') {
		engineDataVal = 'Islandés';
	}
	else if (engineDataVal == 'Igbo') {
		engineDataVal = 'Igbo';
	}
	else if (engineDataVal == 'Ijo') {
		engineDataVal = 'Ijo';
	}
	else if (engineDataVal == 'Iloko') {
		engineDataVal = 'Ilocano';
	}
	else if (engineDataVal == 'Indic') {
		engineDataVal = 'Índico';
	}
	else if (engineDataVal == 'Indo-European (Other)') {
		engineDataVal = 'Indoeuropeo (otro)';
	}
	else if (engineDataVal == 'Indonesian') {
		engineDataVal = 'Indonesio';
	}
	else if (engineDataVal == 'Interlingua') {
		engineDataVal = 'Interlingua';
	}
	else if (engineDataVal == 'Inuktitut') {
		engineDataVal = 'Esquimal';
	}
	else if (engineDataVal == 'Inupiak') {
		engineDataVal = 'Inupiak';
	}
	else if (engineDataVal == 'Iranian') {
		engineDataVal = 'Iraní';
	}
	else if (engineDataVal == 'Irish') {
		engineDataVal = 'Irlandés';
	}
	else if (engineDataVal == 'Iroquoian (Other)') {
		engineDataVal = 'Iroqués (otro)';
	}
	else if (engineDataVal == 'Italian') {
		engineDataVal = 'Italiano';
	}
	else if (engineDataVal == 'Japanese') {
		engineDataVal = 'Japonés';
	}
	else if (engineDataVal == 'Javanese') {
		engineDataVal = 'Javanés';
	}
	else if (engineDataVal == 'Judeo-Arabic') {
		engineDataVal = 'Judeo-árabe';
	}
	else if (engineDataVal == 'Judeo-Persian') {
		engineDataVal = 'Judeo-persa';
	}
	else if (engineDataVal == 'Kabyle') {
		engineDataVal = 'Cabilio';
	}
	else if (engineDataVal == 'Kachin') {
		engineDataVal = 'Kachin';
	}
	else if (engineDataVal == 'Kamba') {
		engineDataVal = 'Kamba';
	}
	else if (engineDataVal == 'Kannada') {
		engineDataVal = 'Canarés';
	}
	else if (engineDataVal == 'Kanuri') {
		engineDataVal = 'Canurí';
	}
	else if (engineDataVal == 'Karen') {
		engineDataVal = 'Careno';
	}
	else if (engineDataVal == 'Kashmiri') {
		engineDataVal = 'Cachemir';
	}
	else if (engineDataVal == 'Kazakh') {
		engineDataVal = 'Kazako';
	}
	else if (engineDataVal == 'Khasi') {
		engineDataVal = 'Khasi';
	}
	else if (engineDataVal == 'Khmer') {
		engineDataVal = 'Jemer';
	}
	else if (engineDataVal == 'Khoisan (Other)') {
		engineDataVal = 'Khoisan (otro)';
	}
	else if (engineDataVal == 'Khotanese') {
		engineDataVal = 'Cotanés';
	}
	else if (engineDataVal == 'Kikuyu') {
		engineDataVal = 'Kikuyu';
	}
	else if (engineDataVal == 'Kimbundu') {
		engineDataVal = 'Kimbundu';
	}
	else if (engineDataVal == 'Kinyarwanda') {
		engineDataVal = 'Kinyarwanda';
	}
	else if (engineDataVal == 'Kongo') {
		engineDataVal = 'Congoleño';
	}
	else if (engineDataVal == 'Konkani') {
		engineDataVal = 'Konkaní';
	}
	else if (engineDataVal == 'Korean') {
		engineDataVal = 'Coreano';
	}
	else if (engineDataVal == 'Kpelle') {
		engineDataVal = 'Kpelle';
	}
	else if (engineDataVal == 'Kuanyama') {
		engineDataVal = 'Kuanyama';
	}
	else if (engineDataVal == 'Kurdish') {
		engineDataVal = 'Kurdo';
	}
	else if (engineDataVal == 'Kutenai') {
		engineDataVal = 'Kutenai';
	}
	else if (engineDataVal == 'Ladino') {
		engineDataVal = 'Ladino';
	}
	else if (engineDataVal == 'Lahnd') {
		engineDataVal = 'Lahnda';
	}
	else if (engineDataVal == 'Langue d oc') {
		engineDataVal = 'Occitano';
	}
	else if (engineDataVal == 'Lao') {
		engineDataVal = 'Laosiano';
	}
	else if (engineDataVal == 'Lapp') {
		engineDataVal = 'Lapón';
	}
	else if (engineDataVal == 'Latin') {
		engineDataVal = 'Latín';
	}
	else if (engineDataVal == 'Latvian') {
		engineDataVal = 'Latvio';
	}
	else if (engineDataVal == 'Lingala') {
		engineDataVal = 'Lingala';
	}
	else if (engineDataVal == 'Lithuanian') {
		engineDataVal = 'Lituano';
	}
	else if (engineDataVal == 'Luba-Lulua') {
		engineDataVal = 'Luba-lulua';
	}
	else if (engineDataVal == 'Luo (Kenya and Tanzania)') {
		engineDataVal = 'Luo (Kenia y Tanzania)';
	}
	else if (engineDataVal == 'Lushai') {
		engineDataVal = 'Lushai';
	}
	else if (engineDataVal == 'Macedonian') {
		engineDataVal = 'Macedonio';
	}
	else if (engineDataVal == 'Madurese') {
		engineDataVal = 'Lengua maduresa';
	}
	else if (engineDataVal == 'Maithali') {
		engineDataVal = 'Maithilí';
	}
	else if (engineDataVal == 'Malagasy') {
		engineDataVal = 'Malgache';
	}
	else if (engineDataVal == 'Malay') {
		engineDataVal = 'Malayo';
	}
	else if (engineDataVal == 'Malayalam') {
		engineDataVal = 'Malayalam';
	}
	else if (engineDataVal == 'Maltese') {
		engineDataVal = 'Maltés';
	}
	else if (engineDataVal == 'Mandarin') {
		engineDataVal = 'Mandarín';
	}
	else if (engineDataVal == 'Mandingo') {
		engineDataVal = 'Mandingo';
	}
	else if (engineDataVal == 'Manipuri') {
		engineDataVal = 'Manipuri';
	}
	else if (engineDataVal == 'Manobo Languages') {
		engineDataVal = 'Lenguas manobo';
	}
	else if (engineDataVal == 'Manx') {
		engineDataVal = 'Manés';
	}
	else if (engineDataVal == 'Maori') {
		engineDataVal = 'Maorí';
	}
	else if (engineDataVal == 'Marathi') {
		engineDataVal = 'Maratí';
	}
	else if (engineDataVal == 'Marshall') {
		engineDataVal = 'Marshalés';
	}
	else if (engineDataVal == 'Marwari') {
		engineDataVal = 'Marwari';
	}
	else if (engineDataVal == 'Mayan Languages') {
		engineDataVal = 'Lenguas mayas';
	}
	else if (engineDataVal == 'Mende') {
		engineDataVal = 'Mendé';
	}
	else if (engineDataVal == 'Moldavian') {
		engineDataVal = 'Moldavo';
	}
	else if (engineDataVal == 'Mongolian') {
		engineDataVal = 'Mongol';
	}
	else if (engineDataVal == 'Nahuatl') {
		engineDataVal = 'Náuatl';
	}
	else if (engineDataVal == 'Nauru') {
		engineDataVal = 'Nauru';
	}
	else if (engineDataVal == 'Navajo') {
		engineDataVal = 'Navajo';
	}
	else if (engineDataVal == 'Nepali') {
		engineDataVal = 'Nepalí';
	}
	else if (engineDataVal == 'Newari') {
		engineDataVal = 'Newari';
	}
	else if (engineDataVal == 'Niger-Kordofanian') {
		engineDataVal = 'Níger-kordofano';
	}
	else if (engineDataVal == 'Niuean') {
		engineDataVal = 'Niueano';
	}
	else if (engineDataVal == 'North American Indian') {
		engineDataVal = 'Lenguas de los indígenas de América del Norte';
	}
	else if (engineDataVal == 'Norwegian') {
		engineDataVal = 'Noruego';
	}
	else if (engineDataVal == 'Nubian Languages') {
		engineDataVal = 'Legunas nubias';
	}
	else if (engineDataVal == 'Nyanja') {
		engineDataVal = 'Ñania';
	}
	else if (engineDataVal == 'Nyankole') {
		engineDataVal = 'Ñacole';
	}
	else if (engineDataVal == 'Nyoro') {
		engineDataVal = 'Nyoro';
	}
	else if (engineDataVal == 'Nzima') {
		engineDataVal = 'Nzema';
	}
	else if (engineDataVal == 'Ojibwa') {
		engineDataVal = 'Ojibwa';
	}
	else if (engineDataVal == 'Old Persian (600-400)') {
		engineDataVal = 'Persa antiguo (600-400)';
	}
	else if (engineDataVal == 'Oriya') {
		engineDataVal = 'Oriya';
	}
	else if (engineDataVal == 'Oromo') {
		engineDataVal = 'Oromo';
	}
	else if (engineDataVal == 'Ossetic') {
		engineDataVal = 'Osético';
	}
	else if (engineDataVal == 'Pampanga') {
		engineDataVal = 'Pampangano';
	}   
	else if (engineDataVal == 'Pangasinan') {
		engineDataVal = 'Pangasino';
	}
	else if (engineDataVal == 'Papiamento') {
		engineDataVal = 'Papiamento';
	}
	else if (engineDataVal == 'Papuan-Australian (Other)') {
		engineDataVal = 'Papú-australiano (otro)';
	}
	else if (engineDataVal == 'Persian') {
		engineDataVal = 'Persa';
	}
	else if (engineDataVal == 'Philippine') {
		engineDataVal = 'Filipino';
	}
	else if (engineDataVal == 'Polish') {
		engineDataVal = 'Polaco';
	}
	else if (engineDataVal == 'Ponape') {
		engineDataVal = 'Ponapeño';
	}
	else if (engineDataVal == 'Portuguese') {	
		engineDataVal = 'Portugués';
	}
	else if (engineDataVal == 'Provencal (to 1500)') {
		engineDataVal = 'Provenzal (hasta 1500)';
	}
	else if (engineDataVal == 'Punjabi') {	
		engineDataVal = 'Punyabí';
	}
	else if (engineDataVal == 'Pushto') {
		engineDataVal = 'Pastún';
	}
	else if (engineDataVal == 'Quechua') {
		engineDataVal = 'Quechua';
	}
	else if (engineDataVal == 'Rajasthani') {
		engineDataVal = 'Rajasthaní';
	}
	else if (engineDataVal == 'Rhaeto-Romance') {
		engineDataVal = 'Retorrománico';
	}
	else if (engineDataVal == 'Romance (Other)') {
		engineDataVal = 'Romance (otro)';
	}
	else if (engineDataVal == 'Romanian') {
		engineDataVal = 'Rumano';
	}
	else if (engineDataVal == 'Romany') {
		engineDataVal = 'Romaní';
	}
	else if (engineDataVal == 'Russian') {
		engineDataVal = 'Ruso';
	}
	else if (engineDataVal == 'Salishan Languages') {
		engineDataVal = 'Lenguas salishanas';
	}
	else if (engineDataVal == 'Samoan') {
		engineDataVal = 'Samoano';
	}
	else if (engineDataVal == 'Sango') {
		engineDataVal = 'Sango';
	}
	else if (engineDataVal == 'Sanskrit') {
		engineDataVal = 'Sánscrito';
	}
	else if (engineDataVal == 'Sasak') {
		engineDataVal = 'Sasaco';
	}
	else if (engineDataVal == 'Scots') {
		engineDataVal = 'Escocés';
	}
	else if (engineDataVal == 'Semitic (Other)') {
		engineDataVal = 'Semítico (otro)';
	}
	else if (engineDataVal == 'Serbo-Croatian (Cyrilic)') {
		engineDataVal = 'Serbocroata (alfabeto cirílico)';
	}
	else if (engineDataVal == 'Serbo-Croatian (Roman)') {
		engineDataVal = 'Serbocroata (alfabeto romano)';
	}
	else if (engineDataVal == 'Serer') {
		engineDataVal = 'Serer';
	}
	else if (engineDataVal == 'Shona') {
		engineDataVal = 'Sona';
	}
	else if (engineDataVal == 'Sign') {
		engineDataVal = 'Lenguaje de señas';
	}
	else if (engineDataVal == 'Sindhi') {
		engineDataVal = 'Sindhi';
	}
	else if (engineDataVal == 'Sinhalese') {
		engineDataVal = 'Singalés';
	}
	else if (engineDataVal == 'Siouan (Other)') {
		engineDataVal = 'Siouan (otro)';
	}
	else if (engineDataVal == 'Slavic') {
		engineDataVal = 'Eslavo';
	}
	else if (engineDataVal == 'Slovak') {
		engineDataVal = 'Eslovaco';
	}
	else if (engineDataVal == 'Slovenian') {
		engineDataVal = 'Esloveno';
	}
	else if (engineDataVal == 'Somali') {
		engineDataVal = 'Somalí';
	}
	else if (engineDataVal == 'Soninke') {
		engineDataVal = 'Soninké';
	}
	else if (engineDataVal == 'Sorbian Languages') {
		engineDataVal = 'Lenguas sorbias';
	}
	else if (engineDataVal == 'Sotho') {
		engineDataVal = 'Soto';
	}
	else if (engineDataVal == 'South American Indian') {
		engineDataVal = 'Lenguas de los indígenas de América del Sur';
	}
	else if (engineDataVal == 'Spanish') {
		engineDataVal = 'Español';
	}
	else if (engineDataVal == 'Sukuma') {
		engineDataVal = 'Sukuma';
	}
	else if (engineDataVal == 'Sumerian') {
		engineDataVal = 'Sumerio';
	}
	else if (engineDataVal == 'Sundanese') {
		engineDataVal = 'Sundanés';
	}
	else if (engineDataVal == 'Swahili') {
		engineDataVal = 'Swahili';
	}
	else if (engineDataVal == 'Swazi') {
		engineDataVal = 'Suazi';
	}
	else if (engineDataVal == 'Swedish') {
		engineDataVal = 'Sueco';
	}
	else if (engineDataVal == 'Sylheti') {
		engineDataVal = 'Sylheti';
	}
	else if (engineDataVal == 'Syriac') {
		engineDataVal = 'Siríaco';
	}
	else if (engineDataVal == 'Tagalog') {
		engineDataVal = 'Tagalo';
	}
	else if (engineDataVal == 'Tahitian') {
		engineDataVal = 'Tahitiano';
	}
	else if (engineDataVal == 'Taiwanese') {
		engineDataVal = 'Taiwanés';
	}
	else if (engineDataVal == 'Tajik') {
		engineDataVal = 'Tayiko';
	}
	else if (engineDataVal == 'Tamashek') {
		engineDataVal = 'Tamasheq';
	}
	else if (engineDataVal == 'Tamil') {
		engineDataVal = 'Tamil';
	}
	else if (engineDataVal == 'Tatar') {
		engineDataVal = 'Tataro';
	}
	else if (engineDataVal == 'Telugu') {
		engineDataVal = 'Telegú';
	}
	else if (engineDataVal == 'Terena') {
		engineDataVal = 'Tereno';
	}
	else if (engineDataVal == 'Tetum') {
		engineDataVal = 'Tetum';
	}
	else if (engineDataVal == 'Thai') {
		engineDataVal = 'Tailandés';
	}
	else if (engineDataVal == 'Tibetan') {
		engineDataVal = 'Tibetano';
	}
	else if (engineDataVal == 'Tigre') {
		engineDataVal = 'Tigré';
	}
	else if (engineDataVal == 'Tigrinya') {
		engineDataVal = 'Tigriña';
	}
	else if (engineDataVal == 'Timne') {
		engineDataVal = 'Temné';
	}
	else if (engineDataVal == 'Tok Pisin') {
		engineDataVal = 'Tok pisin';
	}
	else if (engineDataVal == 'Tokelauan') {
		engineDataVal = 'Tokelauano';
	}
	else if (engineDataVal == 'Tonga (Nyasa)') {
		engineDataVal = 'Tongano (Nyasa)';
	}
	else if (engineDataVal == 'Tonga (Tonga Islands)') {
		engineDataVal = 'Tongano (Islas Tonga)';
	}
	else if (engineDataVal == 'Truk') {
		engineDataVal = 'Truk';
	}
	else if (engineDataVal == 'Tsimshian') {
		engineDataVal = 'Tsimshian';
	}
	else if (engineDataVal == 'Tsonga') {
		engineDataVal = 'Tsonga';
	}
	else if (engineDataVal == 'Tswana') {
		engineDataVal = 'Tswana';
	}
	else if (engineDataVal == 'Tumbuka') {
		engineDataVal = 'Tumbuka';
	}
	else if (engineDataVal == 'Turkish') {
		engineDataVal = 'Turco';
	}
	else if (engineDataVal == 'Turkish, Ottoman') {
		engineDataVal = 'Turco, otomano';
	}
	else if (engineDataVal == 'Turkmen') {
		engineDataVal = 'Turcomano';
	}
	else if (engineDataVal == 'Tuvalu') {
		engineDataVal = 'Tuvaluano';
	}
	else if (engineDataVal == 'Twi') {
		engineDataVal = 'Twi';
	}
	else if (engineDataVal == 'Ugaritic') {
		engineDataVal = 'Ugarítico';
	}
	else if (engineDataVal == 'Uighur') {
		engineDataVal = 'Uigur';
	}
	else if (engineDataVal == 'Ukrainian') {
		engineDataVal = 'Ucraniano';
	}
	else if (engineDataVal == 'Umbundu') {
		engineDataVal = 'Umbundu';
	}
	else if (engineDataVal == 'Undetermined') {
		engineDataVal = 'Indeterminada';
	}
	else if (engineDataVal == 'Urdu') {
		engineDataVal = 'Urdu';
	}
	else if (engineDataVal == 'Uzbek') {
		engineDataVal = 'Uzbeko';
	}
	else if (engineDataVal == 'Vietnamese') {
		engineDataVal = 'Vietnamita';
	}
	else if (engineDataVal == 'Votic') {
		engineDataVal = 'Votia';
	}
	else if (engineDataVal == 'Wakashan Languages') {
		engineDataVal = 'Lenguas wakashan';
	}
	else if (engineDataVal == 'Welsh') {
		engineDataVal = 'Galés';
	}
	else if (engineDataVal == 'Wolof') {
		engineDataVal = 'Wolof';
	}
	else if (engineDataVal == 'Xhosa') {
		engineDataVal = 'Xhosa';
	}
	else if (engineDataVal == 'Yakut') {
		engineDataVal = 'Yakuto';
	}
	else if (engineDataVal == 'Yao (Bantu)') {
		engineDataVal = 'Yao (bantú)';
	}
	else if (engineDataVal == 'Yapese') {
		engineDataVal = 'Yapese';
	}
	else if (engineDataVal == 'Yiddish') {
		engineDataVal = 'Ídish';
	}
	else if (engineDataVal == 'Yoruba') {
		engineDataVal = 'Yoruba';
	}
	else if (engineDataVal == 'Zande') {
		engineDataVal = 'Zande';
	}
	else if (engineDataVal == 'Zapotec') {
		engineDataVal = 'Zapoteco';
	}
	else if (engineDataVal == 'Zenaga') {
		engineDataVal = 'Zenaga';
	}
	else if (engineDataVal == 'Zulu') {
		engineDataVal = 'Zulú';
	}
	else if (engineDataVal == 'Zuni') {
		engineDataVal = 'Zuni';
	}
	return engineDataVal;
}
// make lookup table for engine data by navigator name or navigator name.value
var lookup;

// merge search engine data with menu data to produce what will be displayed in filter menu
function updateMenu(menuData,engineData,selectedValues,fixFilter) {
	lookup = [];  // reset lookup data
	if(engineData != null && engineData != undefined){
		for (var i=0; i<engineData.length; i++) {
			if(site_id == 'medicare' && langPref == 'sp'){
				engineData[i].displayable = translateToSpanish(engineData[i].displayable);
			}
			/*-- END CHANGES P23695 Medicare Spanish Translation - n709197 --*/
			var name = engineData[i].nav;
			var nameValue = name + '.' + engineData[i].val;
			if (lookup[name] == null) {
				lookup[name] = i;
			}
			lookup[nameValue] = i;
		}
	}
	// loop through menu data
	for (var i=0; i<menuData.length; i++) {
		var filter = menuData[i];
		
		// if we are only doing one filter (a filter fix), skip all others
		if (fixFilter && fixFilter != filter.name) {
			continue;
		}
		
		filter.show = false;  // don't show unless some values
		
		if (filter.nav) {
			// add navigator values for this filter
			filter.values = [];
			
			var k=lookup[filter.nav];
			k = k ? k : 0;
			if(engineData != null && engineData != undefined){
				for (; k<engineData.length; k++) {
					var navigator = engineData[k];
					if (navigator.nav != filter.nav) break; // no more for for this navigator
	
					var val = navigator.val;
					if (filter.exclude && filter.exclude[val]) continue;  // do not use this value
	
					var filterVal = {};  // a new value
					filterVal.name = navigator.displayable;
					filterVal.val = val;
					filterVal.active = isActiveValue(filter.name, val, selectedValues);
					filterVal.count = navigator.count;
					filterVal.nav = filter.nav;  // all values have the same navigator
					filter.values.push(filterVal);
					filter.show = true;  // has at least one value
				}
			}
			// process the short/long list if necessary
			if (filter.shortLength) {
				// short list by popularity
				sortByCount(filter.values);
				for (var k=0; k<filter.values.length; k++) {
					if (k < filter.shortLength) {
						filter.values[k].list = 'short';
					} else {
						filter.values[k].list = 'long';
					}
				}
			}
			sortByName(filter.values);
		} else if (filter.values) {
			// values specified in filter
			sortByName(filter.values);
			for (var j=0; j<filter.values.length; j++) {
				filterVal = filter.values[j];
				var nav = filterVal.nav;
				var val = filterVal.val;
				
				// see if we can find this value in the navigators
				var k = lookup[nav + '.' + val];
				if (k!=undefined && k!=null && (k==0 || k)) {  // found it
					if(engineData != null && engineData != undefined){
						var navigator = engineData[k];
						
						// see if value is conditional and should not be used
						if (skipFilterValue(filterVal)) {
							// delete value from menu
							filter.values[j] = null;
						} else {  // use the value
							filterVal.count = navigator.count;
							filterVal.active = isActiveValue(filter.name, val, selectedValues);
							filter.show = true;  // has at least one value
						} // conditional value
					}
				} else { // didn't find it
					// delete value from menu
					filter.values[j] = null;
				} // navigator found for filter value
			} // loop through filter values
			
		} // type of filter
		
		// if this filter has no values, remove it
		if (!filter.show) {
			menuData[i] = null;
			continue;  // no more processing this filter
		}
		
	} // loop through all filters
	
}

// given the menu HTML and the updated menu data, create the HTML
// for all the values in the filters in the menu.  Each menu item will look like this:
// <li class="filter-value filter-shortlist filter-selected">
//   <div class="filter-display">Male <div class="filter-count-display">123</div></div>
//   <div class="filter-match">M</div>
//   <div class="filter-nav">gendernavigator</div>
//   <div class="filter-count">123</div>
// </li>
//
// If the value is on a short list, it will have a class of filter-shortlist
// If the value has been selected, it will have the class filter-selected
// If the value has not been selected, it will have the class filter-unselected
// the menu values will always be placed inside the element in the filter with class
// filter-sub-level.  The HTML will be added there by this function
function addMenuValues(menuHtml, menuData, fixFilter) {
	// if we are fixing a menu that was already created, first clear out the old values
	if (fixFilter) {
		var filterHtml = menuHtml.find("div.filter-name").filter(function (index) {
		    return $(this).text() == fixFilter;
		})
		filterHtml = filterHtml.parent();
		var htmlLocation = filterHtml.find('ul.filter-sub-level');
		htmlLocation.html('');
	}

	// loop through menu data
	for (var i=0; i<menuData.length; i++) {
		var filter = menuData[i];
		if (filter == null) continue;  // skip any deleted filters
		var filterName = filter.name;

		
		// if we are only doing one filter (a filter fix), skip all others
		if (fixFilter && fixFilter != filterName) {
			continue;
		}

		// find this same filter in the menu HTML
		var filterHtml = menuHtml.find("div.filter-name").filter(function (index) {
		    return $(this).text() == filterName;
		})

		if (filterHtml.size() == 0) continue;  // skip filter if not in the HTML
		filterHtml = filterHtml.parent();
		
		// get the html for the values in this filter
		var html = createFilterValuesHtml(filter);
		
		// find where to put the value HTML within the filter HTML
		var htmlLocation = filterHtml.find('ul.filter-sub-level');
		if (htmlLocation.size() == 0) continue;  // skip if no place to put the HTML

		// add the values HTML to the filter HTML
		htmlLocation.html(html);
	}
}

// create the HTML for the values in a filter
function createFilterValuesHtml(filter) {
	var html = '';
	for (var i=0; i<filter.values.length; i++) {
		var value = filter.values[i];
		if (value == null) continue;  // skip deleted ones
		html += createFilterValueHtml(value);

	}
	return html;
}

// create the HTML for a single value in a filter
function createFilterValueHtml(value) {
	var filterMatch = value.val;
	var filterNav = value.nav;
	var filterDisplay = value.name;
	var filterCount = value.count;
	var filterActive = value.active;
	var filterNotDisplayCount="";
	if(value.displaycount != undefined){
		filterNotDisplayCount="true";
	}
	else{
		filterNotDisplayCount="false";
	}
	var activeClass = filterActive ? 'filter-selected' : 'filter-unselected';
	var listClass = value.list ? (value.list ==  'short' ? 'filter-shortlist' : 'filter-longlist') : "";
	var countHtml = "";
	if(filterNotDisplayCount=="false"){
		countHtml="<div class='filter-count-display'> (" + filterCount + ")</div>";
	}
	else{
		countHtml="<div class='filter-count-display'></div>";
	}
	var conditional = value.cond;  // values shows conditionally
	var condHtml = conditional ? '<div class="filter-conditional">' + conditional + '</div>\n' : '';

	var html = 
		'<li class="filter-value ' + activeClass + ' ' + listClass + '">\n' +
		'  <div class="filter-display">' + filterDisplay + countHtml + '</div>\n' +
		'  <div class="filter-match">' + filterMatch + '</div>\n' +
		'  <div class="filter-nav">' + filterNav + '</div>\n' +
		'  <div class="filter-count">' + filterCount + '</div>\n' +
		'</li>\n'
	;
	return html;
}

// these sort functions are complicated because there is an IE bug with sort functions
// that compare the arguments directly

// sort filter values by count field
function sortByCount(values) {
	values.sort(function(v1,v2){
		var n1=parseInt(v1.count),
		    n2=parseInt(v2.count);
		if(n1 > n2) return -1;
		if(n1 < n2) return 1;
		return 0;
	});
}

/* Filter Ui Design Changes  Start */
function toggleFilterPleat(){
	$('#provTypeFilContent').toggle();
	if($('#filterOpenImg').is(':visible')){
		$('#filterOpenImg').hide();
		$('#filterCloseImg').show();
		/* Filter Ui Design Changes  Start */
		/* $('.providerTypeFilterTableDisplayName').css("margin-left","-12px"); */
		/* $('#provtypePleatLabel').css("color","#ffffff"); */
		/* Filter Ui Design Changes  End */
	}else{
		$('#filterOpenImg').show();
		$('#filterCloseImg').hide();
		/* Filter Ui Design Changes  Start */
		/* $('.providerTypeFilterTableDisplayName').css("margin-left","-9px"); */
		/* $('#provtypePleatLabel').css("color","black"); */
		/* Filter Ui Design Changes  End */
	}
}
/* Filter Ui Design Changes  End */

// sort filter values by name field
function sortByName(values) {
	values.sort(function(v1,v2){
		var s1=(''+v1.name).toLowerCase(),
		    s2=(''+v2.name).toLowerCase();
		if(s1 > s2) return 1;
		if(s1 < s2) return -1;
		return 0;
	});
}

function tweakFilterValues(filterValues) {
	var tweak = getHtml($('div.filter-search-tweak'));
	if (tweak.length == 0) return filterValues;
	var tweakSplit = tweak.split('|');
	if (filterValues.indexOf(tweakSplit[0]) >= 0) {
		return filterValues + '|' + tweakSplit[1];
	} else {
		return filterValues;
	}
}

Array.prototype.remove = function() {
    var what, a = arguments, L = a.length, ax;
    while (L && this.length) {
        what = a[--L];
        while ((ax = this.indexOf(what)) !== -1) {
            this.splice(ax, 1);
        }
    }
    return this;
};
