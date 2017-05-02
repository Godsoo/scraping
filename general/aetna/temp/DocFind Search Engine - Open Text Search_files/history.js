/*
 * This file provides the functionality to do history in DSE (back and forward buttons).
 * It uses the technique of different #hash values at the end of the URL to keep track of
 * history without leaving the page.  A monitor periodically checks if this value has
 * changed and signals an event.
 */

// the following are low-level functions to handle hash value changes

// this is needed because different browsers support location.hash differently
function get_hash() {
	var url = window.location + '';
	var inx = url.indexOf('#');
	if (inx >= 0) {
		var hash = url.substr(inx+1, url.length);
		return hash;
	} else {
		return '';
	}
	
}

var current_hash = get_hash();
var hashInterval;  // the timer
var restoringPage = false;  // in the middle of restoring a page

function check_hash() {
//	clearInterval(hashInterval);
	if ( get_hash() !== current_hash ) {
//		alert('page changed');
		current_hash = get_hash();
		page_change( current_hash );
	}
//	hashInterval = setInterval( "check_hash()", 100 );
}


function set_hash( new_hash ) {
	if (new_hash === get_hash()) {
//		alert('dont set hash: \n' + new_hash + '\n' + get_hash());
	} else if (restoringPage) {
//		alert('restoring page - no change');
	} else {
//		alert('set hash: \n' + new_hash + '\n' + get_hash());
		current_hash = new_hash
		window.location.hash = new_hash;
	}
//	var urlParts = (window.location + '').split('#');
//	var newURL = urlParts[0] + '#' + new_hash;
//	window.location = newURL;
}

// this simulates publish/subscribe pattern using jquery

var topics = {};

jQuery.Topic = function( id ) {
	var callbacks,
		method,
		topic = id && topics[ id ];
		if ( !topic ) {
			callbacks = jQuery.Callbacks();
			topic = {
				publish: callbacks.fire,
				subscribe: callbacks.add,
				unsubscribe: callbacks.remove
			};
			if ( id ) {
				topics[ id ] = topic;
			}
		}
		return topic;
	};

/*
 * The following topics can be monitored
 * - savePage
 * - restorePage
 * 
 * A function that gets called with savePage will be passed a page object.
 * This object is used to store name/value strings.  Anyone monitoring for the
 * savePage method can determine information on the page that should be saved
 * so that the page can be recreated later.  Values must be strings, and they can be
 * hidden fields, state information, etc.
 * 
 * A function that gets called by the restorePage event will be passed a page object.
 * That function is expected to return the page to the state that it was when it was
 * saved.  More than one function can monitor for this event.  Restoring a page may
 * include restoring input fields, restoring state variables, and doing ajax calls.
 * This function will be passed the new page object as well as the old
 * page object.  This will allow the function to know what is already on
 * the existing page and determine what (if anything) is needed to update
 * the page to the new state.  If there is no old page object, this means
 * that the user has gont to a completely different website and then went
 * back to this one, so the entire page needs to be restored.
 * 
 * When a page is ready to be saved (after a search or something the user did)
 * the markPage function is called.
 */

/*
 * start the page change processing
 */
function startChangeHandler() {
//	alert('startChangeHandler: ' + get_hash());
	currentHash = get_hash();  // no change yet
	page_change(currentHash);  // initial change
	hashInterval = setInterval( "check_hash()", 100 );
}

/*
 * Mark the page, meaning it is one that can be returned to
 * A reason can be passed to it, indicating why the page was marked.  This could make
 * it easier when restoring the page, knowing the last thing the user did.
 */
function markPage(reason) {
//	alert('markPage: ' + reason);
	var page = {};  // holds state information
	page.markPage = reason;
	$.Topic( "savePage" ).publish( page );  // everyone saves the state of the page

	// make the hash for this page
	var hash = makeHash(page);

//Start Code added to test the customization
//test for hash code
var url = window.location + '';
	var hashIndex = url.indexOf('#');

	//if hash exists then check to see if the character before it is an &.
	//if it's not then add it.
	/* if( hashIndex > 0 )
	{
		//test for presence of & character prior to the hash
		var amperIndex = url.substring(hashIndex-1, hashIndex);
		//alert( amperIndex );
		if ( amperIndex != "&" )
		{	
			var hashFix = "&";

			//test for presence of query string
			var queryIndex = url.indexOf('?');
			if( queryIndex < 0 )
			{
				hashFix = "?&";
			}

			var baseurl = url.substring(0, hashIndex);
			//alert(baseurl);
			var hashurl = url.substring(hashIndex);
			//alert(hashurl);
			window.location.replace( baseurl + hashFix + hashurl );
			
		}
	} */

//End Code added to test Customization
//	alert('hash from saved page: ' + hash);
	
	// before setting the new hash, record the previous page's state.  This will let
	// us pass that in to functions that need to update the state of the page
	var oldHash = get_hash();
	var inx = oldHash.indexOf('#');
	if (inx >= 0) {
		oldHash = oldHash.substr(inx+1, oldHash.length);
	}
	
	// change the URL to reflect the marked page object
	set_hash(hash);
}

/*
 * make the part of the url after the hash (#) from information in the page object
 */
function makeHash(page) {
	var url = "";  // the part of the URL after the hash
	for(var name in page) {
		var value = escape(page[name]);
		url += name + '=' + value + '&';
	}
	return url.substring(0,url.length-1);  // remove trailing &
}

/*
 * make the page object from the part of the URL after the hash
*/
function makePage(hash) {
	if (hash.length == 0) {
		return null;  // no hash, no state
	}

	page = {};  // page state object
	var parms = hash.split('&');

	for (var i = 0; i < parms.length; i++) {
		var parm = parms[i].split('=');
		var name = parm[0];
		var value = unescape(parm[1]);
		page[name] = value;
	}

	return page;
}

function page_change( hash ) {
	restoringPage = true;  // no hash change allowed while restoring a page
//	alert('page_change: ' + hash);
	var inx = hash.indexOf('#');
	var page = makePage(hash);
//	alert('publish restorePage');
	$.Topic( "restorePage" ).publish( page );  // everyone restores page to this state
	restoringPage = false;
}
