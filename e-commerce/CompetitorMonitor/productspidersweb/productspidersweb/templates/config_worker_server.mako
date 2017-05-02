<html>
<head></head>
<body>
    <a href="${request.route_url('logout')}" title="Logout">Logout</a>
    <br /><br />
    <a href="${request.route_url('home')}" title="Home">Home</a>
    % if worker_server:
        <h1>Configuration for ${worker_server.name}</h1>
    % else:
        <h1>New worker server</h1>
    % endif

    ${renderer.begin(request.route_url('config_worker_server'))}
	${renderer.csrf_token()}
	<div class="field">
        % if worker_server:
                <input type="hidden" value="${worker_server.id}" name="id" />
        % endif

        <label for="name">Name</label><br/>
            ${renderer.text("name", size=30)}<br/>
            ${renderer.errorlist("name")}
        <label for="host">Host</label><br/>
            ${renderer.text("host", size=30)}<br/>
            ${renderer.errorlist("host")}
        <label for="user">User</label><br/>
            ${renderer.text("user", size=30)}<br/>
            ${renderer.errorlist("user")}
        <label for="password">Password</label><br/>
            ${renderer.text("password", size=30)}<br/>
            ${renderer.errorlist("password")}
        <label for="port">Port</label><br/>
            ${renderer.text("port", size=5)}<br/>
            ${renderer.errorlist("port")}
        <label for="scrapy_url">Scrapy URL</label><br/>
            ${renderer.text("scrapy_url", size=30)}<br/>
            ${renderer.errorlist("scrapy_url")}
        <label for="enabled">Enabled</label><br/>
            ${renderer.checkbox("enabled")}<br/>
            ${renderer.errorlist("enabled")}
	</div>

	<div class="buttons">
        ${renderer.submit("submit", "Submit")}
	</div>
	${renderer.end()}
</body>
</html>
