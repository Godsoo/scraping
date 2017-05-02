var typeAheadLocationURL = $("#typeAheadLocationURL").text();
//var typeAheadURL = $(".typeAheadURL").html();
/*-- START CHANGES P20751b ACO Branding - n596307 --*/
var hlStatusCodeFirstWhereBox;
/*-- END CHANGES P20751b ACO Branding - n596307 --*/
(function(window, document, undefined) {
  $(".viewmore").live("click", function() {
    var classname = $(this).attr("value");
    $("." + classname).removeClass("hidden");
    $(this).addClass("hidden");
  });

  var groupBy = function(array, predicate) {
    var grouped = {};
    var orderedGroup = {};
    for (var i = 0; i < array.length; i++) {
      var groupKey = predicate(array[i]);
      if (typeof(grouped[groupKey]) === "undefined"){
    	  grouped[groupKey] = [];
      }
      
      grouped[groupKey].push(array[i]);
    }
    if(grouped.location!=null  &&  grouped.location.length>0){
 	   orderedGroup.location = grouped.location;
    }
   
  return orderedGroup;
  } 
  
  /* P20488 - 1321 changes start */
  var buildSearchBox = function() {
 /*-----START CHANGES P19791a Exchange August 2013-----*/
		//Load the default zip code if the site id is QualifiedHealthPlanDoctors 's zipCode
	  /*-- START CHANGES P8551c QHP_IVL PCR - n204189 --*/
		var qhpZip = $.getUrlVar('externalZipCode');
		/*-- END CHANGES P8551c QHP_IVL PCR - n204189 --*/
		var stateToBePrefilled=$('#stateToBePrefilled').html();
		if(stateToBePrefilled!=null && trim(stateToBePrefilled) != "" && qhpZip!= null && qhpZip != ""){	
		if(qhpZip.indexOf("#")>0)
		   qhpZip = qhpZip.substring(0,qhpZip.indexOf("#"));
			return '<div class="hl-autocomplete-location-box">' +
		      '<div class="hl-autocomplete-locationbar">' +
		      '<input style="font-style: normal;color: rgb(0, 0, 0);" id="hl-autocomplete-search-location" title="hl-autocomplete-search-location" type="text" class="hl-searchbar-input-location"  name= "r" value='+ 
		      qhpZip +
		      ' onfocus="javascript:changeFormatGeoLocation();"/>' +
		      '</div>' +
		      '</div>';
		}
		/*-----END CHANGES P19791a Exchange August 2013-----*/
	else{

    return '<div class="hl-autocomplete-location-box">' +
            '<div class="hl-autocomplete-locationbar">' +
            '<input id="hl-autocomplete-search-location" title="hl-autocomplete-search-location" type="text" class="hl-searchbar-input-location"  name= "r" value="'+ghostTextWhereBox+'" onblur="javascript:addGhostGeoText();" onfocus="javascript:changeFormatGeoLocation();"/>' +
            '</div>' +
            '</div>';
	}
  }
/* P20488 - 1321 changes end */

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
        data.push({label: v["result"],url: v["url"], category: v["type"], subcategory: v["subtype"], aetnaid: v["aetnaid"], lastname: v["lastname"], firstname: v["firstname"], zipcode: v["zipcode"], coordinates: v["coordinates"], stateabbr: v["stateabbr"]});
      });
      /*-- END CHANGES P20751b ACO Branding - n596307 --*/
    });
    return data;
  }

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
                ul.append('<a class="viewmore" href="javaScript:void(0);" value="' + currentCategory + '">' + morenum + ' more Locations</a>');
              }
              isviewmore = false;
            }

            if(index==0){
            	//var liToAdd = "<li class='ui-autocomplete-category topSpacing'>" + 'Locations:' + "</li>";
            	var liToAdd = "<li class='ui-autocomplete-category topSpacing'></li>"; 
            	ul.append(liToAdd);
            }else{
            	//var liToAdd = "<li class='ui-autocomplete-category borderCategory'>" + 'Locations:' + "</li>";
            	var liToAdd = "<li class='ui-autocomplete-category borderCategory'></li>";
            	ul.append(liToAdd);
            }
            
            currentCategory = item.category;

          }

          self._renderItem(ul, item, maxnum, index);
          if (index == (items.length - 1) && index >= maxnum) {
            ul.append('<a class="viewmore" href="javaScript:void(0);" value="' + currentCategory + '">' + (index - maxnum + 1) + ' more Locations</a>');
          }
          
        });
      },
      _renderItem : function(ul, item, maxnum, index) {
        if (typeof item.label != "undefined") {
          //highlights typed
/* P20488 - 1321 changes start */
          item.label = item.label.replace(new RegExp("(?![^&;]+;)(?!<[^<>]*)(" + $.ui.autocomplete.escapeRegex(this.term) + ")(?![^<>]*>)(?![^&;]+;)(.*)", "gi"), "<strong>$1</strong>$2");
/* P20488 - 1321 changes end */
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
    $("#hl-autocomplete-search-location").catcomplete({
      delay: 10,
      source: function(request, response) {
        $.ajax({
          url: $("#typeAheadLocationURL").html().replace( /\&amp;/g, '&' ),
          dataType: "jsonp",
          data: {
            "q": request.term,
            "wherebox": 1
          },
          success: function(xmlResponse) {
            if (request.term !== $("#hl-autocomplete-search-location").val()) {
              return;
            }
            var categorydata = buildResultBox(xmlResponse["data"]);
            /*-- START CHANGES P20751b ACO Branding - n596307 --*/
            hlStatusCodeFirstWhereBox = xmlResponse["meta"].code;
            /*-- END CHANGES P20751b ACO Branding - n596307 --*/
            response($.map(categorydata, function(item) {
              return {
                label: item.label,
                url: item.url,
                /*-- START CHANGES P20751b ACO Branding - n596307 --*/
                subcategory: item.subcategory,
                /*-- END CHANGES P20751b ACO Branding - n596307 --*/
                zipcode: item.zipcode,
                coordinates: item.coordinates,
                stateabbr: item.stateabbr
              }
            }));
        	/* START CHANGES P24698a MAY-2016- N709197 --*/
            if(categorydata[0] != undefined && categorydata[0] != null){
            	if(categorydata[0].subcategory == undefined || categorydata[0].subcategory == null || categorydata[0].subcategory == "" || categorydata[0].subcategory == 'city'){
            		$('#quickStateCodeFromFirstHLCall').val('');
            		$('#quickZipCodeFromFirstHLCall').val(categorydata[0].zipcode);
            	}else if(categorydata[0].subcategory == 'state'){
            		$('#quickZipCodeFromFirstHLCall').val('');
            		$('#quickStateCodeFromFirstHLCall').val(categorydata[0].stateabbr);
            	}
            }
            /* END CHANGES P24698a MAY-2016- N709197 --*/
          },
          /*-- START CHANGES P20751b ACO Branding - n596307 --*/
          error: function(XMLHttpRequest, status, error) {	
        	  var err = eval("(" + XMLHttpRequest.responseText + ")");
        	  $("#healthLineErrorMessage").val(err.Message);
          }
          /*-- END CHANGES P20751b ACO Branding - n596307 --*/
        });
      },

      minLength: 1,
      focus: function(event, ui) {
        var item = ui.item;
        if (item.hidden) {
          $(".viewmore").click();

        }
      },
      select:function(event, ui) {
	      $("#hl-autocomplete-search-location").val(ui.item.value);
	      $("#geoMainTypeAheadLastQuickSelectedVal").val(ui.item.value);
	      /*-- START CHANGES P20751b ACO Branding - n596307 --*/
	      $('#QuickGeoType').val(ui.item.subcategory);
	      /*-- END CHANGES P20751b ACO Branding - n596307 --*/
		  $('#QuickZipcode').val(ui.item.zipcode);
	      $('#QuickCoordinates').val(ui.item.coordinates);
	      $('#stateCode').val(ui.item.stateabbr);
	      $('#geoBoxSearch').val('true');
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
    });
}


  $(function() {
    $(".hl-autocomplete-location-textBox").append(buildSearchBox());
/*-- Start changes SR1347 Sep2014 - N204183 --*/
    var stateToBePrefilled=$('#stateToBePrefilled').html();
	if(stateToBePrefilled!=null && trim(stateToBePrefilled) != ""){
    prefillExternalSearchTypeAndGeoSearch();
	}
    /*-- End changes SR1347 Sep2014 - N204183 --*/
    prePopulateZipForSecure();
/*-- START CHANGES P20751 - PDI Removal - n596307 --*/
    if(urlProtocol == urlProtocolSecure){
    	prefillExternalPCPDTypeForSecure();
    }
    /*-- END CHANGES P20751 - PDI Removal - n596307 --*/
    resetData();
//  Changes to emulate click functionality and prevent form submitting when Enter key is pressed.
// Start    
     $('#hl-autocomplete-search-location').bind('keydown',function(event) {
     	if(event.which == 13) {
     		event.preventDefault();
     		var str = $('#hl-autocomplete-search-location').val();
     		str = trim(str);
     		$('#hl-autocomplete-search-location').val(str);
     		if($('#hl-autocomplete-search-location').val()){
			$(".ui-autocomplete").hide();
			$('#hl-autocomplete-search-location').blur();
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