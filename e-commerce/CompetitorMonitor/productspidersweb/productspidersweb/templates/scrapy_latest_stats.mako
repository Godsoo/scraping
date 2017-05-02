<html>
<head>
    <link rel="stylesheet" type="text/css" href="/productspiders/static/css/jquery.dataTables.css" />
    <script type="text/javascript" src="/productspiders/static/js/jquery-1.9.1.min.js"></script>
    <script type="text/javascript" src="/productspiders/static/js/jquery.dataTables.1.9.0.js"></script>

    <script type="text/javascript">
        $(document).ready(function () {
            $('#stats').dataTable({
                "bStateSave": true,
                "bPaginate": false,
                "aoColumns": [
                    null,
                    null,
                    null
                  ]
            });
        });
    </script>
</head>
<body>
    <a href="${request.route_url('logout')}" title="Logout">Logout</a>
    <br /><br />
    <a href="${request.route_url('home')}" title="Home">Home</a>
	<h1>Spiders tested on latest scrapy</h1>
	<table border="1" id="stats" class="display">
        <thead>
		<tr>
		    <td>Account</td>
			<td>Spider</td>
			<td>Successful Crawls</td>
		</tr>
        </thead>
        <tbody>
		% for spider in spiders_pending:
		  <tr>
                <td>${spider.Account.name}</td>
		        <td>${spider.Spider.name}</td>
                <td>NO</td>
		  </tr>
		% endfor
        % for spider in spiders_success:
		  <tr>
                <td>${spider.Account.name}</td>
		        <td>${spider.Spider.name}</td>
                <td>YES</td>
		  </tr>
		% endfor
        </tbody>
	</table>
</body>
</html>
