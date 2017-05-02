/*
OnlineOpinion v5.7.5
Released: 7/22/2013. Compiled 08/01/2013 01:19:59 PM -0500
Branch: master ec3bc14a5857d12efdb13903e508244a142f29ab
Components: Full
UMD: disabled
The following code is Copyright 1998-2013 Opinionlab, Inc.  All rights reserved. Unauthorized use is prohibited. This product and other products of OpinionLab, Inc. are protected by U.S. Patent No. 6606581, 6421724, 6785717 B1 and other patents pending. http://www.opinionlab
*/

/* [+] Floating Icon configuration */
var TLcookie = "TLAETGuid";

if (OOo.readCookie('TLAETGuid') == null) {
    TLcookie = "JSESSIONID_102";
}

/* [+] Tab Configuration*/
var oo_tab = new OOo.Ocode({
  tab: {},
  tealeafCookieName: TLcookie
});
