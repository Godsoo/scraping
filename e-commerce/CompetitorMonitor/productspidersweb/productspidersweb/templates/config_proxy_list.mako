<html>
<head></head>
<body>
    <a href="${request.route_url('logout')}" title="Logout">Logout</a>
    <br /><br />
    <a href="${request.route_url('home')}" title="Home">Home</a>
    % if proxy_list:
        <h1>Configuration for ${proxy_list.name}</h1>
    % else:
        <h1>New proxy list</h1>
    % endif

    ${renderer.begin(request.route_url('config_proxy_list'))}
	${renderer.csrf_token()}
	<div class="field">
        % if proxy_list:
                <input type="hidden" value="${proxy_list.id}" name="id" />
        % endif

        <label for="name">Name</label><br/>
            ${renderer.text("name", size=30)}<br/>
            ${renderer.errorlist("name")}
        <label for="proxies">Proxies (One per line)</label><br/>
           ${renderer.textarea("proxies", style="width: 215px; height:200px")}<br/>
           ${renderer.errorlist("proxies")}

	</div>

	<div class="buttons">
        ${renderer.submit("submit", "Submit")}
	</div>
	${renderer.end()}
</body>
</html>
