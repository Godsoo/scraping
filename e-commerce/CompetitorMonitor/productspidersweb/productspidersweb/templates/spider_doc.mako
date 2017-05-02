<!DOCTYPE html>
<html>

<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>spider_doc</title>
    <link rel="stylesheet" href="/productspiders/static/bootstrap/css/bootstrap.min.css">
</head>

<body>
<div class="container">
    <header>
        <nav class="navbar navbar-default">
            <div class="container-fluid">
                <div class="navbar-header">
                    % if back_url:
                        <ul class="nav navbar-nav navbar-left">
                            <li role="presentation"><a href="${back_url}">Back </a></li>
                        </ul>
                    % endif
                </div>
                <div class="collapse navbar-collapse" id="navcol-1">
                    <button class="navbar-toggle collapsed" data-toggle="collapse" data-target="#navcol-1"><span
                            class="sr-only">Toggle navigation</span><span class="icon-bar"></span><span
                            class="icon-bar"></span><span class="icon-bar"></span></button>
                    <a class="btn btn-danger navbar-btn navbar-right" role="button" href="${refresh_cache_url}">Refresh
                        cache</a></div>
            </div>
        </nav>
    </header>
    <ul class="nav nav-tabs">
        <li class="${'active' if not spec_active else ''}"><a href="#spider_doc" data-toggle="tab">Spider doc</a></li>
        <li class="${'active' if spec_active else ''}"><a href="#spider_spec" data-toggle="tab">Spider spec</a></li>
    </ul>
    <div class="tab-content">
        <div id="spider_doc" class="tab-pane ${'active' if not spec_active else ''}">
                <%include file="spider_doc/doc_tab_contents.mako"/>
        </div>
        <div id="spider_spec" class="tab-pane ${'active' if  spec_active else ''}">
            % if can_edit_spec:
                <%include file="spider_doc/spec_form_tab_contents.mako"/>
            % else:
                <%include file="spider_doc/spec_view_tab_contents.mako"/>
            % endif
        </div>
    </div>
</div>
<script src="/productspiders/static/js/jquery.js"></script>
<script src="/productspiders/static/bootstrap/js/bootstrap.min.js"></script>
</body>

</html>