#!/bin/sh -e
set -x

echo "NO_START=0\nJETTY_HOST=127.0.0.1\nJETTY_PORT=8983\n" | sudo tee /etc/default/jetty
cat /etc/default/jetty
sudo cp ckan/ckan/config/solr/schema.xml /etc/solr/conf/schema.xml
sudo /etc/init.d/jetty start
sleep 20 
nosetests --ckan --nologcapture --with-pylons=subdir/test.ini --reset-db --with-coverage --cover-package=ckanext.issues --cover-inclusive --cover-erase --cover-tests
