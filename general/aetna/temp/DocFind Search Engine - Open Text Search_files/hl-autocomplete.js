var typeAheadURL = $(".typeAheadURL").html();
var idetifyFlowsToEnableFormSubmit = true;
function clickToViewMore(obj){
	 $("." + $(obj).attr('value')).removeClass("hidden");
	 $("." +obj.className).addClass("hidden");
}
/*-- START CHANGES P20751b ACO Branding - n596307 --*/
function checkForACOClassCodeBeforeDisplaying(acoCatObject){
	if($.inArray('ACO', acoCatObject.classcodes) > -1){
		return true;
	}
	return false;
}
/*-- end CHANGES P20751b ACO Branding - n596307 --*/
(function(window, document, undefined) {
  var groupBy = function(array, predicate) {
    var grouped = {};
    var orderedGroup = {};
if(array != null && array.length>0){
    for (var i = 0; i < array.length; i++) {
      var groupKey = predicate(array[i]);
      if (typeof(grouped[groupKey]) === "undefined"){
    	  if(array[i].type == 'categorycode'){
    		  if(checkForACOClassCodeBeforeDisplaying(array[i])){
    			  grouped[groupKey] = [];
    		  }
    	  }
    	  else{
    		  grouped[groupKey] = [];
    	  }
      }
      
      if(array[i].type == 'specialist_any_location'){
    	  array[i].type = 'specialist';
    	  array[i].result = array[i].result + ' (any location)';
      }
      /*-- START CHANGES P20751b ACO Branding - n596307 --*/
      if(array[i].type == 'categorycode'){
    	  if(checkForACOClassCodeBeforeDisplaying(array[i])){
    		  grouped[groupKey].push(array[i]);
    	  }
      }
      else{
    	  grouped[groupKey].push(array[i]);
      }
      /*-- END CHANGES P20751b ACO Branding - n596307 --*/
    }
}
   
  if(grouped.specialist!=null  &&  grouped.specialist.length>0){
	   var arrLength = 0;
	   if(grouped.specialist_any_location!=null && grouped.specialist_any_location!='undefined'){
		   arrLength = grouped.specialist_any_location.length;
	   }
	   if(arrLength>0){
		   for(count=0;count<arrLength;count++){
			   grouped.specialist.splice(count,0,grouped.specialist_any_location[count]);
			   orderedGroup.specialist = grouped.specialist;
		   }
	   }else{
		   orderedGroup.specialist = grouped.specialist;
	   }
   }
   
   if(grouped.hospital!=null  &&  grouped.hospital.length>0){
	   orderedGroup.hospital = grouped.hospital;
   }
   
   /*-- START CHANGES P20751b ACO Branding - n596307 --*/
   if(grouped.categorycode!=null  &&  grouped.categorycode.length>0){
	   orderedGroup.categorycode = grouped.categorycode;
   }
   /*-- END CHANGES P20751b ACO Branding - n596307 --*/
   
   if(grouped.facility!=null  &&  grouped.facility.length>0){
	   orderedGroup.facility = grouped.facility;
   }
   
   /* if(grouped.physician_group!=null  &&  grouped.physician_group.length>0){
		orderedGroup.physician_group = grouped.physician_group;
	} */
   
   /*if(grouped.location!=null  &&  grouped.location.length>0){
	   orderedGroup.location = grouped.location;
   }*/

   if(grouped.specialty!=null  &&  grouped.specialty.length>0){
	   orderedGroup.specialty = grouped.specialty;
   }
   
   if(grouped.condition!=null  &&  grouped.condition.length>0){
	   orderedGroup.condition = grouped.condition;
   }
   
   if(grouped.procedure!=null  &&  grouped.procedure.length>0){
	   orderedGroup.procedure = grouped.procedure;
   }
   return orderedGroup;
  }

/* P20488 - 1231 changes start */
  var buildSearchBox = function() {
    return '<div class="hl-search-box">' +
            '<div class="hl-searchbar">' +
            '<input id="hl-autocomplete-search" title="hl-autocomplete-search" type="text" class="hl-searchbar-input" name="q" value="'+ghostTextWhatBox+'"  onblur="javascript:addGhostWhatText();" onfocus="javascript:changeFormat();" onkeypress="javscript:whereValFunction();"/>' +
            '</div>' +
            '</div>';
  }

  var buildResultBox = function(json) {
    var data = [];
    var groupData = groupBy(json, function (obj) {
      return obj.type;
    });
    var oArray = null;
    $.each(groupData, function(key, val) {
      oArray = val;
      /*-- START CHANGES P20751b ACO Branding - n596307 --*/
      $.each(oArray, function(i, v) {
        data.push({label: v["result"],url: v["url"], category: v["type"], subcategory: v["subtype"], aetnaid: v["aetnaid"], lastname: v["lastname"], firstname: v["firstname"], zipcode: v["zipcode"], coordinates: v["coordinates"], categorycode: v["categorycode"]});
      });
      /*-- END CHANGES P20751b ACO Branding - n596307 --*/
    });
    return data;
  }
/* P20488 - 1231 changes end */

  var resetData = function() {
    $.widget("custom.catcomplete", $.ui.autocomplete, {
      _renderMenu: function(ul, items) {
        var isviewmore = false,
                maxnum = 3,
                morenum = 0;
        var self = this,
                currentCategory = "";
        var currentArray = groupBy(items, function (obj) {
          return obj.category;
        });
        
        $.each(items, function(index, item) {
          if (item.category != currentCategory) {

            if (typeof currentArray[currentCategory] != "undefined") {
              if (index >= maxnum) {
                isviewmore = true;
                morenum = index - maxnum;
              }
              maxnum += currentArray[currentCategory].length;
            }


            if (isviewmore) {
              if (morenum > 0) {
                /* ul.append('<a id="viewmore" class=viewmore' + currentCategory + ' href="javaScript:void(0);" onclick="clickToViewMore(this);" value="' + currentCategory + '">' + morenum + ' more...</a>'); */
			ul.append('<a id="viewmore" class=viewmore' + currentCategory + ' href="javaScript:void(0);" onclick="clickToViewMore(this);" value="' + currentCategory + '">' + morenum + ' more ' + $('#' + currentCategory.toLowerCase() + 'hlLabel').text() +'</a>');
              }
              isviewmore = false;
            }

            if(index==0){
            	var hlLabelForDisplay = $('#' + item.category.toLowerCase() + 'hlLabel').text();
            	/* var liToAdd = "<li class='ui-autocomplete-category topSpacing' id='" + item.category.toLowerCase() + "ForOrdering'" + ">"+ changeToCamelCase(hlLabelForDisplay) + ':' + "</li>"; */
			var liToAdd = "<li class='ui-autocomplete-category topSpacing' id='" + item.category.toLowerCase() + "ForOrdering'" + "></li>";
            	ul.append(liToAdd);
            }else{
            	var hlLabelForDisplay = $('#' + item.category.toLowerCase() + 'hlLabel').text();
            	/* var liToAdd = "<li class='ui-autocomplete-category borderCategory' id='"+ item.category.toLowerCase() + "ForOrdering'" + ">" + changeToCamelCase(hlLabelForDisplay) + ':' + "</li>"; */
			var liToAdd = "<li class='ui-autocomplete-category borderCategory' id='"+ item.category.toLowerCase() + "ForOrdering'" + "></li>";
            	ul.append(liToAdd);
            }
            
            currentCategory = item.category;

          }

          self._renderItem(ul, item, maxnum, index);
          if (index == (items.length - 1) && index >= maxnum) {
            /* ul.append('<a id="viewmore" class=viewmore' + currentCategory + ' href="javaScript:void(0);" onclick="clickToViewMore(this);" value="' + currentCategory + '">' + (index - maxnum + 1) + ' more...</a>'); */
		 ul.append('<a id="viewmore" class=viewmore' + currentCategory + ' href="javaScript:void(0);" onclick="clickToViewMore(this);" value="' + currentCategory + '">' + (index - maxnum + 1) + ' more ' + $('#' + currentCategory.toLowerCase() + 'hlLabel').text() +'</a>');
          }
          
        });
        
        //$searchfor.appendTo(ul);
      },
      _renderItem : function(ul, item, maxnum, index) {
        if (typeof item.label != "undefined") {
          //highlights typed
/* P20488 - 1231 changes start */
          item.label = item.label.replace(new RegExp("(?![^&;]+;)(?!<[^<>]*)(" + $.ui.autocomplete.escapeRegex(this.term) + ")(?![^<>]*>)(?![^&;]+;)(.*)", "gi"), "<strong>$1</strong>$2");
/* P20488 - 1231 changes end */
        }

        item.isviewmore = false;
        if (index >= maxnum) {
          item.hidden = true;
          return $("<li class='hidden " + item.category + "'></li>")
                  .data("item.autocomplete", item)
                  .append("<a>" + item.label + "</a>")
                  .appendTo(ul);
        }
        item.hidden = false;
        return $("<li></li>")
                .data("item.autocomplete", item)
                .append("<a>" + item.label + "</a>")
                .appendTo(ul);
      }
    });
    
    var d={}
    
    var hlSwitch = 'ON';
    if(hlSwitch!='OFF'){
    $("#hl-autocomplete-search").catcomplete({
      delay: 100,
      source: function(request, response) {
        $.ajax({
          url: $(".typeAheadURL").html().replace( /\&amp;/g, '&' ),
          dataType: "jsonp",
          data: {
            "q": request.term
          },
          success: function(xmlResponse) {
            if (request.term !== $("#hl-autocomplete-search").val()) {
              return;
            }
            var categorydata = buildResultBox(xmlResponse["data"]);
            response($.map(categorydata, function(item) {
              return {
                label: item.label,
                url: item.url,
                category: item.category,
                aetnaid: item.aetnaid,
                lastname: item.lastname,
                firstname: item.firstname,
                zipcode: item.zipcode,
                coordinates: item.coordinates,
                categorycode : item.categorycode
                //detectedzip: item.detectedzip
                //detectedcoordinates = item.detectedcoordinates;
                //detectedstate = ui.item.detectedstate;
              }
            }));
          }
        });
      },

      minLength: 1,
      focus: function(event, ui) {
        var item = ui.item;
        if (item.hidden) {
        	$('.viewmore'+item.category.toLowerCase()).click();
        }
      },
      select:function(event, ui) {
        $("#searchQuery").val(ui.item.value);
        $("#mainTypeAheadSelectionVal").val(ui.item.value);
        var uiCategory = ui.item.category;
        /* Changes for Story9523/9517 Start */
        var aetnaid = ui.item.aetnaid;
        var lastname = ui.item.lastname;
        var firstname = ui.item.firstname;
        var zipcode = ui.item.zipcode;
        var coordinates = ui.item.coordinates;
	/*-- START CHANGES P20751b ACO Branding - n596307 --*/
        var categorycode = ui.item.categorycode;
        //var detectedzip = ui.item.detectedzip;
        //var detectedcoordinates = ui.item.detectedcoordinates;
        //var detectedstate = ui.item.detectedstate;
        
        if(uiCategory == 'specialty'){
        	$('#quickSearchTypeMainTypeAhead').val('specialty');
        }else if(uiCategory == 'location'){
        	$('#quickSearchTypeMainTypeAhead').val('location');
        }
        /*-- START CHANGES P20751b ACO Branding - n596307 --*/
        else if(uiCategory == 'categorycode'){
	//commented to call HL API each time
        	//$('#quickSearchTypeMainTypeAhead').val('categorycode');
        	$('#quickCategoryCode').val(categorycode); 
        }
	/*-- END CHANGES P20751b ACO Branding - n596307 --*/
	   /* P19791a PCR#17887 April 2014 - Hospital Type Ahead Fix - Rohit : START */
        /* else if(uiCategory == 'hospital'){
        	$('#quickSearchTypeMainTypeAhead').val('hospital');
        } */
        /* Changes for story 9517 Start */
        else if ( uiCategory == 'physician_group' || uiCategory == 'facility' || uiCategory == 'hospital' || uiCategory =='specialist'){
/* P19791a PCR#17887 April 2014 - Hospital Type Ahead Fix - Rohit : END */
        	$('#quickSearchTypeMainTypeAhead').val(uiCategory);
        	$('#aetnaId').val(aetnaid);
	
        	/* P20488 - 1231 changes start */
		$('.hl-autocomplete-location-textBox .hl-autocomplete-location-box .hl-autocomplete-locationbar .hl-searchbar-input-location').css('color','#000000');
        	$('.hl-autocomplete-location-textBox .hl-autocomplete-location-box .hl-autocomplete-locationbar .hl-searchbar-input-location').css('font-style','normal');
        	$('#hl-autocomplete-search-location').val(zipcode);
		$("#geoMainTypeAheadLastQuickSelectedVal").val(zipcode);
        	/* P20488 - 1231 changes end */

           $('#QuickZipcode').val(zipcode); 
           $('#QuickCoordinates').val(coordinates);
           $('#geoBoxSearch').val('true');

           $('#Quicklastname').val(lastname);
           $('#Quickfirstname').val(firstname);
        }
        /* else if(uiCategory == 'specialist_any_location'){
    		$('#quickSearchTypeMainTypeAhead').val(uiCategory);
       	$('#Quicklastname').val(lastname); 	                  		$('#Quickfirstname').val(firstname);	          
    	} */
    	
        /* Changes for story 9517 End*/
    	/*if (!(uiCategory == 'physician_group' || uiCategory == 'facility' || uiCategory =='specialist' || uiCategory =='hospital')){
        		if(detectedstate!=null && detectedstate!= ''){
        			$('#stateCode').val(detectedstate);
        			$('#geoBoxSearch').val('true');
        		}
        		else if(zipcode == null || zipcode == ''){
    			if((detectedzip !=null && detectedzip != '') && (detectedcoordinates !=null && detectedcoordinates != '')){
        			$('#QuickZipcode').val(detectedzip);
        			$('#QuickCoordinates').val(detectedcoordinates);
        			$('#geoMainTypeAheadLastQuickSelectedVal').val();
        			$('#geoBoxSearch').val('true');
        		}
        	}
    	}*/
     }  
    });
}
}

  $(function() {
    $(".hl-autocomplete").append(buildSearchBox());
    //508 changes
    if($('#searchQuery').val() != null && $('#searchQuery').val() != ''){
    	idetifyFlowsToEnableFormSubmit = false;
    }
    if(idetifyFlowsToEnableFormSubmit){
    	defaultFocusToSearchFor();
    }
/*-- Start changes SR1347 Sep2014 - N204183 --*/
    prefillExternalSearchTypeAndGeoSearch();
    /*-- End changes SR1347 Sep2014 - N204183 --*/
    resetData();
//  Changes to emulate click functionality and prevent form submitting when Enter key is pressed.
// Start    
     $('#hl-autocomplete-search').bind('keydown',function(event) {
		//reset plantypelink selected
	planTypeForPublic = '';
     	if(event.which == 13) {
     		event.preventDefault();
     		var str = $('#hl-autocomplete-search').val();
     		str = trim(str);
     		$('#hl-autocomplete-search').val(str);
     		if($('#hl-autocomplete-search').val()){
			$(".ui-autocomplete").hide();
     			$('.hl-searchbar-button').click();
 			}
        }
 	});
//End
  });
  
  function changeToCamelCase(str){
	  str = str.toLowerCase().replace(/\b[a-z]/g, function(letter) {
	  	return letter.toUpperCase();
	  });
	  
	  return str;
  }
})(window, document);
