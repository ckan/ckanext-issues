from ckan import model
from ckan.lib import search
from ckan.plugins import toolkit
import ckan.new_tests.helpers as helpers
import ckan.new_tests.factories as factories

from ckanext.issues.tests import factories as issue_factories

from nose.tools import assert_true, assert_raises


class TestIssueUpdate(object):
    def teardown(self):
        helpers.reset_db()
        search.clear()

    def test_org_editor_can_update_an_issue(self):
        org_editor = factories.User()
        org = factories.Organization()
        helpers.call_action('member_create', object=org_editor['name'],
                            id=org['id'], object_type='user',
                            capacity='editor')
        dataset = factories.Dataset(owner_org=org['name'], private=True)
        user = helpers.call_action('get_site_user')
        issue = issue_factories.Issue(user=user, dataset_id=dataset['id'])

        context = {
            'user': org_editor['name'],
            'model': model,
        }
        assert_true(helpers.call_auth('issue_update', context,
                                      dataset_id=dataset['id']))

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
        assert_true(helpers.call_auth('issue_update', context, id=issue['id'],
                                      dataset_id=dataset['id'],
                                      status='open'))

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
        assert_raises(toolkit.NotAuthorized, helpers.call_auth, 'issue_update',
                      context, id=issue['id'], dataset_id=dataset['id'],
                      status='open')
