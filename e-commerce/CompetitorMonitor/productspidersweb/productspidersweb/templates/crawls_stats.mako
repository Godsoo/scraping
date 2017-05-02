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
                "aaSorting": [[5, "desc"]],
                "aoColumns": [
                    {"bVisible": false, "bSearchable": false},
                    null,
                    null,
                    null,
                    null,
                    { "iDataSort": 0},
                    null,
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
	<h1>Crawls stats</h1>
	<table border="1" id="stats" class="display">
        <thead>
		<tr>
		    <td>Time Taken int</td>
		    <td>Account</td>
			<td>Spider</td>
			<td>Start Time</td>
            <td>End Time</td>
            <td>Time Taken</td>
            <td>Products Count</td>
            <td>Products per Minute</td>
            <td>Proxies</td>
            <td>Tor</td>
		</tr>
        </thead>
        <tbody>
		% for spider in spiders:
		  <tr>
                <td>${int(spider['time_taken'].total_seconds())}</td>
                <td>${spider['account_name']}</td>
		        <td>${spider['name']}</td>
                <td>${spider['start_time'].strftime('%Y-%m-%d %H:%M:%S')}</td>
                <td>${spider['end_time'].strftime('%Y-%m-%d %H:%M:%S')}</td>
                <td>${str(spider['time_taken']).split('.')[0]}</td>
                <td>${spider['products_count']}</td>
                <td>${spider['products_per_min']}</td>
                <td>${spider['use_proxies']}</td>
                <td>${spider['use_tor']}</td>
		  </tr>
		% endfor
        </tbody>
	</table>
</body>
</html>
