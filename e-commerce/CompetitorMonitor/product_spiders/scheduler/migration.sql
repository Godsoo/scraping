alter type status add value 'scheduled_on_worker' after 'scheduled';
alter type status add value 'schedule_errors' after 'scheduled_on_worker';
alter table crawl add column scheduled_time timestamp without time zone;
alter table crawl add column scheduled_on_worker_time timestamp without time zone;

alter table worker_server add column worker_slots integer default 5;