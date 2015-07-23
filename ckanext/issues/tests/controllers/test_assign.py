from bs4 import BeautifulSoup
from nose.tools import assert_equals, assert_in

from ckan.lib import search
from ckan.plugins import toolkit
import ckan.new_tests.helpers as helpers
import ckan.new_tests.factories as factories

from ckanext.issues.tests import factories as issue_factories


class TestAssign(helpers.FunctionalTestBase):
    def setup(self):
        super(TestAssign, self).setup()
        self.owner = factories.User()
        self.org = factories.Organization(user=self.owner)
        self.dataset = factories.Dataset(user=self.owner,
                                         owner_org=self.org['id'])
        self.issue = issue_factories.Issue(user=self.owner,
                                           user_id=self.owner['id'],
                                           dataset_id=self.dataset['id'])
        self.app = self._get_test_app()

    def teardown(self):
        helpers.reset_db()
        search.clear()

    def test_user_self_assign(self):
        env = {'REMOTE_USER': self.owner['name'].encode('ascii')}
        response = self.app.get(
            url=toolkit.url_for('issues_show',
                                dataset_id=self.dataset['id'],
                                issue_number=self.issue['number']),
            extra_environ=env,
        )
        form = response.forms['ckanext-issues-assign']
        form['assignee'] = self.owner['name']
        response = helpers.submit_and_follow(self.app, form, env)
        soup = BeautifulSoup(response.body)

        assignee = soup.find(id='ckanext-issues-assignee').text.strip()
        assert_equals(self.owner['name'], assignee)

    def test_assign_an_editor_to_an_issue(self):
        editor = factories.User()
        test = helpers.call_action(
            'member_create',
            id=self.org['id'],
            object=editor['id'],
            object_type='user',
            capacity='editor'
        )

        env = {'REMOTE_USER': editor['name'].encode('ascii')}
        response = self.app.get(
            url=toolkit.url_for('issues_show',
                                dataset_id=self.dataset['id'],
                                issue_number=self.issue['number']),
            extra_environ=env,
        )
        form = response.forms['ckanext-issues-assign']
        form['assignee'] = editor['name']
        response = helpers.submit_and_follow(self.app, form, env)
        soup = BeautifulSoup(response.body)

        assignee = soup.find(id='ckanext-issues-assignee').text.strip()
        assert_equals(editor['name'], assignee)

    def test_standard_user_cannot_assign(self):
        user = factories.User()
        env = {'REMOTE_USER': user['name'].encode('ascii')}
        response = self.app.post(
            toolkit.url_for('issues_assign',
                            dataset_id=self.dataset['id'],
                            issue_number=self.issue['number']),
            {'assignee': user['name']},
            extra_environ=env,
            expect_errors=True
        )

        assert_equals(401, response.status_int)

    def test_cannot_assign_an_issue_that_does_not_exist(self):
        env = {'REMOTE_USER': self.owner['name'].encode('ascii')}
        response = self.app.post(
            toolkit.url_for('issues_assign',
                            dataset_id=self.dataset['id'],
                            issue_number='not an issue'),
            {'assignee': self.owner['name']},
            extra_environ=env,
            expect_errors=True
        )

        assert_equals(404, response.status_int)

    def test_assign_form_does_not_appear_for_unauthorized_user(self):
        user = factories.User()
        env = {'REMOTE_USER': user['name'].encode('ascii')}
        response = self.app.get(
            url=toolkit.url_for('issues_show',
                                dataset_id=self.dataset['id'],
                                issue_number=self.issue['number']),
            extra_environ=env,
        )
        try:
            form = response.forms['ckanext-issues-assign']
            raise Exception('form has appeared when it should not have')
        except KeyError:
            pass

    def test_assign_form_does_not_appear_for_anon_user(self):
        env = {'REMOTE_USER': self.owner['name'].encode('ascii')}
        response = self.app.get(
            url=toolkit.url_for('issues_show',
                                dataset_id=self.dataset['id'],
                                issue_number=self.issue['number']),
        )
        try:
            form = response.forms['ckanext-issues-assign']
            raise Exception('form has appeared when it should not have')
        except KeyError:
            pass

    def test_cannot_assign_if_user_does_not_exist(self):
        env = {'REMOTE_USER': self.owner['name'].encode('ascii')}
        response = self.app.get(
            url=toolkit.url_for('issues_show',
                                dataset_id=self.dataset['id'],
                                issue_number=self.issue['number']),
            extra_environ=env,
        )
        form = response.forms['ckanext-issues-assign']
        form['assignee'] = 'not a user'
        response = helpers.submit_and_follow(self.app, form, env)
        assert_in('User not a user does not exist', response)

    def test_issue_creator_cannot_assign_if_they_cannot_package_update(self):
        user = factories.User()
        issue = issue_factories.Issue(user=user,
                                      user_id=user['id'],
                                      dataset_id=self.dataset['id'])
        env = {'REMOTE_USER': user['name'].encode('ascii')}
        response = self.app.post(
            toolkit.url_for('issues_assign',
                            dataset_id=self.dataset['id'],
                            issue_number=self.issue['number']),
            {'assignee': user['name']},
            extra_environ=env,
            expect_errors=True
        )

        assert_equals(401, response.status_int)
