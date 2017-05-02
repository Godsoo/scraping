<div class="page-header">
    <h1>Spider documentation: <span class="text-muted">${spider.name}</span></h1></div>
% if ticket_url:
    <section>
        <h3>Original ticket: <a href="${ticket_url}" target="_blank">
            % if ticket_num:
                &num;${ticket_num}
            %else:
                URL
            % endif
        </a></h3></section>
% endif
% if spider_rating is not None:
    <section>
        <%
            # determine which label we need: green (success), yellow (warning), red (danger)
            if spider_rating >= 10:
                                label_class = 'label-danger'
            elif spider_rating >= 5:
                                label_class = 'label-warning'
            else:
                                label_class = 'label-success'
        %>
        <h3>Spider complexity rating: <span class="label ${label_class}">${spider_rating} </span></h3>
        % if edit_spider_rating:
            <small><a href="${edit_spider_rating}">Edit</a></small>
        % endif
    </section>
% endif
% if created_by:
    <section>
        <h3>Created by: <span class="text-muted">${created_by}</span></h3></section>
% endif
% if top_comment_lines:
    <section>
        <div id="accordion-top-comment" class="panel-group">
            <div class="panel panel-default">
                <div class="panel-heading">
                    <h3 class="panel-title"><a href="#panel-top-comment" class="accordion-toggle"
                                               data-toggle="collapse"
                                               data-parent="#accordion">Top comment</a></h3></div>
                <div class="panel-body panel-collapse collapse" id="panel-top-comment">
                    <p>
                        % for line in top_comment_lines:
                        ${line}<br/>
                        % endfor
                    </p>
                </div>
            </div>
        </div>
    </section>
% endif
% if last_commit_by:
    <section>
        <h3>Last commit by: <span class="text-muted">${last_commit_by}</span></h3></section>
% endif
% if commits:
    <section>
        <div id="accordion-commits" class="panel-group">
            <div class="panel panel-default">
                <div class="panel-heading">
                    <h3 class="panel-title">
                        <a href="#panel-commits" class="accordion-toggle"
                           data-toggle="collapse"
                           data-parent="#accordion-commits">Commits (${len(commits)})</a>
                    </h3></div>
                <div class="panel-body panel-collapse collapse" id="panel-commits">
                    % for commit in commits:
                        <article>
                            <h5>Changeset: ${commit['changeset']}</h5>
                            <ul>
                                <li>Date: ${commit['date']}</li>
                                <li>By: ${commit['user']}</li>
                                <li>Description: ${commit['desc']}</li>
                            </ul>
                        </article>
                    % endfor
                </div>
            </div>
        </div>
    </section>
% endif