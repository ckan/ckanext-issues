[![Build Status](https://travis-ci.org/ckan/ckanext-issues.svg?branch=master)](https://travis-ci.org/ckan/ckanext-issues)
[![Coverage Status](https://coveralls.io/repos/ckan/ckanext-issues/badge.svg)](https://coveralls.io/r/ckan/ckanext-issues)
# CKAN Issues Extension

This extension allows users to to report issues with datasets in a CKAN
instance.

**Current Status:** Beta

## What it does

Once installed and enabled, the issues extension will make available a per-
dataset issue tracker.

The issue tracker user interface can be found at:

    /dataset/{dataset-name-or-id}/issues

You can add an issue at:

    /dataset/{dataset-name-or-id}/issues/add

### Issues API

The issues extension also exposes its functionality as part of the standard [CKAN Action API][api]:

[api]: http://docs.ckan.org/en/latest/api/index.html

Specifically:

    /api/3/action/issue_show
    /api/3/action/issue_create
    /api/3/action/issue_update
    /api/3/action/issue_delete
    /api/3/action/issue_search
    /api/3/action/issue_count
    /api/3/action/issue_comment_create
    /api/3/action/issue_report
    /api/3/action/issue_report_clear
    /api/3/action/issue_comment_report
    /api/3/action/issue_comment_report_clear

## Installation

To install the plugin, enter your virtualenv and install the source::

    pip install -e git+http://github.com/ckan/ckanext-issues

Create the necessary tables:

    paster --plugin=ckanext-issues issues init_db -c ckan.ini

This will also register a plugin entry point, so you now should be
able to add the following to your CKAN .ini file::

    ckan.plugins = issues

After you clear your cache and restart the web server, the Issues extension
should be available.

## Upgrade from older versions

When upgrading ckanext-issues from older code versions, you should run the issues upgrade command, in case there are any model migrations (e.g. 11th Jan 2016):

    paster --plugin=ckanext-issues issues upgrade_db -c test-core.ini

## Configuration

To switch-on notifications, you should set the following option in your
configuration, and all users in the group will get the email.

    ckanext.issues.send_email_notifications = true

If you set max_strikes then users can 'report' a comment as spam/abuse. If the number of users reporting a particular comment hits the max_strikes number then it is hidden, pending moderation.

    ckanext.issues.max_strikes = 2

### Activation

By default, issues are enabled for all datasets. If you wish to restrict
issues to specific datasets or organizations, you can use these config options:
    
    ckanext.issues.enabled_for_datasets = mydataset1 mydataset2 ...
    ckanext.issues.enabled_for_organizations = department-of-transport health-regulator

Alternatively, you can switch issues on/off for particular datasets by using an extra field:

    'issues_enabled': True

and you can set the default for all the other datasets (without that extra field):

    ckanext.issues.enabled_without_extra = false

For the extra field to work you must not set `enabled_per_dataset` or `enabled_for_organizations` options.

### Spam-checking with Akismet 

To enable spam-checking of issues and comments you will need to sign up to [Akismet](https://akismet.com/) and obtain an API Key.  Once you have a key you should add it to the ini file as

```
ckanext.issues.akismet.key = MYAPIKEY
```

If enabled creating an issue or a comment will trigger a background task that checks the content with Akismet, marking it as spam if Akismet suggests that it is.  


## Feedback

Please open an issue in the github [issue tracker][issues].

[issues]: https://github.com/ckan/ckanext-issues

## Developers

Normal requirements for CKAN Extensions (including an installation of CKAN and
its dev requirements). Contributions welcome.

### Testing with Postgres
To run full production tests on postgres run. These are the tests that the travis build will run

    nosetests --ckan --with-pylons=test.ini -v --with-id ckanext/issues --with-coverage --cover-package=ckanext.issues --nologcapture

### Testing with sqlite
For quick development tests run. --reset-db is necessary when running sqlite tests in memory

    nosetests --reset-db --ckan --with-pylons=test-sqlite.ini -v --with-id ckanext/issues --with-coverage --cover-package=ckanext.issues --nologcapture
