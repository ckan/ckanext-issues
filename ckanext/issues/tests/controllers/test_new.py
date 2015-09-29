from ckan.lib import search
from ckan.plugins import toolkit
import ckan.new_tests.helpers as helpers
import ckan.new_tests.factories as factories

from ckanext.issues.tests import factories as issue_factories
from ckanext.issues.tests.helpers import ClearOnTearDownMixin

from nose.tools import assert_equals, assert_in


class TestCreateNewIssue(helpers.FunctionalTestBase, ClearOnTearDownMixin):
    def setup(self):
        super(TestCreateNewIssue, self).setup()
        self.owner = factories.User()
        self.org = factories.Organization(user=self.owner)
        self.dataset = factories.Dataset(user=self.owner,
                                         owner_org=self.org['name'])
        self.app = self._get_test_app()

    def test_create_new_issue(self):
        env = {'REMOTE_USER': self.owner['name'].encode('ascii')}
        response = self.app.get(
            url=toolkit.url_for('issues_new', dataset_id=self.dataset['id']),
            extra_environ=env,
        )
        form = response.forms['issue-new']
        form['title'] = 'new issue'
        form['description'] = 'test_description'
        response = helpers.webtest_submit(form, 'save', extra_environ=env)

        response = response.follow()
        assert_equals(200, response.status_int)
        assert_in('Your issue has been registered, thank you for the feedback',
                  response)

        issues = helpers.call_action('issue_search',
                                     dataset_id=self.dataset['id'])
        assert_equals(1, issues['count'])
        assert_equals('new issue', issues['results'][0]['title'])
        assert_equals('test_description', issues['results'][0]['description'])


class TestCreateNewIssueComment(helpers.FunctionalTestBase,
                                ClearOnTearDownMixin):
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
                                issue_number=self.issue['number'],
                                dataset_id=self.dataset['id']),
            params={'comment': 'Comment'},
            extra_environ=env,
        )
        response = response.follow()
        assert_equals(200, response.status_int)
        issue_dict = toolkit.get_action('issue_show')(
            data_dict={
                'dataset_id': self.dataset['id'],
                'issue_number': self.issue['number'],
            }
        )
        assert_equals('Comment', issue_dict['comments'][0]['comment'])
