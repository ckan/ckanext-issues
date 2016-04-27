#!/bin/sh -e
set -x

echo "NO_START=0\nJETTY_HOST=127.0.0.1\nJETTY_PORT=8983\nJAVA_HOME=$JAVA_HOME" | sudo tee /etc/default/jetty
ls /usr/share/solr/
pwd
ls
ckan/bin/solr_init/create_core.sh
sudo cp ckan/ckan/config/solr/schema.xml /etc/solr/conf/schema.xml
sudo service jetty restart
nosetests --ckan --nologcapture --with-pylons=subdir/test.ini --reset-db --with-coverage --cover-package=ckanext.issues --cover-inclusive --cover-erase --cover-tests
