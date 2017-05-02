
/*************************************************************************
[Custom_LaunchAgent.js]
 
 Copyright (C) 2009 Next IT Corporation, Inc. Spokane, WA. All Rights Reserved. 
 This document is confidential work and intellectual property of Next IT 
 Corporation. Permission to copy, distribute or use any portion of this file 
 is prohibited without the express written consent of Next IT Corporation.

 Version: 1.0
 Notes:
	This will be included on Aetna's website to launch agent with proper size and location.  
	All additional integration functions are also included.
	Created 9/10/2009 Kate.Beck

*****************************************************************************/
function NIT() { };

NIT.ContextCookieName = "ActiveAgentContext";
NIT.PACookieCurrent = "CurrentPage";
NIT.PACookiePrevious = "PreviousPage";
NIT.PACookieChildWindow = "ChildWindowPage";
NIT.UTCookieUserType = "UserType";
NIT.PAMainWindow = false;
NIT.AgentLaunchTypeRelaunch = "relaunch";
NIT.AgentLaunchTypeInitial = "initial";
NIT.AgentUrl = "";
NIT.AgentWindowName = "aetnaAgent";
NIT.AgentLaunchCookieName = "ActiveAgentLaunch";
NIT.AgentReLaunchKey = "RelaunchParam";
NIT.StartRegFromFloat = "StartRegFromFloat";
NIT.CostBenefitsSearchCookieName = "CostBenefitsSearch";
NIT.CostLaunchMemberIndex = "costLaunchMemberIndex";
NIT.CostLaunchSearchTerm = "costLaunchSearchTerm";
//List of pages listening for cookie navigation
NIT.CookieNavListenerPageList = [
    'docfind',
    'docfindse',
    'hospitaldetailspublicdocfind',
    'facilitydetailspublicdocfind',
    'providerdetailspublicdocfind',
    'publicdocfindresults',
    'publicdocfindse',
    'hospitaldetailsdocfind',
    'facilitydetailsdocfind',
    'providerdetailsdocfind',
    'docfindresults',
	'expublicdocfindse',
	'expublicdocfindresults',
	'exproviderdetailspublicdocfind',
	'exfacilitydetailspublicdocfind',
	'exhospitaldetailspublicdocfind',
    'ivlpublicdocfindse',
    'ivlpublicdocfindresults',
    'ivlproviderdetailspublicdocfind',
    'ivlfacilitydetailspublicdocfind',
    'ivlhospitaldetailspublicdocfind'
];

//#region NIT functions for Aetna
//Set Current Page.
NIT.SetPACookie = function (pageValue) {
    var paCookieValues = "";
    var previousPageValue = "";
    NIT.PAMainWindow = false;

    //check for cookie
    var paCookie = NIT.GetCookie(NIT.ContextCookieName);

    if (paCookie == undefined) {
        NIT.PAMainWindow = true;
    }
    else {
        if (paCookie.Values[NIT.PACookieCurrent] == "") {
            NIT.PAMainWindow = true;
        }
    }
    //override this so code works in FF for now due to onunload bug
    //NIT.PAMainWindow = true;  //took out 2/3/2010 for Feb 13th deploy with Aetna's fixes.
    if (NIT.PAMainWindow) {
        //if exists, just update CurrentPage value
        if (paCookie != undefined) {
            paCookie.Values[NIT.PACookieCurrent] = pageValue;
        }
        else {
            //if doesn't exists create new cookie
            paCookieValues += NIT.PACookieCurrent + "=" + pageValue + "&";
            paCookieValues += NIT.PACookiePrevious + "=" + previousPageValue + "&";
            paCookieValues += NIT.PACookieChildWindow + "=";
            paCookie = new NIT.Cookie(NIT.ContextCookieName, paCookieValues);
        }
        paCookie.Save();
    }
    //JIRA:AET-5519 - If we're on a DocFind page, start polling for nav cookie
    if (NIT.IsCookieNavListenerPage(pageValue)) {
        NIT.CookieCommandPolling.checkCommandCookie();
    }
}


//JIRA:AET-5519 - Only listening for cookie navigation on certain pages
NIT.IsCookieNavListenerPage = function (pageValue)
{
    var val = pageValue.toLowerCase();
    for (var i = 0; i < NIT.CookieNavListenerPageList.length; i++)
    {
        if (val == NIT.CookieNavListenerPageList[i])
        {
            return true;
        }
    }
    return false;
}

NIT.SetPACookieTab = function(pageValue)
{
    //AET-84 set PA value on tab, so just check if main window since pa logic has already run.
    if (NIT.PAMainWindow)
    {
        //check for cookie
        var paCookie = NIT.GetCookie(NIT.ContextCookieName);
        
        //if exists, just update CurrentPage value
        if (paCookie != undefined)
        {
            var oldCurrentPageValue = paCookie.Values[NIT.PACookieCurrent];
            paCookie.Values[NIT.PACookieCurrent] = pageValue;
            paCookie.Values[NIT.PACookiePrevious] = oldCurrentPageValue;
            paCookie.Save();
        }
    }
}

