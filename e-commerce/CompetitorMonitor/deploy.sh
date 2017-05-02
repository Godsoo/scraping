#!/bin/sh

restart=0
restart_celery=0

for arg in "$@"
do
    if [ "$arg" = "restart" ]; then
        restart=1
    fi
    if [ "$arg" = "restart_celery" ]; then
        restart_celery=1
    fi
done

~/pythoncrawlers/bin/fab -H innodev@148.251.79.44 deploy

if [ ${restart} = 1 ]; then
    ~/pythoncrawlers/bin/fab -H innodev@148.251.79.44 deploy_webapp
fi
if [ ${restart_celery} = 1 ]; then
    ~/pythoncrawlers/bin/fab -H innodev@148.251.79.44 deploy_celery
fi
~/pythoncrawlers/bin/fab -H innodev@88.198.32.57,innodev@competitormonitor.com:2777,innodev@88.99.3.215 -P deploy_slave_repo:'product-spiders-repo-scrapy1','product-spiders-scrapy1'
