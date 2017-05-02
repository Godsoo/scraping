<html>
<head>
    <script type="text/javascript" src="/productspiders/static/js/jquery-1.9.1.min.js"></script>
</head>
<body>
    <a href="${request.route_url('logout')}" title="Logout">Logout</a>
    <br /><br />
    <a href="${request.route_url('home')}" title="Home">Home</a>
	<h1>Configuration for ${account.name}</h1>
	${renderer.begin(request.route_url('config_account', account=account.name))}
	${renderer.csrf_token()}
	<div class="field">	
    	     <label for="member_id" >Member ID</label><br/>
    	     ${renderer.text("member_id", size=6)}<br/>
    	     ${renderer.errorlist("member_id")}
        <br/>
        <h3>Upload destinations (leave blank for default - new system)</h3>
        % for upload_dst in upload_destinations:
            <label for="upload_to_${upload_dst.name}">Upload to ${upload_dst.name}</label>
            ${renderer.checkbox("upload_to_" + upload_dst.name, checked=(upload_dst in account.upload_destinations))}<br /><br />
        % endfor
        <label for="crawls_per_day" >Crawls per day(optional)</label><br/>
           	  ${renderer.text("crawls_per_day", size=2)}<br/>
           	  ${renderer.errorlist("crawls_per_day")}
               <br/>
	     <label for="enabled">Enabled</label>
	     ${renderer.checkbox("enabled")}<br/>
	     ${renderer.errorlist("enabled")}
	     <h3>Email notification receivers(Comma separated)</h3>
	     % for status in statuses:
	       <label for="${status}_emails">${statuses_labels[status]}</label></br>
	       ${renderer.text(status + "_emails", size=30)}<br/>
	       ${renderer.errorlist(status + "_emails")}
	     % endfor
	     <br />
	     <label for="enabled">MAP screenshots</label>
         ${renderer.checkbox("map_screenshots")}<br/>
         ${renderer.errorlist("map_screenshots")}
         <br />
	</div>

	<div class="buttons">
    	     ${renderer.submit("submit", "Submit")}
	</div>
	${renderer.end()}	
</body>
</html>