NIT.SetPACookieChildWindow = function (pageValue) 
{
    if (NIT.PAMainWindow) 
    {
        //check for cookie
        var paCookie = NIT.GetCookie(NIT.ContextCookieName);

        //if exists, update just ChildWindowPage value
        if (paCookie != undefined) 
        {
            paCookie.Values[NIT.PACookieChildWindow] = pageValue;
            paCookie.Save();
        }
    }
}

//Put CurrentPage in PreviousPage value and clear CurrentPage.
NIT.ClearPACookie = function()
{
    //first check if this is the main PA window
    if (NIT.PAMainWindow)
    {
        var paCookieValues = "";
        var oldCurrentPageValue = "";

        //check for cookie
        var paCookie = NIT.GetCookie(NIT.ContextCookieName);
        if (paCookie != undefined)
        {
            oldCurrentPageValue = paCookie.Values[NIT.PACookieCurrent];
            paCookie.Values[NIT.PACookieCurrent] = '';
            paCookie.Values[NIT.PACookiePrevious] = oldCurrentPageValue;
        }
        else
        {
            paCookieValues += NIT.PACookieCurrent + "=&";
            paCookieValues += NIT.PACookiePrevious + "=" + oldCurrentPageValue + "&";
            paCookieValues += NIT.PACookieChildWindow + "=";
            paCookie = new NIT.Cookie(NIT.ContextCookieName, paCookieValues);
        } 
        paCookie.Save();
    }
}

NIT.ClearPACookieChildWindow = function () 
{
    if (NIT.PAMainWindow) 
    {
        //check for cookie
        var paCookie = NIT.GetCookie(NIT.ContextCookieName);
        if (paCookie != undefined)
        {
            paCookie.Values[NIT.PACookieChildWindow] = '';
            paCookie.Save();
        }

    }
}

NIT.GetCurrentPage = function()
{
    var currentPage = '';

    var contextCookie = NIT.GetCookie(NIT.ContextCookieName);
    if (contextCookie != undefined)
    {
        //get CurrentPage value
        if (contextCookie.Values[NIT.PACookieCurrent] != null)
        {
            currentPage = contextCookie.Values[NIT.PACookieCurrent];
        }
    }
    return currentPage;
}

NIT.SetUserType = function (userType)
{
	//check for cookie
	var userCookie = NIT.GetCookie(NIT.ContextCookieName);
	var userCookieValue = NIT.UTCookieUserType + "=" + userType;
	//if exists, just update UserType value
	if (userCookie != undefined)
	{
		userCookie.Values[NIT.UTCookieUserType] = userType;
	}
	else
	{  //if doesn't exists create new cookie
		userCookie = new NIT.Cookie(NIT.ContextCookieName, userCookieValue);
	}
	userCookie.Save();
}

NIT.SetCostBenefitsMemberIndex = function (memberIndex)
{
	var costBenefitsSearchCookie = NIT.GetCookie(NIT.CostBenefitsSearchCookieName);
	var costBenefitsMemberIndex = NIT.CostLaunchMemberIndex + "=" + memberIndex;
	if (costBenefitsSearchCookie != undefined)
	{
		costBenefitsSearchCookie.Values[NIT.CostLaunchMemberIndex] = memberIndex;
	}
	else
	{
		costBenefitsSearchCookie = new NIT.Cookie(NIT.CostBenefitsSearchCookieName, costBenefitsMemberIndex);
	}
	costBenefitsSearchCookie.Save();
}

NIT.SetCostBenefitsSearchTerm = function (searchTerm)
{
	var costBenefitsSearchCookie = NIT.GetCookie(NIT.CostBenefitsSearchCookieName);
	var costBenefitsSearchTerm = NIT.CostLaunchSearchTerm + "=" + searchTerm;
	if (costBenefitsSearchCookie != undefined)
	{
		costBenefitsSearchCookie.Values[NIT.CostLaunchSearchTerm] = searchTerm;
	}
	else
	{
		costBenefitsSearchCookie = new NIT.Cookie(NIT.CostBenefitsSearchCookieName, costBenefitsSearchTerm);
	}
	costBenefitsSearchCookie.Save();
}

NIT.SendAppEvent = function(win, appEventValue)
{
    if (appEventValue != undefined && appEventValue != "")
    {
        try
        {
            win.NIT.SendAppEvent(appEventValue);
        } //if can't access the other directly then send through the cookie (i.e. for MPE frame which is a different subdomain).
        catch (e)
        {
            //set cookie value.
            NIT.SetRelaunchCookie(appEventValue);            
        }        
    }
}

NIT.SendQuestion = function(win, question, launchPointParameter)
{
    if (question != undefined && question != "")
        win.NIT.SendQuestion(question, launchPointParameter)
}

NIT.SetRelaunchCookie = function(appEventValue)
{
    //set cookie that AA is polling for with the re-launch param.
    var launchCookie = NIT.GetCookie(NIT.AgentLaunchCookieName);
    launchCookie.Values[NIT.AgentReLaunchKey] = encodeURIComponent(appEventValue);
    launchCookie.Save();
}

