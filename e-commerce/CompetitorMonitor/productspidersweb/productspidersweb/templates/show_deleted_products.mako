<%!
    def url_short(text):
        return text[:50] + '...'
%>
<html>
<head>
    <link rel="stylesheet" type="text/css" href="/productspiders/static/css/jquery.dataTables.css" />
    <script type="text/javascript" src="/productspiders/static/js/jquery-1.9.1.min.js"></script>
    <script type="text/javascript" src="/productspiders/static/js/jquery.dataTables.1.9.0.js"></script>

    <script type="text/javascript">
        $(document).ready(function() {
                $('#deleted_products').dataTable({"bStateSave": true});
        });
    </script>
</head>
<body>
	<h1>Deleted products</h1>
	<table id="deleted_products" class="display">
        <thead>
            <tr>
                <td>Product Name</td>
                <td>Url</td>
                <td>Dealer</td>
        	</tr>
        </thead>

        <tbody>
		% for product in deleted_products:
            <tr>
                <td>${product.product_name}</td>
                <td><a href="${product.url}" target="_blank" title="${product.url}">${product.url|url_short}<a/></td>
                <td>${product.dealer}</td>
            </tr>
		% endfor
        </tbody>
	</table>
</body>
</html>
