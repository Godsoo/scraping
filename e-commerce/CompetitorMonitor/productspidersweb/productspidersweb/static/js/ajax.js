/*
 * @require: jQuery Library
 */

// -- AJAX -- //
var Ajax = new Function();

// Send
// m:method, u:url, p:params, c:callback, a:async?
Ajax.send_ajax = function(m, u, p, c, a){
    if (m != 'GET') {
		var request = $.ajax({
		    type: 'POST',
		    url: u,
		    data: $.param(p),
		    complete: c,
		    async: a,
		    headers: {
			'X-CSRFToken': getCookie('csrftoken')
		    }
		});
	} else {
		var request = $.ajax({
		    type: 'GET',
		    url: u,
		    complete: c,
		    async: a
		});
    }
}

// Eval request
Ajax.eval_request = function(response){
    if (response.status == 500) {
    	alert('An error has ocurred<br />Message: '+response.responseText);
    	return -1;
    } else if (response.status == 404) {
    	alert('Not found');
    	return 1;
    } else if (response.status == 200) {
    	// alert('OK');
        return 0;
    } else {
    	alert('ERROR: server has returned: ' + response.responseText);
    	return -1;
    }
}

// -- CSRF Token functions -- //
function getCookie(name) {
    var cookieValue = null;
    if (document.cookie && document.cookie != '') {
        var cookies = document.cookie.split(';');
        for (var i = 0; i < cookies.length; i++) {
            var cookie = $.trim(cookies[i]);
            // Does this cookie string begin with the name we want?
            if (cookie.substring(0, name.length + 1) == (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

function sameOrigin(url) {
    // url could be relative or scheme relative or absolute
    var host = document.location.host; // host + port
    var protocol = document.location.protocol;
    var sr_origin = '//' + host;
    var origin = protocol + sr_origin;
    // Allow absolute or scheme relative URLs to same origin
    return (url == origin || url.slice(0, origin.length + 1) == origin + '/') ||
        (url == sr_origin || url.slice(0, sr_origin.length + 1) == sr_origin + '/') ||
        // or any other URL that isn't scheme relative or absolute i.e relative.
        !(/^(\/\/|http:|https:).*/.test(url));
}

function safeMethod(method) {
    return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
}
