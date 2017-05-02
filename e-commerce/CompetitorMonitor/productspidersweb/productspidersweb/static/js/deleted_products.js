/**
 * Author: juraseg
 * Date: 2/7/13
 */

(function (window) {
    /*********************************
     * Date comparison
     *********************************/
    function is_earlier_date(date) {
        if (!(date instanceof Date)) {
            date = new Date(date);
        }
        var one_day_timestamp = 86400000,
            today = new Date();
        return ((today - date) > one_day_timestamp);
    }

    /*********************************
     * Crawl actions
     *********************************/
    function set_crawl_valid(crawl_id, reload) {
        if (reload === undefined) {
            reload = true;
        }
        $.post('/productspiders/set_valid', {crawl_id:crawl_id}, function (data) {
            if (reload) {
                location.reload(true);
            }
        });
    }
    function delete_invalid_crawl(crawl_id, reload) {
        if (reload === undefined) {
            reload = true;
        }
        $.post('/productspiders/delete_crawl', {crawl_id:crawl_id}, function (data) {
            if (reload) {
                location.reload(true);
            }
        });
    }
    function upload_changes(spider_id, real_upload, reload) {
        if (reload === undefined) {
            reload = true;
        }
        $.post('/productspiders/upload', {spider_id:spider_id, real_upload:real_upload}, function (data) {
            if (reload) {
                location.reload(true);
            }
        });
    }
    function run_crawl(spider_name, reload) {
        if (reload === undefined) {
            reload = true;
        }
        $.post('/productspiders/runcrawl', {spider: spider_name}, function (data) {
            if (reload) {
                location.reload(true);
            }
        });
    }


    /*********************************
     * iframes
     *********************************/
    function focus_iframe() {
        document.getElementById("iframe_modal").focus();
    }

    function show_modal_iframe(src, view_model, config) {
        if (config === undefined) {
            config = false;
        }
        var template = '' +
            '<div id="iframe_container">' +
            '   <button id="iframe_refresh">Refresh</button><br />' +
            '   <iframe id="iframe_modal" src="' + src + '" height="650" width="1100" style="border:0">' +
            '</div>';
        $.modal(
            template,
            {
                //closeHTML:"",
                containerCss: {
                    backgroundColor: "#fff",
                    height: 680,
                    padding: 0,
                    width: 1100
                },
                overlayClose: true,
                onClose: function (dialog) {
        //            view_model.getData();
                    $.modal.close();
                }
            }
        );
        $("#iframe_modal").load(function (event) {
            var self = this,
                $form;

            setTimeout(focus_iframe, 150);

            if (config) {
                $form = $(this).contents().find("form");
                $($form).submit(function (event) {
                    $(self).load(function () {
                        $.modal.close();
                        view_model.getData();
                    });
                });
            }
        });
        $("#iframe_refresh").click(function(e) {
            $("#iframe_modal").get(0).contentWindow.location.reload(true);
            e.preventDefault();
        });
    }


    /*********************************
     * modal windows
     *********************************/
    function show_modal_config_iframe(src, viewmodel) {
        show_modal_iframe(src, viewmodel, true);
    }

    function show_modal_ajax_loading(message) {
        var template = '\
            <div style="text-align:center">\
                <img src="/productspiders/static/images/ajax-loader.gif" />\
                <br />\
                %%message%%\
            </div>';
        var options = {
            containerCss:{
                backgroundColor:"#fff"
            },
            overlayClose:false,
            escClose:false,
            closeHTML: ""
        };
        if (!message) {
            options.containerCss.height = 16;
            options.containerCss.width = 16;
            options.containerCss.padding = 0;
            options.containerCss.border = "none";
            message = "";
        }
        else {
            message = "<p>" + message + "</p>";
        }
        template = template.replace("%%message%%", message);
        $.modal(template, options);
    }

    function show_modal_assigned_to_assembla(view_model, spider) {
        var template;
        if (spider.assembla_ticket_id()) {
            show_modal_ajax_loading("Loading ticket...");

            $.getJSON(spider.assembla_ticket_url(), function(data) {
                close_modal();
                if (data.status == 'error') {
                    template = '<div id="assigned_to_simple">\
                        <h3>Failed to load Assembla ticket...</h3>\
                        Assign to:\
                        <input type="text"/>\
                        <button>Save</button>\
                    </div>';
                    $.modal(
                        template,
                        {
                            containerCss:{
                                // border: "none",
                                backgroundColor:"#fff"
                            },
                            overlayClose:true,
                            escClose:true
                        }
                    );
                    function save(value) {
                        spider.assigned_to(value);
                        view_model.save_assigned(spider);
                    }
                    var $popup = $("#assigned_to_simple");
                    $($popup).find("a").attr('href', spider.assembla_authorization_url());
                    $($popup).find("button").on('click', save);
                    $($popup).find("input").on('keypress', function(event) {
                        if (event.keyCode == 13) {
                            event.preventDefault();
                            var value = $($popup).find("input").val();
                            save(value);
                        }
                    });
                    if (spider.assigned()) {
                        $($popup).find("input").val(spider.assigned_to());
                    }
                }
                else {
                    template = '<div id="assigned_to_assembla">\
                        <h3>Assembla ticket is already created</h3>\
                        <h4>Summary:</h4><p id="summary">' + data.summary + '</p>\
                        <h4>Description:</h4><p id="description">' + data.description + '</p>\
                        <h4>Assigned to:</h4><p id="assigned_to">' + data.assigned_to + '</p>\
                        <h4>URL:</h4><a href="' + data.url + '" title="URL to ticket" target="_blank">' + data.url + '</a>\
                    </div>';
                    $.modal(
                        template,
                        {
                            containerCss:{
                                width: 480,
                                // border: "none",
                                backgroundColor:"#fff"
                            },
                            overlayClose:true,
                            escClose:true
                        }
                    );
                }
            });
        }
        else {
            var ticket_summary = spider.account_name() + ": " + spider.name() + " issue";

            var options = "";
            for (var idx in view_model.assembla.users) {
                var user_name = view_model.assembla.users[idx].name;
                var user_id = view_model.assembla.users[idx].id;
                options = options + "<option value='" + user_id + "'>" + user_name + "</option>";
            }

            template = '<div id="assigned_to_assembla">\
                    <form method="post">\
                        <input type="hidden" name="id" value="' + spider.id() + '"/>\
                        Ticket name:<br />\
                        <input name="summary" size="40" value="' + ticket_summary + '"/><br /><br />\
                        Ticket description:<br />\
                        <textarea name="description" cols="32" rows="10">&lt;error description&gt;</textarea><br /><br />\
                        Assign to:<br />\
                        <select name="assign_to">\
                        ' + options + '\
                        </select><br /><br />\
                        Upload source file? <input type="checkbox" name="upload_source_file" checked/><br />\
                        <input type="submit" value="Save"/>\
                    </form>\
                </div>';
            $.modal(
                template,
                {
                    containerCss:{
                        width: 280,
                        // border: "none",
                        backgroundColor:"#fff"
                    },
                    overlayClose:true,
                    escClose:true
                }
            );

            function save(ticket_id, assigned_to) {
                spider.assembla_ticket_id(ticket_id);
                spider.assigned_to(assigned_to);
            }
            var $popup = $("#assigned_to_assembla");
            $($popup).find("form").attr('action', view_model.assembla.ticket_submit_url);
            $($popup).find("form").ajaxForm({
                beforeSubmit: function($form, options, event) {
                    close_modal();
                    show_modal_ajax_loading("Saving ticket...");
                },
                success: function(data) {
                    close_modal();
                    if (data.status == 'ok') {
                        save(data.ticket_id, data.assigned_to);
                    }
                    else {
                        console.log("ERROR: error saving ticket");
                        console.log(data.message);
                    }
                },
                error: function(data) {
                    console.log("ERROR: server error occured while saving ticket");
                    close_modal();
                }
            });
        }
    }

    function show_modal_assigned_to_simple(view_model, spider, message) {
        var template = '<div id="assigned_to_simple">\
                Assign to:\
                <input type="text"/>\
                <button>Save</button>\
                <br />\
                <a href="" title="Create ticket in Assembla...">Create ticket in Assembla...</a>\
            </div>';
        $.modal(
            template,
            {
                containerCss:{
                    // border: "none",
                    backgroundColor:"#fff"
                },
                overlayClose:true,
                escClose:true
            }
        );
        function save() {
            var value = $($popup).find("input").val();
            spider.assigned_to(value);
            view_model.save_assigned(spider);
        }
        var $popup = $("#assigned_to_simple");
        $($popup).find("a").attr('href', spider.assembla_authorization_url());
        $($popup).find("button").on('click', save);
        $($popup).find("input").on('keypress', function(event) {
            if (event.keyCode == 13) {
                event.preventDefault();
                save();
            }
        });
        if (spider.assigned()) {
            $($popup).find("input").val(spider.assigned_to());
        }
    }

    function show_modal_assigned_to(view_model, spider) {
        if (view_model.assembla.authorized) {
            show_modal_assigned_to_assembla(view_model, spider);
        }
        else {
            show_modal_assigned_to_simple(view_model, spider);
        }
    }

    function show_modal_upload_fix(view_model, spider) {
        var template = '<div id="upload_fix">\
                <form method="post" enctype="multipart/form-data">\
                    Upload new spider source<br /><br />\
                    <input type="hidden" name="id" value="' + spider.id() + '"/>\
                    <input type="file" name="source_file" style="width:380px"/><br /><br />\
                    <input type="submit" value="Upload"/><br />\
                </form>\
            </div>';
        $.modal(
            template,
            {
                containerCss:{
                    width: 480,
                    // border: "none",
                    backgroundColor:"#fff"
                },
                overlayClose:true,
                escClose:true
            }
        );
        var $popup = $("#upload_fix");
        $($popup).find("form").attr('action', spider.upload_spider_source());
        $($popup).find("form").ajaxForm({
            beforeSubmit: function($form) {
                close_modal();
                show_modal_ajax_loading("Uploading spider source...");
            },
            success: function(data) {
                close_modal();
                if (data.status == 'ok') {
                    console.log("Uploaded fix");
                }
                else {
                    console.log("ERROR: error uploading fix");
                    console.log(data.message);
                }
            },
            error: function() {
                console.log("ERROR: server error occured while uploading fix");
                close_modal();
            }
        });
    }

    function close_modal() {
        $.modal.close();
    }

    /*********************************
     * Spider model for KO
     *********************************/
    function Spider(data) {
        var self = this;

        for (var key in data) {
            self[key] = ko.observable(data[key]);
        }

        self.id = ko.observable(data.id);
        self.name = ko.observable(data.name);
        self.crawl_id = ko.observable(data.crawl_id);
        self.crawl_date = ko.observable(data.crawl_date);
        self.crawl_status = ko.observable(data.crawl_status);
        self.website_id = data.website_id;
        self.enabled = ko.observable(data.enabled);
        self.account_enabled = ko.observable(data.account_enabled);
        self.account_name = ko.observable(data.account_name);
        self.automatic_upload = ko.observable(data.automatic_upload);
        self.upload_testing_account = ko.observable(data.upload_testing_account);
        self.error = ko.observable(data.error);
        self.crawls_url = ko.observable(data.crawls_url);
        self.config_url = ko.observable(data.config_url);
        self.logs_url = ko.observable(data.logs_url);
        self.set_valid_url = ko.observable(data.set_valid_url);
        self.delete_crawl_url = ko.observable(data.delete_crawl_url);
        self.errors_url = ko.observable(data.errors_url);
        self.upload_url = ko.observable(data.upload_url);
        self.set_uploaded_url = ko.observable(data.set_uploaded_url);
        self.change_error_status_url = ko.observable(data.change_error_status_url);
        self.assigned_to = ko.observable(data.assigned_to);
        self.save_error_assignment_url = ko.observable(data.save_error_assignment_url);
        self.assembla_authorization_url = ko.observable(data.assembla_authorization_url);
        self.assembla_ticket_id = ko.observable(data.assembla_ticket_id);
        self.assembla_ticket_url = ko.observable(data.assembla_ticket_url);
        self.upload_spider_source = ko.observable(data.upload_spider_source);

        self.status = ko.computed(function () {
            if (self.enabled() && self.id()) {
                return "Enabled";
            }
            else {
                return "Disabled";
            }
        });
        self.account_status = ko.computed(function () {
            if (self.account_enabled() && self.id()) {
                return "Enabled";
            }
            else {
                return "Disabled";
            }
        });
        self.automatic_upload_text = ko.computed(function () {
            if (self.automatic_upload()) {
                return "Enabled";
            }
            else {
                return "Disabled";
            }
        });
        self.error_status = ko.computed(function() {
            if (self.error()) {
                return self.error().status;

            }
            else {
                return "No error";
            }
        });
        self.is_valid = self.set_valid_url ? true : false;
        self.assigned = ko.computed(function() {
            if (self.assigned_to() == "" || self.assigned_to() == null) {
                return false;
            }
            else {
                return true;
            }
        });
    }

    /*********************************
     * ViewModel for ko
     *********************************/
    function ViewModel(model_url, errors, assembla_config) {
        var self = this;

        self.model_url = model_url;

        self.spiders = ko.observableArray([]);

        self.errors = errors;

        self.assembla = assembla_config;

        self.change_error_status_text = ko.computed(function() {
            if (self.errors == 'possible') {
                return "Mark as real error";
            }
            else if (self.errors == 'real') {
                return "Mark as fixed";
            }
            return null;
        });

        self.title = ko.computed(function() {
            if (!self.errors) {
                return "All spiders";
            }
            else {
                if (self.errors == 'real') {
                    return "Real errors spiders";
                }
                else if (self.errors == 'possible') {
                    return "Possible errors spiders";
                }
                else {
                    return "Error spiders";
                }
            }
        });

        self.editing = ko.observable(false);
        self.editing_assigned_to = ko.observable("");
        self.editing_spider = null;

        self._remove_spider = function(spider) {
            this.spiders.remove(function (item) { return spider.id == item.id; });
        };

        self.show_spider_crawls = function (spider) {
            show_modal_iframe(spider.crawls_url(), self);
        };
        self.show_spider_errors = function (spider) {
            show_modal_iframe(spider.errors_url(), self);
        };
        self.show_spider_config = function (spider) {
            show_modal_config_iframe(spider.config_url(), self);
        };
        self.show_spider_logs = function (spider) {
            show_modal_iframe(spider.logs_url(), self);
        };

        self.set_crawl_valid = function (spider) {
            set_crawl_valid(spider.crawl_id, false);
            spider.set_valid_url(undefined);
            spider.delete_crawl_url(undefined);
            if (self.errors == 'possible') {
                self._remove_spider(spider);
            }
        };
        self.delete_invalid_crawl = function (spider) {
            delete_invalid_crawl(spider.crawl_id, false);
            spider.delete_crawl_url(undefined);
            spider.set_valid_url(undefined);
            if (self.errors == 'possible') {
                self._remove_spider(spider);
            }
        };
        self.upload_changes = function (spider) {
            upload_changes(spider.id(), '1', false);
            spider.upload_url(undefined);
            spider.set_uploaded_url(undefined);
        };
        self.run_spider = function(spider) {
            run_crawl(spider.name(), false);
            spider.crawl_status('scheduled');
        };
        self.set_uploaded = function (spider) {
            upload_changes(spider.id(), '0', false);
            spider.upload_url(undefined);
            spider.set_uploaded_url(undefined);
        };
        self.change_error_status = function(spider) {
            if (self.errors == 'possible') {
                self.mark_error_as_real(spider);
            }
            else if (self.errors == 'real') {
                self.mark_error_as_fixed(spider);
            }
        };
        self.mark_error_as_real = function(spider) {
            $.post(
                spider.change_error_status_url(),
                {id: spider.id, status: 'real'},
                function(data) {
                    if (data['status'] == 'OK') {
                        self._remove_spider(spider);
                    }
                }
            );
        };
        self.mark_error_as_fixed = function(spider) {
            $.post(
                spider.change_error_status_url(),
                {id: spider.id, status: 'fixed'},
                function(data) {
                    if (data['status'] == 'OK') {
                        self._remove_spider(spider);
                    }
                }
            );
        };

        self.save_assigned = function(spider) {
            $.post(
                spider.save_error_assignment_url(),
                {id: spider.id, assigned: spider.assigned_to()},
                function() {
                    close_modal();
                }
            );
        };

        self.edit_assigned_to = function(spider) {
            self.editing(true);
            self.editing_spider = spider;
            show_modal_assigned_to(self, spider);
        };

        self.upload_fix = function(spider) {
            show_modal_upload_fix(self, spider);
        };

        self.runnable = function(spider) {
            if (spider.enabled()) {
                if (spider.crawl_status() == 'processing_finished' ||
                    spider.crawl_status() == 'errors_found' ||
                    spider.crawl_status() == 'scheduled' ||
                    spider.crawl_status() == 'scheduled_on_worker' ||
                    spider.crawl_status() == 'schedule_errors' ||
                    spider.crawl_status() == 'running' ||
                    spider.crawl_status() == 'crawl_finished' ||
                    spider.crawl_status() == 'upload_errors' ||
                    spider.crawl_status() == 'retry') {
                    return false;
                }
                var crawl_date = new Date(spider.crawl_date());
                if (is_earlier_date(crawl_date)) {
                    return true;
                }
                return false;
            }
            return false;
        };

        self.getData = function (additional_callback) {
            show_modal_ajax_loading("Loading spiders...");
            $.getJSON(self.model_url, function (data) {
                var mappedSpiders = $.map(data, function (spider_data) {
                    return new Spider(spider_data);
                });
                self.spiders(mappedSpiders);

                if (typeof additional_callback === "function") {
                    additional_callback();
                }
                close_modal();
            });
        };
    }

    var spiders_ko = {
        init: function(spiders_url, errors, assembla_config, container) {
            var view_model = new ViewModel(spiders_url, errors, assembla_config);
            view_model.getData();
            ko.applyBindings(view_model);

            $(container).dataTable({"iDisplayLength": 100, "bStateSave": true});

            this.view_model = view_model;
        }
    };
    window['spiders_ko'] = spiders_ko;


     /*********************************
     * DeletionsReview model for KO
     *********************************/
    function DeletionsReview(data) {
        var self = this;

        for (var key in data) {
            self[key] = ko.observable(data[key]);
        }

        self.crawl_id = ko.observable(data.crawl_id);
        self.id = ko.observable(data.crawl_id);
        self.crawl_date = ko.observable(data.crawl_date);
        self.found_date = ko.observable(data.found_date);
        self.spider_id = ko.observable(data.spider_id);
        self.account_name = ko.observable(data.account_name);
        self.site = ko.observable(data.site);
        self.name = ko.observable(data.site);
        self.matched_count = ko.observable(data.matched_count);
        self.total = ko.observable(data.total);
        self.unmatched_count = ko.observable(data.unmatched_count);
        self.change_error_status_url = ko.observable(data.change_error_status_url);
        self.assigned_to = ko.observable(data.assigned_to);
        self.save_error_assignment_url = ko.observable(data.save_error_assignment_url);
        self.assembla_authorization_url = ko.observable(data.assembla_authorization_url);
        self.assembla_ticket_id = ko.observable(data.assembla_ticket_id);
        self.assembla_ticket_url = ko.observable(data.assembla_ticket_url);
        self.upload_spider_source = ko.observable(data.upload_spider_source);
        self.products_url = ko.observable(data.products_url);

        self.assigned = ko.computed(function() {
            if (self.assigned_to() == "" || self.assigned_to() == null) {
                return false;
            }
            else {
                return true;
            }
        });
    }

    /*********************************
     * ViewModel for ko
     *********************************/
    function ViewModelDR(model_url, assembla_config) {
        var self = this;

        self.model_url = model_url;

        self.drs = ko.observableArray([]);

        self.assembla = assembla_config;


        self.editing = ko.observable(false);
        self.editing_assigned_to = ko.observable("");
        self.editing_dr = null;


        self._remove_dr = function(dr) {
            this.drs.remove(function (item) { return dr.crawl_id == item.crawl_id; });
        };


        self.show_products = function (dr) {
            show_modal_iframe(dr.products_url(), self);
        };


        self.mark_error_as_fixed = function(dr) {
            $.post(
                dr.change_error_status_url(),
                {crawl_id: dr.crawl_id},
                function(data) {
                    if (data['ok'] == 'OK!') {
                        self._remove_dr(dr);
                    }
                }
            );
        };

        self.save_assigned = function(dr) {
            $.post(
                dr.save_error_assignment_url(),
                {id: dr.crawl_id, assigned: dr.assigned_to()},
                function() {
                    close_modal();
                }
            );
        };

        self.edit_assigned_to = function(dr) {
            self.editing(true);
            self.editing_dr = dr;
            show_modal_assigned_to(self, dr);
        };

        self.upload_fix = function(dr) {
            //show_modal_upload_fix(self, dr);
        };

        self.getData = function (additional_callback) {
            show_modal_ajax_loading("Loading data...");
            $.getJSON(self.model_url, function (data) {
                var mappedSpiders = $.map(data, function (spider_data) {
                    return new DeletionsReview(spider_data);
                });
                self.drs(mappedSpiders);

                if (typeof additional_callback === "function") {
                    additional_callback();
                }
                close_modal();
            });
        };
    }

    var drs_ko = {
        init: function(drs_url, assembla_config, container) {
            var view_model = new ViewModelDR(drs_url, assembla_config);
            view_model.getData();
            ko.applyBindings(view_model);

            $(container).dataTable({"iDisplayLength": 100, "bStateSave": true});

            this.view_model = view_model;
        }
    };
    window['drs_ko'] = drs_ko;
})(window);