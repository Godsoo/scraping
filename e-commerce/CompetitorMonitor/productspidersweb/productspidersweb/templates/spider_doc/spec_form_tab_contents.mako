<div class="page-header">
    <h1>Spider spec</h1></div>
<div>
    <h3>Load spec from assembla ticket</h3>
    % if assembla_authorized:
        <form method="post" class="form-inline" action="${request.route_url('assembla_load_spec_from_ticket')}">
            <div class="form-group">
                <label for="ticket_num">Ticket Num:</label>
                <input name="ticket_num" type="text" value="${ticket_num if ticket_num else ''}"/>
                % if back_url:
                    <input type="hidden" name="back_url" value="${back_url}"/>
                % endif
            </div>
            <button type="submit" class="btn btn-primary">Load from assembla</button>
            <hr/>
        </form>
    % else:
        <p>You need to login in assembla to use this section: <a href="${request.route_url('assembla_authorization')}"
                                                                 target="_blank">Click
            here to login</a>
        <hr/>
    % endif
</div>
% for msg in spec_errors:
    <div class="alert alert-danger" role="alert">
        <span class="glyphicon glyphicon-exclamation-sign" aria-hidden="true"></span>
        <span class="sr-only">Error:</span>
        ${msg}
    </div>
% endfor
<div>
    <h3>Spec</h3>
    <form method="post">
        <div class="form-group">
            <label class="control-label" for="client">Client </label>
            <input class="form-control" type="text" name="client" value="${spec.get('client', '')}">
        </div>
        <div class="form-group">
            <label class="control-label" for="date">Date </label>
            <input class="form-control" type="date" name="date" value="${spec.get('date', '')}">
        </div>
        <div class="form-group">
            <label class="control-label" for="site_name">Site Name</label>
            <input class="form-control" type="text" name="site_name" value="${spec.get('site_name', '')}">
        </div>
        <div class="form-group">
            <label class="control-label" for="all_products">Monitor all products on site?</label>
            <textarea class="form-control" name="all_products">${spec.get('all_products', '')}</textarea>
        </div>
        <div class="form-group">
            <label class="control-label" for="price">Price </label>
            <textarea class="form-control" name="price">${spec.get('price', '')}</textarea>
        </div>
        <div class="form-group">
            <label class="control-label" for="currency">Currency </label>
            <input class="form-control" type="text" name="currency" value="${spec.get('currency', '')}">
        </div>
        <div class="form-group">
            <label class="control-label" for="stock">Stock </label>
            <textarea class="form-control" name="stock">${spec.get('stock', '')}</textarea>
        </div>
        <div class="form-group">
            <label class="control-label" for="cat">Categories </label>
            <textarea class="form-control" name="cat">${spec.get('cat', '')}</textarea>
        </div>
        <div class="form-group">
            <label class="control-label" for="brand">Brands </label>
            <textarea class="form-control" name="brand">${spec.get('brand', '')}</textarea>
        </div>
        <div class="form-group">
            <label class="control-label" for="shipping">Shipping </label>
            <textarea class="form-control" name="shipping">${spec.get('shipping', '')}</textarea>
        </div>
        <div class="form-group">
            <label class="control-label" for="sku">Product codes</label>
            <textarea class="form-control" name="sku">${spec.get('sku', '')}</textarea>
        </div>
        <button class="btn btn-default" type="submit">Save</button>
    </form>
</div>