/*
This query calculates all proxymesh traffic used by each spider (if not used then spider is ignored)
and outputs it sorted by traffic used
 */
SELECT
  a.id,
  s.id,
  a.name,
  s.name,
  sum(cs.response_bytes) / 1024 / 1024 / 1024 AS "usage (GB)"
FROM crawl_stats cs JOIN crawl c ON cs.crawl_id = c.id
  JOIN spider s ON s.id = c.spider_id
  JOIN proxy_list p ON s.proxy_list_id = p.id
  JOIN account a ON a.id = s.account_id
WHERE p.proxies LIKE '%proxymesh%' AND crawl_date > '2014-09-12' AND crawl_date <= '2014-10-12'
GROUP BY s.id, a.id, a.name, s.name
ORDER BY sum(cs.response_bytes) DESC;