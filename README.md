[![Build Status](https://travis-ci.org/okfn/ckanext-issues.svg?branch=master)](https://travis-ci.org/okfn/ckanext-issues)
[![Coverage Status](https://coveralls.io/repos/okfn/ckanext-issues/badge.svg)](https://coveralls.io/r/okfn/ckanext-issues)
# CKAN Issues Extension

This extension allows users to to report issues with datasets and resources in
a CKAN instance.

**Current Status:** Alpha

## What it does

Once installed and enabled, the issues extension will make available a per
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
    /api/3/action/issue_report_spam
    /api/3/action/issue_reset_spam_state
    /api/3/action/issue_comment_report_spam
    /api/3/action/issue_comment_reset_spam_state

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

### Activation

By default, issues are enabled for all datasets. If you wish to restrict
issues to specific datasets you can use the config option
    
    ckanext.issues.enabled_for_dataset = mydataset1 mydataset2 ...

If `enabled_per_dataset` is not set you can use the config option

    ckanext.issues.enabled_per_dataset_default = false

To turn off issues for all datasets, in this case, ckanext-issues will search
for a dataset extra in each dataset

    'issues_enabled': True

If this dataset extra is present, issues will be enabled for that dataset.

## Feedback

Please open an issue in the github [issue tracker][issues].

[issues]: https://github.com/okfn/ckanext-issues

## Developers

Normal requirements for CKAN Extensions (including an installation of CKAN and
its dev requirements).

### Testing with Postgres
To run full production tests on postgres run. These are the tests that the travis build will run

    nosetests --ckan --with-pylons=test.ini -v --with-id ckanext/issues --with-coverage --cover-package=ckanext.issues --nologcapture

### Testing with sqlite
For quick development tests run. --reset-db is necessary when running sqlite tests in memory

    nosetests --reset-db --ckan --with-pylons=test-sqlite.ini -v --with-id ckanext/issues --with-coverage --cover-package=ckanext.issues --nologcapture
