<html>
<head>
    <script type="text/javascript" src="/productspiders/static/js/jquery-1.9.1.min.js"></script>
    <script type="text/javascript">
        function set_updates_silent()
        {
            if (confirm("Are you sure?")) {
                $.post('/productspiders/set_updates_silent', {crawl_id:'${crawl.id}'}, function (data) {
                    location.reload(true);
                }
               );
            }
        }
        function set_update_silent(i)
        {
            if (confirm("Are you sure?")) {
                $.post('/productspiders/set_updates_silent', {crawl_id:'${crawl.id}', line: i}, function (data) {
                    location.reload(true);
                }
               );
            }
        }
    </script>
</head>
<body>
    <a href="${request.route_url('logout')}" title="Logout">Logout</a>
    <br /><br />
    <a href="${request.route_url('home')}" title="Home">Home</a>
	<h1>Changes for ${crawl.spider.name} on ${crawl.crawl_date}</h1><br/>
    <a href="javascript: set_updates_silent()">Set all updates silent</a>
    % if pages_count and page:
        <%
        start = page - 2
        if start < 1:
            start = 1
        end = start + 5
        if end > pages_count:
            end = pages_count
        %>
        <div style="float: right;">
            <a href="${request.route_url(request.matched_route.name.replace("_paged", ""), crawl_id=crawl.id)}">Show all</a>
            <span>Pages: </span>
        % if start > 1:
            <a href="${request.route_url(request.matched_route.name, crawl_id=crawl.id, _query={'page':1})}"> << </a>
        % endif
        % for i in xrange(start, end + 1):
            % if i == page:
                <span>${i}</span>
            % else:
                <a href="${request.route_url(request.matched_route.name, crawl_id=crawl.id, _query={'page':i})}">${i}</a>
            % endif
        % endfor
        % if end < pages_count:
            <a href="${request.route_url(request.matched_route.name, crawl_id=crawl.id, _query={'page':pages_count})}"> >> </a>
        % endif
        </div>
    % endif
	<table border="1">
	       <tr>
        <td>Identifier</td>
		<td>SKU</td>
		<td>Name</td>
		<td>Old Price</td>
		<td>Price</td>
		<td>Difference</td>
		<td>Change Type</td>
		<td>Url</td>
        <td>Category</td>
        <td>Brand</td>
        <td>Image URL</td>
        <td>Shipping Cost</td>
        <td>Stock</td>
	<td>Dealer</td>
        <td>&nbsp;</td>
	    </tr>
	       % for i, change in enumerate(changes):
	        <tr>
		  % for key in ['identifier', 'sku', 'name', 'old_price', 'price', 'difference', 'change_type']:
		    <td>${str(change.get(key, '')).decode('utf8', 'ignore')}</td>
		  % endfor
		  <td><a href="${change['url'].decode('utf8', 'ignore')}">${change['url'].decode('utf8', 'ignore')}</a></td>
           <td>${change.get('category', '').decode('utf8', 'ignore')}</td>
            <td>${change.get('brand', '').decode('utf8', 'ignore')}</td>
            <td>
                <a href="${change.get('image_url', '').decode('utf8', 'ignore')}">
                ${change.get('image_url', '').decode('utf8', 'ignore')}
               </a>
            </td>
            <td>${change.get('shipping_cost', '')}</td>
            <td>${change.get('stock', '')}</td>
	    <td>${change.get('dealer', '').decode('utf8', 'ignore')}</td>
          <td>
              % if change['change_type'] == 'update':
                <a href="javascript: set_update_silent('${i}')">Set update silent</a>
              % endif
          </td>
		</tr>
	       % endfor
	</table>
</body>
</html>
