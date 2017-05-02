<div class="page-header">
    <h1>Spider spec</h1></div>
<div>
    <section>
        <h3>Client </h3>
        <p>${spec.get('client', '')}</p>
    </section>
    <section>
        <h3>Date </h3>
        <p>${spec.get('date', '')}</p>
    </section>
    <section>
        <h3>Site name</h3>
        <p>${spec.get('site_name', '')}</p>
    </section>
    <section>
        <h3>Monitor all products on site</h3>
        % for line in spec.get('all_products', '').splitlines():
            <p>${line}</p>
        % endfor
    </section>
    <section>
        <h3>Price </h3>
        % for line in spec.get('price', '').splitlines():
            <p>${line}</p>
        % endfor
    </section>
    <section>
        <h3>Currency </h3>
        <p>${spec.get('currency', '')}</p>
    </section>
    <section>
        <h3>Stock </h3>
        % for line in spec.get('stock', '').splitlines():
            <p>${line}</p>
        % endfor
    </section>
    <section>
        <h3>Categories </h3>
        % for line in spec.get('cat', '').splitlines():
            <p>${line}</p>
        % endfor
    </section>
    <section>
        <h3>Brands </h3>
        % for line in spec.get('brand', '').splitlines():
            <p>${line}</p>
        % endfor
    </section>
    <section>
        <h3>Shipping </h3>
        % for line in spec.get('shipping', '').splitlines():
            <p>${line}</p>
        % endfor
    </section>
    <section>
        <h3>Product codes</h3>
        % for line in spec.get('sku', '').splitlines():
            <p>${line}</p>
        % endfor
    </section>
</div>