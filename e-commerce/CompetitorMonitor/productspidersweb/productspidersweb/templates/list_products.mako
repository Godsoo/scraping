<html>
<head>
</head>
<body>
    <a href="${request.route_url('logout')}" title="Logout">Logout</a>
    <br /><br />
    <a href="${request.route_url('home')}" title="Home">Home</a>
	<h1>Products for ${crawl.spider.name} on ${crawl.crawl_date}</h1>
    <a href="/productspiders/download_products/${crawl.id}">Download CSV</a>
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
            <span>Pages: </span>
            <a href="${request.route_url(request.matched_route.name.replace("_paged", ""), crawl_id=crawl.id)}">Show all</a>
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
	<table border="1" style="table-layout: fixed;">
	<tr>
	   <td>Identifier</td>
	   <td>SKU</td>
	   <td>Name</td>
	   <td>Price</td>
	   <td>Url</td>
       <td>Category</td>
       <td>Brand</td>
       <td>Image URL</td>
       <td>Shipping Cost</td>
       <td>Stock</td>
       <td>Dealer</td>
        </tr>
% for product in products:
<tr>
<td>${(product.get('identifier', '') or '').decode('utf8', 'ignore')}</td>
<td>${(product.get('sku', '') or '').decode('utf8', 'ignore')}</td>
<td>${product['name'].decode('utf8', 'ignore')}</td>
<td>${product['price']}</td>
<td><a href="${product['url'].decode('utf8', 'ignore')}">${product['url'].decode('utf8', 'ignore')}</a></td>
<td>${(product.get('category', '') or '').decode('utf8', 'ignore')}</td>
<td>${(product.get('brand', '') or '').decode('utf8', 'ignore')}</td>
<td><a href="${(product.get('image_url', '') or '').decode('utf8', 'ignore')}">${(product.get('image_url', '') or '').decode('utf8', 'ignore')}</a></td>
<td>${product.get('shipping_cost', '')}</td>
<td>${product.get('stock', '')}</td>
<td>${(product.get('dealer', '') or '').decode('utf8', 'ignore')}</td>
</tr>
% endfor
	</table>
</body>
</html>
