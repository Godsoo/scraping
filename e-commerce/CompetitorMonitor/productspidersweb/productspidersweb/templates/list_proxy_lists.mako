<html>
<head>
    <link rel="stylesheet" type="text/css" href="/productspiders/static/css/jquery.dataTables.css" />
    <script type="text/javascript" src="/productspiders/static/js/jquery-1.9.1.min.js"></script>
    <script type="text/javascript" src="/productspiders/static/js/jquery.dataTables.1.9.0.js"></script>

    <script type="text/javascript">
        function delete_proxy_list(id)
        {
            if (confirm('Are you sure?')) {
                window.location.replace('${request.route_url("delete_proxy_list")}' + '?id=' + id);
            }
        }
    </script>

  <script type="text/javascript">

  </script>
</head>
<body>
    <a href="${request.route_url('logout')}" title="Logout">Logout</a>
    <br /><br />
    <a href="${request.route_url('home')}" title="Home">Home</a>
	<h1>Proxy Lists</h1>
    <a href="${request.route_url('config_proxy_list')}">Create proxy list</a><br/>
	<table border="1">
        <thead>
		<tr>
		    <td>ID</td>
			<td>Name</td>
			<td>&nbsp;</td>
			<td>&nbsp;</td>
		</tr>
        </thead>
        <tbody>
		% for proxy_list in proxy_lists:
		  <tr>
		        <td>${proxy_list.id}</td>
                <td>${proxy_list.name}</td>
                <td><a href="${request.route_url('config_proxy_list') + '?id=' + str(proxy_list.id)}">Edit</a></td>
                <td><a href="javascript: delete_proxy_list('${proxy_list.id}')">Delete</a></td>
		  </tr>
		% endfor
        </tbody>
	</table>
</body>
</html>
