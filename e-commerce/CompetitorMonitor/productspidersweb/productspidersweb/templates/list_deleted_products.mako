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
        function bad_delete(deletion_review_id) {
            $.post('/productspiders/deletion_review_bad_delete', {deletion_review_id: deletion_review_id}, function (data) {
                location.reload();
            });
        }
        function good_delete(deletion_review_id) {
            $.post('/productspiders/deletion_review_good_delete', {deletion_review_id: deletion_review_id}, function (data) {
                location.reload();
            });
        }
        $(document).ready(function() {
                $('#deleted_products').dataTable({"bStateSave": true, "aaSorting": [[0,'desc'], [5,'desc']]});
        });
    </script>
</head>
<body>
    <a href="${request.route_url('logout')}" title="Logout">Logout</a>
    <br /><br />
    <a href="${request.route_url('home')}" title="Home">Home</a>
	<h1>Deleted products</h1>
	<table id="deleted_products" class="display">
        <thead>
            <tr>
                <td>Crawl Date</td>
                <td>Account Name</td>
                <td>Site</td>
                <td>Product Name</td>
                <td>Url</td>
                <td>Matched?</td>
                <td>Dealer</td>
                <td>Product deleted?</td>
        	</tr>
        </thead>

        <tbody>
		% for product in deleted_products:
            <tr>
                <td>${product.crawl_date}</td>
                <td>${product.account_name}</td>
                <td>${product.site}</td>
                <td>${product.product_name}</td>
                <td><a href="${product.url}" target="_blank" title="${product.url}">${product.url|url_short}</a></td>
                <td>
                    % if product.matched:
                        <div style="color: green">Yes</div>
                    % else:
                        <div style="color: red">No</div>
                    % endif
                </td>
                <td>${product.dealer}</td>
                <td><a href="javascript: good_delete('${product.id}')">Yes</a> /
                    <a href="javascript: bad_delete('${product.id}')">No</a></td>
            </tr>
		% endfor
        </tbody>
	</table>
</body>
</html>
