<html>
<head></head>
<body>
    <a href="${request.route_url('logout')}" title="Logout">Logout</a>
    <br /><br />
    <a href="${request.route_url('home')}" title="Home">Home</a>
    % if additional_fields_group:
        <h1>Configuration for ${additional_fields_group.name}</h1>
    % else:
        <h1>New additional fields group</h1>
    % endif

    ${renderer.begin(request.route_url('config_additional_fields_group'))}
	${renderer.csrf_token()}
	<div class="field">
        % if additional_fields_group:
                <input type="hidden" value="${additional_fields_group.id}" name="id" />
        % endif

        <label for="name">Name</label><br/>
            ${renderer.text("name", size=30)}<br/>
            ${renderer.errorlist("name")}
        <label for="enable_url">Enable URL</label><br/>
            ${renderer.checkbox("enable_url")}<br/>
            ${renderer.errorlist("enable_url")}
        <label for="enable_name">Enable Name</label><br/>
            ${renderer.checkbox("enable_name")}<br/>
            ${renderer.errorlist("enable_name")}
        <label for="enable_category">Enable Category</label><br/>
            ${renderer.checkbox("enable_category")}<br/>
            ${renderer.errorlist("enable_category")}
        <label for="enable_brand">Enable Brand</label><br/>
            ${renderer.checkbox("enable_brand")}<br/>
            ${renderer.errorlist("enable_brand")}
        <label for="enable_image_url">Enable Image URL</label><br/>
            ${renderer.checkbox("enable_image_url")}<br/>
            ${renderer.errorlist("enable_image_url")}
        <label for="enable_weekly_updates">Enable Weekly Updates</label><br/>
            ${renderer.checkbox("enable_weekly_updates")}<br/>
            ${renderer.errorlist("enable_weekly_updates")}
	</div>

	<div class="buttons">
        ${renderer.submit("submit", "Submit")}
	</div>
	${renderer.end()}
</body>
</html>
