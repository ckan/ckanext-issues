from ckan.plugins import toolkit
import ckan.new_tests.helpers as helpers
import ckan.new_tests.factories as factories

from ckanext.issues.tests import factories as issue_factories

from nose.tools import assert_equals


class TestIssuesController(helpers.FunctionalTestBase):
    def test_unauthorized_users_cannot_see_issues_on_a_dataset(self):
        '''test that a 401 is returned, previously this would just 500'''
        user = factories.User()
        org = factories.Organization(user=user)
        dataset = factories.Dataset(user=user, owner_org=org['name'], 
                                    private=True)
        issue = issue_factories.Issue(user=user, user_id=user['id'], 
                                      dataset_id=dataset['id'])
        unauthorized_user = factories.User()

        app = self._get_test_app()
        env = {'REMOTE_USER': unauthorized_user['name'].encode('ascii')}

        response = app.get(
            url=toolkit.url_for('issues_show', 
                                package_id=dataset['id'], 
                                id=issue['id']),
            extra_environ=env,
            expect_errors=True
        )
        assert_equals(response.status_int, 401)
