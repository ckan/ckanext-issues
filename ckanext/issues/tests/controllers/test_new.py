from ckan.lib import search
from ckan.plugins import toolkit
import ckan.new_tests.helpers as helpers
import ckan.new_tests.factories as factories

from ckanext.issues.tests import factories as issue_factories

from nose.tools import assert_equals


class TestCreateNewIssue(helpers.FunctionalTestBase):
    def setup(self):
        super(TestCreateNewIssue, self).setup()
        self.owner = factories.User()
        self.org = factories.Organization(user=self.owner)
        self.dataset = factories.Dataset(user=self.owner,
                                         owner_org=self.org['name'])
        self.app = self._get_test_app()

    def test_create_new_issue(self):
        env = {'REMOTE_USER': self.owner['name'].encode('ascii')}
        response = self.app.post(
            url=toolkit.url_for('issues_new', package_id=self.dataset['id']),
            params={'title': 'new issue', 'description': 'test description'},
            extra_environ=env,
        )
        response = response.follow()
        assert_equals(200, response.status_int)

    def teardown(self):
        helpers.reset_db()
        search.clear()


class TestCreateNewIssueComment(helpers.FunctionalTestBase):
    def setup(self):
        super(TestCreateNewIssueComment, self).setup()
        self.owner = factories.User()
        self.org = factories.Organization(user=self.owner)
        self.dataset = factories.Dataset(user=self.owner,
                                         owner_org=self.org['name'])
        self.issue = issue_factories.Issue(user=self.owner,
                                           user_id=self.owner['id'],
                                           dataset_id=self.dataset['id'])
        self.app = self._get_test_app()

    def test_create_new_comment(self):
        env = {'REMOTE_USER': self.owner['name'].encode('ascii')}
        response = self.app.post(
            url=toolkit.url_for('issues_comments',
                                id=self.issue['id'],
                                package_id=self.dataset['id']),
            params={'comment': 'Comment'},
            extra_environ=env,
        )
        response = response.follow()
        assert_equals(200, response.status_int)
        issue_dict = toolkit.get_action('issue_show')(
            data_dict={'id': self.issue['id']}
        )
        assert_equals('Comment', issue_dict['comments'][0]['comment'])

    def teardown(self):
        helpers.reset_db()
        search.clear()
