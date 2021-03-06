<html>
<head>
    <link rel="stylesheet" type="text/css" href="/productspiders/static/css/jquery.dataTables.css" />
    <script type="text/javascript" src="/productspiders/static/js/jquery-1.9.1.min.js"></script>
    <script type="text/javascript" src="/productspiders/static/js/jquery.dataTables.1.9.0.js"></script>

    <script type="text/javascript">
        function delete_additional_fields_group(id)
        {
            if (confirm('Are you sure?')) {
                window.location.replace('${request.route_url("delete_additional_fields_group")}' + '?id=' + id);
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
	<h1>Additional Fields groups</h1>
    <a href="${request.route_url('config_additional_fields_group')}">Create additional fields groups</a><br/>
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
		% for additional_fields_group in additional_fields_groups:
		  <tr>
		        <td>${additional_fields_group.id}</td>
                <td>${additional_fields_group.name}</td>
                <td><a href="${request.route_url('config_additional_fields_group') + '?id=' + str(additional_fields_group.id)}">Edit</a></td>
                <td><a href="javascript: delete_additional_fields_group('${additional_fields_group.id}')">Delete</a></td>
		  </tr>
		% endfor
        </tbody>
	</table>
</body>
</html>
