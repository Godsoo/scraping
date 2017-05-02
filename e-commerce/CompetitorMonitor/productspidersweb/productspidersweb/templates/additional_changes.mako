<html>
<head>
</head>
<body>
<a href="${request.route_url('logout')}" title="Logout">Logout</a>
<br/><br/>
<a href="${request.route_url('home')}" title="Home">Home</a>

<h1>Additional changes for ${crawl.spider.name} on ${crawl.crawl_date}</h1>
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
            <a href="${request.route_url(request.matched_route.name.replace("_paged", ""), crawl_id=crawl.id)}">Show
                all</a>
            <span>Pages: </span>
            % if start > 1:
                <a href="${request.route_url(request.matched_route.name, crawl_id=crawl.id, _query={'page':1})}">
                    << </a>
            % endif
            % for i in xrange(start, end + 1):
                % if i == page:
                    <span>${i}</span>
                % else:
                    <a href="${request.route_url(request.matched_route.name, crawl_id=crawl.id, _query={'page':i})}">${i}</a>
                % endif
            % endfor
            % if end < pages_count:
                <a href="${request.route_url(request.matched_route.name, crawl_id=crawl.id, _query={'page':pages_count})}">
                    >> </a>
            % endif
        </div>
    % endif
    % for product in products:
        <h3>Changes for</h3>
        <table border="1">
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
                <td>Dealer</td>
            </tr>

            <tr>
                <td>${product['product_data'].get('identifier', '')}</td>
                <td>${product['product_data'].get('sku', '')}</td>
                <td>${product['product_data']['name']}</td>
                <td>${product['product_data']['price']}</td>
                <td><a href="${product['product_data']['url']}">${product['product_data']['url']}</a></td>
                <td>${product['product_data'].get('category', '')}</td>
                <td>${product['product_data'].get('brand', '')}</td>
                <td>
                    <a href="${product['product_data'].get('image_url', '')}">
                        ${product['product_data'].get('image_url', '')}
                    </a>
                </td>
                <td>${product['product_data'].get('shipping_cost', '')}</td>
                <td>${product['product_data'].get('dealer', '')}</td>
            </tr>

        </table>
        <br/>
        <table border="1">
            <tr>
                <td>Field</td>
                <td>Old Value</td>
                <td>New Value</td>
            </tr>

            % for field in sorted(product['changes'].keys()):
                <tr>
                    <td>${field}</td>
                    <td>${product['changes'][field][0]}</td>
                    <td>${product['changes'][field][1]}</td>
                </tr>
            % endfor
        </table>
    % endfor
</body>
</html>
