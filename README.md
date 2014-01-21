# CKAN Issues Extension

This extension allows users to to report issues with datasets and resources in
a CKAN instance.

**Current Status:** Beta

## Installation and Activation

To install the plugin, enter your virtualenv and install the source::

    pip install git+http://github.com/okfn/ckanext-issues

This will also register a plugin entry point, so you now should be
able to add the following to your CKAN .ini file::

    ckan.plugins = issues

After you clear your cache and reload the site, the Issues plugin
and should be available.

To configure notifications, you should set the following options in your
configuration.  Should notify_admin and notify_owner be set to False then no
emails will be sent about the newly created issue.

    ckanext.issues.notify_admin = True
    ckanext.issues.notify_owner = True
    ckanext.issues.from_address = test@localhost.local

Feedback
--------

Please open an issue in the github [issue tracker][issues].

[issues]: https://github.com/okfn/ckanext-issues

