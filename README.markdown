CKAN Todo Extension
===================

Adds Todo list functionality.

**Current Status:** Incomplete

Installation and Activation
---------------------------

To install the plugin, enter your virtualenv and install the source:

    $ pip install hg+http://bitbucket.org/johnglover/ckanext-todo

This will also register a plugin entry point, so you now should be 
able to add the following to your CKAN .ini file:

    ckan.plugins = todo
 
After you clear your cache and reload the site, the Todo plugin
and should be available. 

Todo / Roadmap
--------------
* Tests
* Add autocomplete API and frontend for todo categories

Tests
-----
From the ckanext-todo directory, run:

    $ nosetests --ckan

Feedback
--------
Send any comments, queries, suggestions or bug reports to:
j @ johnglover dot net.
