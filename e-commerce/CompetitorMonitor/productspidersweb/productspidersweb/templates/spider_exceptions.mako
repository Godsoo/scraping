<html>
<head>
    <link rel="stylesheet" type="text/css" href="/productspiders/static/css/jquery.dataTables.css" />
    <script type="text/javascript" src="/productspiders/static/js/jquery-1.9.1.min.js"></script>
    <script type="text/javascript" src="/productspiders/static/js/jquery.dataTables.1.9.0.js"></script>

    <script type="text/javascript">

    </script>

  <script type="text/javascript">
        $(document).ready(function () {
            $('#exceptions').dataTable({
                "bStateSave": true,
                "bPaginate": false,
                "aaSorting": [[0, "desc"]]
            });
        });
    </script>
</head>
<body>
    <a href="${request.route_url('logout')}" title="Logout">Logout</a>
    <br /><br />
    <a href="${request.route_url('home')}" title="Home">Home</a>
	<h1>Spider exceptions</h1>

	<table border="1" id="exceptions">
        <thead>
		<tr>
		    <td>Date</td>
			<td>Spider</td>
            <td>Total</td>
			<td>Exceptions</td>
			<td>&nbsp;</td>
		</tr>
        </thead>
        <tbody>
		% for ex in spider_exceptions:
		  <tr>
		        <td>${str(ex.date)}</td>
                <td>${ex.spider_name}</td>
                <td>${str(ex.total) if ex.total else ''}</td>
                <td>${ex.exceptions}</td>
                <td><a href="${request.route_url('exception_log') + '?id=' + str(ex.id)}">Download</a></td>
		  </tr>
		% endfor
        </tbody>
	</table>
</body>
</html>
