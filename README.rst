CKAN Todo Extension
===================

Adds Issues (tasks/todos etc) to CKAN.

**Current Status:** Beta

Installation and Activation
---------------------------

To install the plugin, enter your virtualenv and install the source::

    $ pip install git+http://github.com/okfn/ckanext-issues

This will also register a plugin entry point, so you now should be 
able to add the following to your CKAN .ini file::

    ckan.plugins = todo
 
After you clear your cache and reload the site, the Issues plugin
and should be available. 

Tests
-----

From the ckanext-todo directory, run::

    $ nosetests --ckan

Feedback
--------

Send any comments, queries, suggestions or bug reports to:
j @ johnglover dot net.

