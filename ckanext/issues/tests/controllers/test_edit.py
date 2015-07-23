from ckan.lib import search
from ckan.plugins import toolkit
import ckan.new_tests.helpers as helpers
import ckan.new_tests.factories as factories

from ckanext.issues.tests import factories as issue_factories

import bs4
from nose.tools import (assert_equals, assert_in, assert_is_not_none,
                        assert_is_none)


class TestIssueEdit(helpers.FunctionalTestBase):
    def setup(self):
        super(TestIssueEdit, self).setup()
        self.owner = factories.User()
        self.org = factories.Organization(user=self.owner)
        self.dataset = factories.Dataset(user=self.owner,
                                         owner_org=self.org['name'])
        self.issue = issue_factories.Issue(user=self.owner,
                                           dataset_id=self.dataset['id'])
        self.app = self._get_test_app()

    def test_edit_issue(self):
        # goto issue show page
        env = {'REMOTE_USER': self.owner['name'].encode('ascii')}
        response = self.app.get(
            url=toolkit.url_for('issues_show',
                                dataset_id=self.dataset['id'],
                                issue_number=self.issue['number']),
            extra_environ=env,
        )
        # click the edit link
        response = response.click(linkid='issue-edit-link', extra_environ=env)
        # fill in the form
        form = response.forms['issue-edit']
        form['title'] = 'edited title'
        form['description'] = 'edited description'
        # save the form
        response = helpers.webtest_submit(form, 'save', extra_environ=env)
        response = response.follow()
        # make sure it all worked
        assert_in('edited title', response)
        assert_in('edited description', response)

        result = helpers.call_action('issue_show',
                                     dataset_id=self.dataset['id'],
                                     issue_number=self.issue['number'])
        assert_equals(u'edited title', result['title'])
        assert_equals(u'edited description', result['description'])

    def teardown(self):
        helpers.reset_db()
        search.clear()


class TestEditButton(helpers.FunctionalTestBase):
    def setup(self):
        super(TestEditButton, self).setup()
        # create a test issue, owned by a user/org
        self.owner = factories.User()
        self.org = factories.Organization(user=self.owner)
        self.dataset = factories.Dataset(user=self.owner,
                                         owner_org=self.org['name'])
        self.issue = issue_factories.Issue(user=self.owner,
                                           dataset_id=self.dataset['id'])

        self.app = self._get_test_app()

    def test_edit_button_appears_for_authorized_user(self):
        env = {'REMOTE_USER': self.owner['name'].encode('ascii')}

        response = self.app.get(
            url=toolkit.url_for('issues_show',
                                dataset_id=self.dataset['id'],
                                issue_number=self.issue['number']),
            extra_environ=env,
        )

        soup = bs4.BeautifulSoup(response.body)
        edit_button = soup.find('div', {'id': 'issue-edit-button'})
        assert_is_not_none(edit_button)

    def test_edit_button_does_not_appear_for_unauthorized_user(self):
        user = factories.User()
        env = {'REMOTE_USER': user['name'].encode('ascii')}

        response = self.app.get(
            url=toolkit.url_for('issues_show',
                                dataset_id=self.dataset['id'],
                                issue_number=self.issue['number']),
            extra_environ=env,
        )

        soup = bs4.BeautifulSoup(response.body)
        edit_button = soup.find('div', {'id': 'issue-edit-button'})
        assert_is_none(edit_button)
