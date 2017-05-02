CREATE TABLE spider_spec (
	spider_id INTEGER NOT NULL,
	_data TEXT NOT NULL,
	PRIMARY KEY (spider_id),
	FOREIGN KEY(spider_id) REFERENCES spider (id)
)