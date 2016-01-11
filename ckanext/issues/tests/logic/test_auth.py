from ckan import model
from ckan.plugins import toolkit
try:
    from ckan.new_tests import helpers
    from ckan.new_tests import factories
except ImportError:
    from ckan.tests import helpers
    from ckan.tests import factories

from ckanext.issues.tests import factories as issue_factories
from ckanext.issues.tests.helpers import (
    ClearOnTearDownMixin,
    ClearOnSetupClassMixin
)

from nose.tools import assert_true, assert_raises


class TestIssueUpdate(ClearOnTearDownMixin, ClearOnSetupClassMixin):
    def test_org_editor_can_update_an_issue(self):
        org_editor = factories.User()
        org = factories.Organization(
            users=[{'name': org_editor['id'], 'capacity': 'editor'}]
        )
        dataset = factories.Dataset(owner_org=org['name'], private=True)
        user = helpers.call_action('get_site_user')
        issue = issue_factories.Issue(user=user, dataset_id=dataset['id'])

        context = {
            'user': org_editor['name'],
            'model': model,
        }
        assert_true(
            helpers.call_auth(
                'issue_update',
                context,
                issue_number=issue['number'],
                dataset_id=dataset['id'],
                status='open'
            )
        )

    def test_issue_owner_can_update_issue(self):
        issue_owner = factories.User()
        org = factories.Organization()
        dataset = factories.Dataset(owner_org=org['name'])
        issue = issue_factories.Issue(user=issue_owner,
                                      user_id=issue_owner['id'],
                                      dataset_id=dataset['id'])

        context = {
            'user': issue_owner['name'],
            'model': model,
        }
        assert_true(
            helpers.call_auth(
                'issue_update',
                context,
                issue_number=issue['number'],
                dataset_id=dataset['id'],
                status='open'
            )
        )

    def test_organization_member_cannot_update_issue(self):
        user = factories.User()
        issue_owner = factories.User()
        org = factories.Organization(
            users=[{'name': user['id'], 'capacity': 'member'}]
        )
        dataset = factories.Dataset(owner_org=org['name'])
        issue = issue_factories.Issue(user=issue_owner,
                                      user_id=issue_owner['id'],
                                      dataset_id=dataset['id'])

        other_user = factories.User()
        context = {
            'user': other_user['name'],
            'model': model,
        }
        assert_raises(
            toolkit.NotAuthorized,
            helpers.call_auth,
            'issue_update',
            context,
            issue_number=issue['number'],
            dataset_id=dataset['id'],
            status='open'
        )

    def test_normal_user_cannot_update_issue(self):
        issue_owner = factories.User()
        org = factories.Organization()
        dataset = factories.Dataset(owner_org=org['name'])
        issue = issue_factories.Issue(user=issue_owner,
                                      user_id=issue_owner['id'],
                                      dataset_id=dataset['id'])

        other_user = factories.User()
        context = {
            'user': other_user['name'],
            'model': model,
        }
        assert_raises(
            toolkit.NotAuthorized,
            helpers.call_auth,
            'issue_update',
            context,
            issue_number=issue['number'],
            dataset_id=dataset['id'],
            status='open'
        )

    def test_anonymous_user_cannot_update_issue(self):
        issue_owner = factories.User()
        org = factories.Organization()
        dataset = factories.Dataset(owner_org=org['name'])
        issue = issue_factories.Issue(user=issue_owner,
                                      user_id=issue_owner['id'],
                                      dataset_id=dataset['id'])

        other_user = factories.User()
        context = {
            'user': other_user['name'],
            'model': model,
        }
        assert_raises(
            toolkit.NotAuthorized,
            helpers.call_auth,
            'issue_update',
            context,
            issue_number=issue['number'],
            dataset_id=dataset['id'],
            status='open'
        )


class TestIssueDelete(ClearOnTearDownMixin):
    def test_dataset_owner_can_delete_issue(self):
        user = factories.User()
        org = factories.Organization(user=user)
        dataset = factories.Dataset(owner_org=org['name'])
        issue = issue_factories.Issue(user=user,
                                      user_id=user['id'],
                                      dataset_id=dataset['id'])

        context = {
            'user': user['name'],
            'auth_user_obj': user,
            'model': model,
            'session': model.Session,
        }
        helpers.call_auth('issue_delete', context, issue_id=issue['id'],
                          dataset_id=dataset['id'])

    def test_issue_owner_cannot_delete_on_a_dataset_they_do_not_own(self):
        user = factories.User()
        # they aren't part of the org
        org = factories.Organization()
        dataset = factories.Dataset(owner_org=org['name'])
        issue = issue_factories.Issue(user=user,
                                      user_id=user['id'],
                                      dataset_id=dataset['id'])

        context = {
            'user': user['name'],
            'auth_user_obj': user,
            'model': model,
            'session': model.Session,
        }
        assert_raises(toolkit.NotAuthorized, helpers.call_auth, 'issue_delete',
                      context, issue_id=issue['id'], dataset_id=dataset['id'])

    def test_user_cannot_delete_issue_they_do_not_own(self):
        user = factories.User()
        # they aren't part of the org
        owner = factories.User()
        org = factories.Organization(user=owner)
        dataset = factories.Dataset(owner_org=org['name'])
        issue = issue_factories.Issue(user_id=owner['id'],
                                      dataset_id=dataset['id'])

        context = {
            'user': user['name'],
            'auth_user_obj': user,
            'model': model,
            'session': model.Session,
        }
        assert_raises(toolkit.NotAuthorized, helpers.call_auth, 'issue_delete',
                      context, issue_id=issue['id'], dataset_id=dataset['id'])


class TestReport(object):
    def test_any_user_can_report_an_issue(object):
        user = factories.User()
        context = {
            'user': user['name'],
            'model': model,
        }
        assert_true(helpers.call_auth('issue_report', context=context))

    def test_anon_users_cannot_report_issues(object):
        context = {
            'user': None,
            'model': model,
        }
        assert_raises(toolkit.NotAuthorized, helpers.call_auth,
            'issue_report', context=context)
