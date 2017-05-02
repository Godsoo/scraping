<html>
<head>
    <title>Spider rating: ${spider.name}</title>

    <!-- Bootstrap core CSS -->
    <link href="/productspiders/static/bootstrap/css/bootstrap.min.css" rel="stylesheet">
    <link href="/productspiders/static/bootstrap/css/bootstrap-select.min.css" rel="stylesheet">
    <link href="/productspiders/static/bootstrap/css/datepicker.css" rel="stylesheet">
    <link href="/productspiders/static/bootstrap/bootstrap_table/bootstrap-table.css" rel="stylesheet">
    <link href="/productspiders/static/bootstrap/bootstrap_table/bootstrap-table-filter.css" rel="stylesheet">

    <!-- HTML5 shim and Respond.js IE8 support of HTML5 elements and media queries -->
    <!--[if lt IE 9]>
      <script src="https://oss.maxcdn.com/libs/html5shiv/3.7.0/html5shiv.js"></script>
      <script src="https://oss.maxcdn.com/libs/respond.js/1.4.2/respond.min.js"></script>
    <![endif]-->

    <script src="/productspiders/static/js/jquery.js"></script>
</head>
<body>

## IMPORTANT!!!
##
## This template has quite a complex logic, which is needed to render spider ratings edit form properly.
## It does heavy usage of Mako "defs" (http://docs.makotemplates.org/en/latest/defs.html#using-defs)
## and python blocks (http://docs.makotemplates.org/en/latest/syntax.html#python-blocks)
## to make it more readable.
##
## Also some auxiliary functions are defined in module level block
## (http://docs.makotemplates.org/en/latest/syntax.html#module-level-blocks).
##
## Please, carefully investigate how it works before doing changes.
##
## If any questions please contact Yuri Abzyanov at <yuri.abzyanov@competitormonitor.com>


## Module-level definition of auxiliary functions
<%!
    def field_path(field, parents):
        return '.'.join(parents + [field])

    def subfield_path(subfield, field, parents):
        return field_path(subfield, parents + [field])

    def get_field_title(field, field_config):
        return field_config.get('title', field)
%>


## This is top level rendered, it checks field's type and dispatches to proper renderer
<%def name="render_field(field, field_parents, field_config, field_data)">
    % if field_config['type'] == 'simple':
        % if field_config.get('type2', None) == 'multiple':
            ${render_multiple_field(field, field_parents, field_config, field_data)}
        % else:
            ${render_regular_field(field, field_parents, field_config, field_data)}
        % endif
    % elif field_config['type'] == 'options':
        ${render_options(field, field_parents, field_config, field_data)}

    % elif field_config['type'] == 'checkboxes':
        <div class="panel panel-default">
            <div class="panel-heading">
                <h3 class="panel-title">${get_field_title(field, field_config)}</h3>
            </div>
            <div class="panel-body">
                ${render_checkboxes(field, field_parents, field_config, field_data)}
            </div>
        </div>
    % endif
</%def>

## This rendered renders "options" field.
## It also renders additional sections for values, which has subvalues
<%def name="render_options(field, field_parents, field_config, field_data)">
    <div class="form-group">
        <label class="col-sm-2" for="${field_path(field, field_parents)}">${get_field_title(field, field_config)}</label>
        <div class="col-sm-10">
            <select name="${field_path(field, field_parents)}">
                % for subfield, subfield_config in field_config['values'].items():
                    <option value="${subfield}" id="${subfield_path(subfield, field, field_parents)}"
                            % if field_data and field_data.get('value', None) == subfield:
                                selected
                            % endif
                    >${get_field_title(subfield, subfield_config)}</option>
                % endfor
            </select>
        </div>
        <div class="help-block with-errors"></div>
    </div>
    % for subfield, subfield_config in field_config['values'].items():
        <%
        if field_data and field_data.get('value', None) == subfield:
            subfield_data = field_data.get('subvalues', {})
        else:
            subfield_data = None
        %>
        % if 'values' in subfield_config and len(subfield_config['values']) > 0:
            <div id="div_${subfield_path(subfield, field, field_parents)}" class="div_${field_path(field, field_parents)}">
                ${render_field(subfield, field_parents + [field], subfield_config, subfield_data)}
            </div>
            <script type="text/javascript">
                % if not(field_data and field_data.get('value', None) == subfield):
                    $("[id='div_${subfield_path(subfield, field, field_parents)}']").hide();
                % endif
                $("[id='${subfield_path(subfield, field, field_parents)}']").click(function() {
                    $("[class='div_${field_path(field, field_parents)}']").hide();
                    $("[id='div_${subfield_path(subfield, field, field_parents)}']").show();
                });
            </script>
        % else:
            <script type="text/javascript">
                $("[id='${subfield_path(subfield, field, field_parents)}']").click(function() {
                    $("[class='div_${field_path(field, field_parents)}']").hide();
                });
            </script>
        % endif
    % endfor
</%def>

## This renderer renders list of fields
<%def name="render_checkboxes(field, field_parents, field_config, field_data)">
    % for subfield, subfield_config in field_config['values'].items():
        <div id="div_${subfield_path(subfield, field, field_parents)}">
            ${render_field(subfield, field_parents + [field], subfield_config, field_data.get(subfield, None) if field_data else None)}
        </div>
    % endfor