//check if the Agent has been opened already (agent sets a cookie on initialization)
//used for frames (since they are in a different subdomain and safari and chrome fail on the window.open logic
NIT.AgentOpen = function()
{
    var launchCookie = NIT.GetCookie(NIT.AgentLaunchCookieName);
    if(launchCookie != undefined)
    {
        return true;
    }
    else
    {
        return false;
    }
}

//AET-76
NIT.AppendWebTrendsParameters = function(url, launchParameter)
{
    var queryStr = url.indexOf("?");
    var returnUrl = url + (queryStr == -1 ? "?" : "&");
    returnUrl += "LaunchParameter=" + launchParameter + "&Page=" + NIT.GetCurrentPage();

    return returnUrl;
}
//append all the appropriate querystring values to the inital launch url
NIT.InitialLaunchUrl = function (url, appEventValue, launchQuestion)
{
	//append launch param even though web trends does.  this is case web trends needs to be turned off.
	url += "?" + NIT.AgentLaunchTypeInitial + "=" + appEventValue;
	url = NIT.AppendWebTrendsParameters(url, appEventValue);   //AET-76
	//include question in querystring
	if (launchQuestion != '')
	{
		// AET-6234: This is a hack to get around the SiteMinder CSS issue
		launchQuestion = launchQuestion.replace(/'/g, '`').replace(/</g, '~[').replace(/>/g, ']~');
		url += '&question=' + encodeURIComponent(launchQuestion);
	}
	//check if we are launch from a frame
	if (window.top != window.self)
	{
		url += '&resize=true';  //since frame is different subdomain, we need agent to resize 
	}

	return url;
}

//#endregion  //NIT functions for Aetna

//#region Launch

NIT.LaunchAgentCostBenefitsSearch = function (url, memberIndex, launchParam, searchTerm)
{
	NIT.SetCostBenefitsMemberIndex(memberIndex);
	NIT.SetCostBenefitsSearchTerm(searchTerm);

	NIT.LaunchAgent(url, launchParam);
}

//This is the core version, included all here so Aetna wouldn't have to reference 2 files for launch (since LaunchChildWindow is overridden)  
//Also added agent window name and slimmed down launch functions that include appropriate parameters.
NIT.LaunchAgent = function(agentLocation, launchValue, launchQuestion)
{
    var options = 'scrollbars=no,menubar=no,resizable=yes,location=no,status=yes,titlebar=no,toolbar=no';
    NIT.AgentUrl = agentLocation;
    launchValue = (launchValue) ? launchValue : '';
    if (launchQuestion)
    {
        //limit the input to 200 chars.
        launchQuestion = launchQuestion.substring(0, 200);
    }
    else
    {        launchQuestion = '';
    }
    
    //Agent window width/height and parent window width/height must match popupsettings control in agent.aspx
    var win = PopupScript.LaunchChildWindow(agentLocation, launchValue, launchQuestion, NIT.AgentWindowName, 'right', 300, 695, 38, 0, true, 1024, 768, options);
}

function PopupScript() { };
PopupScript.Version = '6.2';
PopupScript.ApplyParentTop = false; // By default, parent top does not match popup window
PopupScript.PerfectWindowSize = true; // By default, we size by content only and allow window overlap

//Overrode core popup script to include Aetna specific changes such as window name and launchValue
//////////////////////////////////////
// Opens popup window and sizes parent window accordingly
//////////////////////////////////////
PopupScript.LaunchChildWindow = function(url, appEventValue, launchQuestion, agentWindowName, align, width, height, top, left, layoutParent, parentWidth, parentHeight, options)
{
    align = (!align || align.toLowerCase() != 'left') ? 'right' : 'left'; // Default to right if not 'left'
    width = (width) ? width : 250; // Default width: 250px
    height = (height) ? height : '100%'; // Default height: 100%
    top = (top) ? top : 0; // Default top: 0px
    left = (left) ? left : 0; // Default left: 0px
    layoutParent = (layoutParent) ? true : false;
    parentWidth = (parentWidth) ? parentWidth : '100%'; // Default height: 100%
    parentHeight = (parentHeight) ? parentHeight : '100%'; // Default height: 100%
    options = (options) ? options : 'scrollbars=no,menubar=no,resizable=no,location=no,status=yes,titlebar=no,toolbar=no';

    // Make sure they're numeric (Convert from percentages
    width = PopupScript.WidthToScreen(width);
    height = PopupScript.HeightToScreen(height, top);
    top = PopupScript.WidthToScreen(top);
    left = PopupScript.HeightToScreen(left, top);
    parentWidth = PopupScript.WidthToScreen(parentWidth);
    parentHeight = PopupScript.HeightToScreen(parentHeight, top);

    var parentLeft = (align == 'left') ? width : 0;

    // Parent width not specified or not enough space for parent window and need to shrink to fit
    if (parentWidth <= 0 || parentWidth + width > screen.availWidth)
    {
        parentWidth = screen.availWidth - width; // Must also make parent window fit
    }

    // Parent height not specified or taller than can fit
    if (parentHeight <= 0 || parentHeight > screen.availHeight)
    {
        parentHeight = screen.availHeight; // Must also make parent window fit
    }

    // Agent height is taller than can fit
    if (height + top > screen.availHeight)
    {
        height = screen.availHeight - top; // Must also make agent window fit
    }

    if (align == 'right') // Detect "left" and ignore setting
    {
        left = parentWidth;
    }

    var allOptions = 'width=' + width + 'px,height=' + height + 'px,left=' + left + ',top=' + top + ',' + options;

    //check first if we are re-launching from a frame (since for Aetna they are in a different subdomain 
    //and safari and chrome fail on the normal window.open logic for frames)
    if (window.top != window.self && NIT.AgentOpen())
    {
        //pass re-launch param through a cookie (that agent is polling for)
        NIT.SetRelaunchCookie(appEventValue);            
    }
    else
    {
        //Check to see if there's already a agent window open out there
        var ActiveAgent_AgentWindow = window.open('', agentWindowName, allOptions);

        var win = ActiveAgent_AgentWindow;
        try
        {
            var agentWindowUrl = ActiveAgent_AgentWindow.location.href;
            //we would be able to read the URL as we are in same subdomain
            if (agentWindowUrl != undefined && agentWindowUrl.toLowerCase().indexOf('agent.aspx') < 0)
            {
                //add additional querystring parameters to the url (webtrends, launchparam,etc)
                url = NIT.InitialLaunchUrl(url, appEventValue, launchQuestion);

                win = window.open(url, agentWindowName, allOptions);

                if (win)
                {
                    if (PopupScript.PerfectWindowSize)
                    {
                        // The popup size is for content only, we need to resize to get the size perfect
                        win.resizeTo(width, height);
                        win.moveTo(left, top);
                    }
                    var pTop = (PopupScript.ApplyParentTop) ? top : 0;

                    if (layoutParent)
                        PopupScript.PositionWindow(window, parentWidth, parentHeight, pTop, parentLeft);

                        ActiveAgent_AgentWindow = win;
                    
                    PopupScript.AssignParentWindowName();
                    win.focus();
                    //External call to Aetna Navigator to reset session timer.
                    resetSessTimer();
                }
            }
            else    //window is already open
            {
                if (launchQuestion != '')
                {
                    //call javascript to pass through question
                    NIT.SendQuestion(ActiveAgent_AgentWindow, launchQuestion, appEventValue);
                }
                else
                {
                    //call javascript function to pass through the launch param.
                    NIT.SendAppEvent(ActiveAgent_AgentWindow, appEventValue)
                }
                ActiveAgent_AgentWindow.focus();
            }
        }
        catch (e)
        {
            var message = PopupScript.GetErrorMessage(e);
            if (message.indexOf("denied") != -1)
            {
                if (launchQuestion != '')
                {
                    //call javascript to pass through question
                    NIT.SendQuestion(ActiveAgent_AgentWindow, launchQuestion, appEventValue);
                }
                else
                {
                    //call javascript function to pass through the launch param.
                    NIT.SendAppEvent(ActiveAgent_AgentWindow, appEventValue)
                }
                PopupScript.AssignParentWindowName();
                ActiveAgent_AgentWindow.focus();
            }
        }
        return ActiveAgent_AgentWindow; // Return window reference in case we need to use it
    }
};


//#endregion //Launch

//#region PopupScript

//////////////////////////////////////
// Positions a window according to width/height, top/left (used by LaunchChildWindow)
//////////////////////////////////////
PopupScript.PositionWindow = function(win, width, height, top, left) {
    try {
        win.top.moveTo(0, 0); // This helps it work better when it's maximized... (IE seems to get confused sometimes)
        win.top.resizeTo(width, height);
        win.top.moveTo(left, top);

    }
    catch (e) // Permission denied? Happens if we change out of our domain, we should make sure it doesn't happen in any other situation, or comment out throw below
	{
        // if not permission denied, throw the error
	    if (PopupScript.GetErrorMessage(e).indexOf('denied') == -1) {
            throw e;
        }
    }
};

//////////////////////////////////////
// Converts percentages to pixels to match screen width (ie. 50% -> 600)
//////////////////////////////////////
PopupScript.WidthToScreen = function(w) {
if (!PopupScript.IsNumeric(w) && w.indexOf('%') > -1) {
        w = w.substring(0, w.indexOf('%'));
        w = screen.availWidth * w / 100;
    }
    return parseInt(w);
};
//////////////////////////////////////
// Converts percentages to pixels to match screen height (ie. 50% -> 600)
//////////////////////////////////////
PopupScript.HeightToScreen = function(h, top) {
if (!PopupScript.IsNumeric(h) && h.indexOf('%') > -1) {
        h = h.substring(0, h.indexOf('%'));
        h = (screen.availHeight * h / 100) - top;
    }
    return parseInt(h);
};

//////////////////////////////////////
// General functions
//////////////////////////////////////
PopupScript.IsNumeric = function(o) { return (typeof o == 'number' && isFinite(o)); };
PopupScript.IsWindowClosed = function(win)
{
    var closed = false;
    try // getting around permission problem on closed windows
	{
        closed = (win == null || win.closed || typeof (win.self) == 'undefined'); // Added checking win.self for Safari and browsers that don't support window.closed properly
    }
    catch (e) { closed = true; }
    return closed;
};

PopupScript.GetErrorMessage = function(e)
{
    // NOTE:  Permission Denied does not throw exception for: Safari 3 (Mac and PC), Chrome 1.0
    if (e.message) // IE6, IE7, FF3
        return e.message;
    else // FF1, FF1.5, FF2, FF3
        return e.toString();
};

//////////////////////////////////////
// Parent window association
//////////////////////////////////////
PopupScript.ParentWindowNameCookieName = 'ActiveAgent_ParentWindowName';
PopupScript.ParentWindowNamePrefixAgentAsChild = 'ParentWindowAgentAsChild';

PopupScript.IsAgentAssociatedParentWindow = function ()
{
    var returnValue = false;

    var windowName = window.name;
    var windowNameCookie = NIT.GetCookie(PopupScript.ParentWindowNameCookieName);

    if (windowNameCookie != null)
    {
        var expectedWindowName = windowNameCookie.Value;

        if (expectedWindowName == windowName)
        {
            returnValue = true;
        }
    }

    return returnValue;
}

// Called when Agent is launched, just before refreshing into https
// Sets window.name and ActiveAgent_ParentWindowName cookie
PopupScript.AssignParentWindowName = function ()
{
    var windowName = PopupScript.ParentWindowNamePrefixAgentAsChild + Math.floor(Math.random() * 9000 + 1000);
    window.name = windowName;

    var windowNameCookie = new NIT.Cookie(PopupScript.ParentWindowNameCookieName, windowName);
    windowNameCookie.Save();
};
//#endregion //Popup Script

//#region Cookie code
NIT.Cookie = function(name, sVals, exp)
{
    this.Name = name;
    this.Value = null;
    this.Values = new Object();
    // These three are for saving cookies
    this.Expires = (exp) ? exp : null; // Leave null for session cookie (or if updating cookie)
    this.Path = '/';
    this.Secure = false;
    this.Domain = NIT.GetDomain();

    if (sVals != null) // Parse specified value(s)
    {
        var nvc = (typeof (sVals) == "string") ? sVals.split('&') : null; // Get the name-value collection from the cookie
        if (nvc != null && nvc.length > 0 && sVals.indexOf('=') > -1) {
            for (var i = 0; i < nvc.length; i++) {
                var nv = nvc[i].split('='); // Get the name and value of this entry
                if (nv.length > 1)
                    this.Values[nv[0]] = nvc[i].substr(nv[0].length + 1); //nv[1]; // Add property to our Values (remove the name, since the content may also have '=' characters)
                else if (i == 0)
                    this.Value = nv[0]; // If no equal sign and the first entry, it is the main property

            }
        }
        else // Single value cookie
            this.Value = sVals;
    }

    // Methods
    this.Save = function()
    {
        var v = (this.Value != null) ? this.Value : '';
        for (var n in this.Values) {
            v += '&' + n + '=' + this.Values[n]; //escape(this.Values[n]); // No longer escaped, now matching how .NET does it
        }
        if (v[0] == '&')
            v = v.substr(1);

        var me = this.Name + '=' + v +
			((this.Expires == null) ? "" : ("; expires=" + this.Expires.toGMTString())) +
			"; path=" + escape(this.Path) +
			((this.Domain == null) ? "" : ("; domain=" + this.Domain)) +
			((this.Secure) ? "; secure;" : ";");
        document.cookie = me;
    };

    this.Delete = function()
    {
        this.Expires = new Date(1970, 1, 2); // "Fri, 02-Jan-1970 00:00:00 GMT" );
        this.Save();
    };
};

NIT.GetCookies=function() // Parses all available cookies
{
    var all=new Object();
    if(document.cookie!="")
    {
        var cookies=document.cookie.split("; ");
        for(i=0;i<cookies.length;i++)
        {
            var c=cookies[i];
            var idx=c.indexOf('=');
            var n;
            if(idx>0)
            {
                //not found
                n=c.substr(0,idx);
            }
            else
            {
                //use the entire cookie as the name
                idx = c.length;
                n = c;
            }

            var v;
            if(c.length>idx+1) // Not an empty value (just in case)
                v=c.substring(idx+1,c.length); //unescape( c.substring(idx+1, c.length) ); // No longer escaped, now matching how .NET does it
            else
            {
                v = '';
            }
            all[n]=new NIT.Cookie(n,v);
        }
    }
    return all;
};

NIT.GetCookie = function(name) // Selects a cookie by name
{
    return NIT.GetCookies()[name];
};

NIT.ShowCookies = function()
{
    var cookies = NIT.GetCookies();
    var sCookie = 'COOKIES:\n';
    for (var crumb in cookies) {
        sCookie += "\n" + 'Name: ' + cookies[crumb].Name + '\n';
        sCookie += 'Value: ' + cookies[crumb].Value + '\n';
        // now show Values array for the current crumb
        for (var values in cookies[crumb].Values) {
            sCookie += "    " + values + ": ";
            sCookie += cookies[crumb].Values[values] + "\n";
        }
    }
    alert(sCookie);
}

NIT.GetDomain = function()
{
    var url = document.domain;
    var end = "";
    var s = url.indexOf('.');

    if (url.indexOf('.') > -1) {
        end = url.substr(url.lastIndexOf('.'));
        url = url.substring(0, url.lastIndexOf('.'));
    }
    if (url.indexOf('.') > -1) {
        url = url.substr(url.lastIndexOf('.') + 1);
    }
    url = url + end;
    if (url.indexOf('.') == -1) {
        url = null;
    }

    if (url && (/^[0-9]+.[0-9]+$/g).test(url)) // Fix for when we're referencing by IP address
        return null;

    return url;
};
//#endregion //Cookie Code

// BEGIN Floating Launch Point

// Detect url of this script to make our service relative to the script and not the page Agent is running from (required for Embedded)
NIT.scriptSource = '';

try // Must be in a try-catch, or intellisense breaks (since this errors during that processing)
{
    NIT.scriptSource = (function ()
    {
        var scriptTags = document.getElementsByTagName('script');
        var script = scriptTags[scriptTags.length - 1];

        if (script.getAttribute.length !== undefined)
        {
            return script.src;
        }

        return script.getAttribute('src', -1)
    } ());
}
catch (e) { }

NIT.imagesURL = NIT.scriptSource.substr(0, NIT.scriptSource.lastIndexOf('/') + 1) + '../images/';

NIT.checkFloatingLaunchPoint = function()
{
    var launchCookie = NIT.GetCookie("ActiveAgentLaunch");
    var agentLaunched = false;
    if (launchCookie && launchCookie.Values && launchCookie.Values['Launched'] == 'true')
        agentLaunched = true;

    var currentPage = NIT.GetCurrentPage();
    if (currentPage == 'RegPersonalInfoPage' && NIT.getQueryValue('AnnHelp') == 'T')
    {
        if (agentLaunched)
        {
            NIT.LaunchAgent(annUrl, NIT.StartRegFromFloat, '');
        }
        else
        {
            NIT.showFloatingLaunchPoint();
        }
    }
};

NIT.getQueryValue = function (key)
{
    var nvString = window.location.search.substring(1);
    return NIT.parseKey(key, nvString);
};

NIT.parseKey = function (key, nvString)
{
    var vars = nvString.split("&");
    for (var i = 0; i < vars.length; i++)
    {
        var pair = vars[i].split("=");
        if (pair[0] == key)
            return decodeURIComponent(pair[1]);
    }
    return null;
};

NIT.showFloatingLaunchPoint = function ()
{
    // attempt to request the image early so it's there when the flyout gets shown
    new Image().src = NIT.imagesURL + "ann_window.png";

    if (typeof jQuery != 'undefined') //Don't allow floating launch point functionality unless jQuery is loaded
    {
        var outerDivWidth = 301;
        var outerDivHeight = 529;

        var launchPointImg = $("#annNoError");
        var navBar = $("#nav");

        // default position values
        var left = 0
        var top = 143;

        // calculate left offset in case the launch image isn't found
        if ($(window).width() <= 984) left = 978 - outerDivWidth;
        else left = $(window).width() - (($(window).width() - 984) / 2) - outerDivWidth;

        if (launchPointImg.length > 0) // launchPointImg is always there, just not set to show all the time
        {
            // if there's a launch point image, line up with it
            left = launchPointImg.offset().left + launchPointImg.width() - outerDivWidth;
            top = launchPointImg.offset().top;
        }
        else if (navBar.length > 0)
        {
            left = navBar.offset().left + navBar.width() - outerDivWidth;
            top = navBar.offset().top + navBar.height();
        }

        var annOverlay = document.createElement("div");
        annOverlay.setAttribute("id", "ann_overlay");
        annOverlay.style.width = outerDivWidth + "px";
        annOverlay.style.height = outerDivHeight + "px";
        annOverlay.style.position = "absolute";
        annOverlay.style.display = "none";
        annOverlay.style.top = top + "px";
        annOverlay.style.left = left + "px";
        annOverlay.style.zIndex = "9";
        annOverlay.style.textAlign = "left";
        annOverlay.style.backgroundImage = "url(" + NIT.imagesURL + "ann_window.png)";

        var initialQuestion = "($('#floatingLaunchPointTextArea').val() != 'Type your question here.' ? $('#floatingLaunchPointTextArea').val() : '')";
        var launchAnn = "NIT.LaunchAgent(annUrl, '" + NIT.StartRegFromFloat + "', " + initialQuestion + ");NIT.hideFloatingLaunchPoint();";
        var annClose = "<div id=\"ann_close\" style=\"width:45px; height:17px; position:absolute; top:16px; right:18px; cursor:pointer; z-index:11;\"\
        onclick=\"NIT.hideFloatingLaunchPoint();\"></div>";
        var annChatHistory = "<div id=\"ann_chathistory\" style=\"width:254px; height:192px; position:absolute; top:198px; left:25px; \
        font-family:Arial, Helvetica, sans-serif; font-size:12px; line-height:18px; color:#4d4c4c; overflow:auto; z-index:10;\"> \
        <span style=\"color:#002776; font-weight:bold; z-index:10;\">Ann:</span> Hi, I&rsquo;m Ann, your Aetna  Virtual Assistant. \
        Thank you for requesting my help to register on the Aetna member website. To get started, just click the \
        &ldquo;Start Registration&rdquo; link or you can ask me a question below: \
        <br /><br /><a href=\"#\" style=\"color:#005ca1; padding-left:15px; z-index:10;\" \
        onmouseover=\"this.style.textDecoration='none';\" \
        onmouseout=\"this.style.textDecoration='underline'\" \
        onclick=\"" + launchAnn + "\">Start Registration</a></div>";


        var annInput = "<div id=\"ann_input\" style=\"width:260px; height:30px; position:absolute; top:426px; left:20px; z-index:10;\"> \
                <textarea name=\"textarea\" id=\"floatingLaunchPointTextArea\" \
                style=\"width:260px; height:30px; border:0px solid #fff; font-family:Arial, Helvetica, sans-serif; \
                font-size:12px; color:#666; overflow:auto; background-color:transparent;\" \
                onkeypress=\"NIT.checkAgentSubmit(event);\" \
                onfocus=\"if (this.value.indexOf('Type your question here.') > -1){ this.value = ''; this.style.color = '#000';}\" \
                onblur=\"if (this.value == '') { this.value = 'Type your question here.'; this.style.color = '#666';}\">Type your question here.</textarea></div>";
        var annButton = "<div id=\"ann_button\" style=\"width:105px; height:28px; position:absolute; top:476px; left:173px; \
        background:url(" + NIT.imagesURL + "btn_ask_508.jpg); z-index:10; cursor:pointer;\" onclick=\"" + launchAnn + "\"></div>";

        annOverlay.innerHTML = annClose + annChatHistory + annInput + annButton;
        document.body.appendChild(annOverlay);
        $("#ann_overlay").slideDown("slow");
    }
};

NIT.hideFloatingLaunchPoint = function ()
{
    if (typeof jQuery != 'undefined') //Don't allow floating launch point functionality unless jQuery is loaded
    {
        $('#ann_overlay').slideUp('slow', function () { $('#ann_overlay').remove(); });
    }
};

NIT.checkAgentSubmit = function (e)
{
    if (typeof jQuery != 'undefined') //Don't allow floating launch point functionality unless jQuery is loaded
    {
        var key = (typeof (e.which) == 'number') ? e.which : e.keyCode;
        var initialQuestion = ($('#floatingLaunchPointTextArea').val() != 'Type your question here.' ? $('#floatingLaunchPointTextArea').val() : '');

        if (key == 13 || key == 10)
        {
            NIT.LaunchAgent(annUrl, NIT.StartRegFromFloat, initialQuestion);
            NIT.hideFloatingLaunchPoint();
        }
        else if (key != 8 && key != 0) // Allow backspace and delete
        {
            if (initialQuestion.length > 199) // Max input length
            {
                if (e.preventDefault) e.preventDefault();
                e.cancelBubble = true;
                e.returnValue = false;
                return false;
            }
        } 
    }
};

function getEventSrc(e)
{
    if (this.Event)
    {
        var targ = e.target;
        //nodeType of 1 means ELEMENT_NODE   
        return targ.nodeType == 1 ? targ : targ.parentNode;
    }
    else   //this is for IE
        return event.srcElement;
}

NIT.clickedOutsideElement = function (elemId, e)
{
    var theElem = getEventSrc(e);
    while (theElem.parentNode != null)
    {
        if (theElem.id == elemId)
            return false;
        theElem = theElem.parentNode;
    }
    return true;
}

// DOM Event handlers
if (typeof jQuery != 'undefined') //Don't allow floating launch point functionality unless jQuery is loaded
{
    $(window).load(function ()
    {
        NIT.checkFloatingLaunchPoint();
    });

    $(document).click(function (e)
    {
        if ($('#ann_overlay').length > 0)
        {
            if (NIT.clickedOutsideElement('ann_overlay', e))
            {
                NIT.hideFloatingLaunchPoint();
            }
        }
    });
    // clear event cookie on page unload.  Most events get cleared if they aren't immediately consumed, but 
    // NavigatorTimeout sticks around in case user launches ann after navigator has timed out 
    $(window).unload(function ()
    {
        NIT.CookieEvent.clear();
    });
}
//////////////////////////////////////
// Begin: CookieEvent Section (this section is shared between multiple files)
//////////////////////////////////////
NIT.CookieEvent = new function ()
{
    var me = this;
    var COOKIE_NAME = "NIT_EVENT";

    this.eventName;

    this.write = function (eventName)
    {
        if (eventName != undefined)
        {
            me.eventName = eventName;
            var c = new NIT.Cookie(COOKIE_NAME);
            c.Values.eventName = me.eventName;
            c.Save();
        }
    };

    this.read = function ()
    {
        me.eventName = null;

        var c = NIT.GetCookie(COOKIE_NAME);
        if (c && c.Values)
        {
            if (c.Values.eventName)
            {
                me.eventName = c.Values.eventName;
            }
        }
    };

    this.clear = function ()
    {
        var c = NIT.GetCookie(COOKIE_NAME);
        if (c) c.Delete();
        me.eventName = null;
    };
};
//////////////////////////////////////
// End: CookieEvent Section
//////////////////////////////////////

//////////////////////////////////////
// Begin: CookieCommand Section (this section is shared between multiple files)
//////////////////////////////////////
NIT.CookieCommand = new function ()
{
    var me = this;
    var COOKIE_NAME = "NIT_CMD";

    this.navigateUrl;
    this.isNavigating = false;
    this.pageChanged = false; // New, for the agent side

    this.write = function ()
    {
        var c = new NIT.Cookie(COOKIE_NAME);
        if (me.navigateUrl)
        {
            // Avoid null string concatenation
            c.Values.navigateUrl = encodeURIComponent(me.navigateUrl);
        }

        c.Values.isNavigating = me.isNavigating;
        c.Values.pageChanged = me.pageChanged;
        c.Save();
    };

    this.read = function ()
    {
        me.navigateUrl = null;

        var c = NIT.GetCookie(COOKIE_NAME);
        if(typeof c!=='undefined'&&c&&c.Values)
        {
            if (c.Values.navigateUrl)
            {
                me.navigateUrl = decodeURIComponent(c.Values.navigateUrl);
            }

            me.isNavigating = (c.Values.isNavigating == "true");
            me.pageChanged = (c.Values.pageChanged == "true");
        }
    };
};

//////////////////////////////////////
// CookieCommand Section: Launch page only portion
//////////////////////////////////////

NIT.CookieCommandPolling = new function ()
{
    var me = this;
    var timeout = null;

    NIT.CookieCommand.read();
    if (NIT.CookieCommand.isNavigating)
    {
        NIT.CookieCommand.isNavigating = false;
        NIT.CookieCommand.write();
    }
    else // Page changed, not navigated by agent
    {
        NIT.CookieCommand.pageChanged = true;
        NIT.CookieCommand.write();
    }

    // Setup cookie polling for two-way commands
    this.checkCommandCookie = function ()
    {
        //JIRA:AET-5519 - Polling now only starts when on DocFind pages, so window association is ignored
        //if (PopupScript.IsAgentAssociatedParentWindow()) //Only associated parent window performs the navigation
        //{
        NIT.CookieCommand.read();
        if (NIT.CookieCommand.navigateUrl)
        {
            var url = NIT.CookieCommand.navigateUrl;

            location.href = url;

            NIT.CookieCommand.navigateUrl = null;
            NIT.CookieCommand.write();
        }
        //}

        if (timeout)
        {
            clearTimeout(timeout);
        }
        timeout = setTimeout(me.checkCommandCookie, 500);
    };
    //this.checkCommandCookie();
};
//////////////////////////////////////
// End: CookieCommand Section
//////////////////////////////////////

NIT.MPEEstimate_Success = "MPEEstimate_Success";
NIT.MPEEstimate_Error = "MPEEstimate_Error";
NIT.MPEProviderList_Success = "MPEProviderList_Success";
NIT.MPEProviderList_Error = "MPEProviderList_Error";
NIT.SessionTimeout = "SessionTimeout";
NIT.NavigatorLogOut = "NavigatorLogOut";
NIT.MPEDisclaimerCancel = "MPEDisclaimerCancel";
NIT.DocFindSearchComplete = "DocFindSearchComplete";
NIT.DocFindPlanSelectionCancel = "DocFindPlanSelectionCancel";
NIT.DocFindMedicarePlanSelection = "DocFindMedicarePlanSelection";
NIT.TriggerReloadUserProfile="TriggerReloadUserProfile";
NIT.CostDetailsPageLoad="CostDetailsPageLoad";


NIT.RaiseAgentEvent = function (eventName)
{
    NIT.CookieEvent.write(eventName);

    // SessionTimeout cookie should remain in place so Ann knows your session is timed out if she gets launched
    // Note that the event cookie is cleared on page unload, because sessionTrackerExt will trigger the correct behavior once the user navigates
    if(eventName!=NIT.SessionTimeout&&eventName!=NIT.TriggerReloadUserProfile)
    {
        // Check that the event was consumed
        setTimeout(function ()
        {
            NIT.CookieEvent.read();
            if (NIT.CookieEvent.eventName) // event wasn't consumed
            {
                NIT.CookieEvent.clear();
            }
        }, 1000);
    }
};

//end file