</%def>

## Just a regular field
<%def name="render_regular_field(field, field_parents, field_config, field_value)">
    <div class="form-group">
        <label class="col-sm-2" for="${field_path(field, field_parents)}">${get_field_title(field, field_config)}</label>
        <div class="col-sm-10">
            <input type="checkbox" name="${field_path(field, field_parents)}"
                   % if field_value:
                       checked
                   % endif
            />
        </div>
        <div class="help-block with-errors"></div>
    </div>
</%def>

## Multiple values field
<%def name="render_multiple_field(field, field_parents, field_config, field_data)">
    <%
        field_id = field_path(field, field_parents)
    %>
    <div class="panel panel-default">
        <div class="panel-heading">
            <h5 class="panel-title">${get_field_title(field, field_config)}</h5>
        </div>
        <div class="panel-body">
            <h5>Fields:</h5>
            <input type="hidden" name="${field_id}-count" value=${len(field_data) if field_data else 0} />
            <button type="button" class="btn btn-default" id="${field_id}-add">
                <span class="glyphicon glyphicon-plus" aria-hidden="true"></span>
            </button>
            <hr />
            <div id="${field_id}-container">
                % if field_data:
                    % for i, value in enumerate(field_data):
                        <div class='form-group' id=' + new_input_name + -container'>
                            <label class='col-sm-1' for='${field_id}-${i}'>Field:</label>
                            <div class='col-sm-2'>
                                <input type='text' name='${field_id}-${i}' value="${value}" required />
                            </div>
                            <div class='col-sm-2'>
                                <button type='button' class='btn btn-danger' id='${field_id}-${i}-remove'>
                                    <span class='glyphicon glyphicon-remove' aria-hidden='true'></span>
                                </button>
                            </div>
                            <div class='help-block with-errors'></div>
                        </div>
                    % endfor
                % endif
            </div>
        </div>
    </div>
    <script type="text/javascript">
        $("[id='${field_id}-add']").click(function() {
            var count = parseInt($("[name='${field_id}-count']").val());
            var new_input_name = "${field_id}-" + String(count);

            var new_input_html = "" +
                "<div class='form-group' id='" + new_input_name + "-container'>" +
                    "<label class='col-sm-1' for=" + new_input_name + ">Field:</label>" +
                    "<div class='col-sm-2'>" +
                        "<input type='text' name='" + new_input_name + "' required />" +
                    "</div>" +
                    "<div class='col-sm-2'>" +
                        "<button type='button' class='btn btn-danger' id='" + new_input_name + "-remove'>" +
                            "<span class='glyphicon glyphicon-remove' aria-hidden='true'></span>" +
                        "</button>" +
                    "</div>" +
                    "<div class='help-block with-errors'></div>" +
                "</div>";
            $("[id='${field_id}-container']").append(new_input_html);

            $("[id='" + new_input_name + "-remove'").click(function() {
                var id = $(this).attr('id');
                var container_id = id.replace('-remove', '-container');
                var $container = $("[id='" + container_id + "']");
                $($container).remove();
            });

            $("[name='${field_id}-count']").val(count + 1);
        });
    </script>
</%def>

## This is where actual content gegins
<div class="container">
    <h1>Edit spider rating: ${spider.name}</h1>
    <div class="panel panel-default">
        <div class="panel-body">
            <form action="${edit_spider_rating}" method='POST'
                  role="form" data-toggle="validator" class="form-horizontal" id="spider-rating-form">
                % for field, field_config in metrics_schema.items():
                    <div id="div_${field}">
                        ${render_field(field, [], field_config, params.get(field, None))}
                    </div>
                % endfor
                <input type="submit" />
            </form>
        </div>
    </div>
</div>

<script src="/productspiders/static/js/jquery.serializeObject.js"></script>
    <script>
        jQuery.ajaxSettings.traditional = true;
    </script>
    <script src="/productspiders/static/js/ajax.js"></script>
    <script src="/productspiders/static/js/utils.js"></script>
    <script src="/productspiders/static/bootstrap/js/bootstrap.min.js"></script>
    <script src="/productspiders/static/bootstrap/js/bootstrap-datepicker.js"></script>
    <script src="/productspiders/static/bootstrap/js/bootstrap-select.min.js"></script>
    <script src="/productspiders/static/bootstrap/js/validator.js"></script>
    <script src="/productspiders/static/bootstrap/bootstrap_table/bootstrap-table.js"></script>
    <script src="/productspiders/static/bootstrap/bootstrap_table/bootstrap-table-filter.js"></script>
    <script src="/productspiders/static/bootstrap/bootstrap_table/extensions/filter/bootstrap-table-filter.js"></script>
    <script src="/productspiders/static/bootstrap/bootstrap_table/bs-table.js"></script>
    <script src="/productspiders/static/bootstrap/bootstrap_table/tableExport.js"></script>
    <script src="/productspiders/static/bootstrap/bootstrap_table/jquery.base64.js"></script>
    <script src="/productspiders/static/bootstrap/bootstrap_table/extensions/export/bootstrap-table-export.js"></script>
    <script src="/productspiders/static/js/underscore-min.js"></script>
</body>