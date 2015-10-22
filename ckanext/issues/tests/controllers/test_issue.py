from ckan.plugins import toolkit
import ckan.new_tests.helpers as helpers
import ckan.new_tests.factories as factories

from ckanext.issues.tests import factories as issue_factories

import bs4
from nose.tools import (assert_equals, assert_is_not_none, assert_is_none,
                        assert_raises, assert_not_in)


class TestIssuesController(helpers.FunctionalTestBase):
    def test_unauthorized_users_cannot_see_issues_on_a_dataset(self):
        '''test that a 401 is returned, previously this would just 500'''
        user = factories.User()
        org = factories.Organization(user=user)
        dataset = factories.Dataset(user=user, owner_org=org['name'],
                                    private=True)
        issue = issue_factories.Issue(user=user,
                                      user_id=user['id'],
                                      dataset_id=dataset['id'])
        unauthorized_user = factories.User()

        app = self._get_test_app()
        env = {'REMOTE_USER': unauthorized_user['name'].encode('ascii')}

        response = app.get(
            url=toolkit.url_for('issues_show',
                                dataset_id=dataset['id'],
                                issue_number=issue['number']),
            extra_environ=env,
            expect_errors=True
        )
        assert_equals(response.status_int, 401)


class TestIssuesControllerUpdate(helpers.FunctionalTestBase):
    def test_user_cannot_edit_another_users_issue(self):
        owner = factories.User()
        user = factories.User()
        org = factories.Organization(user=owner)
        dataset = factories.Dataset(user=owner, owner_org=org['name'])
        issue = issue_factories.Issue(user=owner, dataset_id=dataset['id'])

        app = self._get_test_app()
        env = {'REMOTE_USER': user['name'].encode('ascii')}

        response = app.post(
            url=toolkit.url_for('issues_edit',
                                dataset_id=dataset['id'],
                                issue_number=issue['number']),
            params={'title': 'edit', 'description': 'edited description'},
            extra_environ=env,
            expect_errors=True
        )
        assert_equals(response.status_int, 401)


class TestShow(helpers.FunctionalTestBase):
    def setup(self):
        super(TestShow, self).setup()
        self.owner = factories.User()
        self.org = factories.Organization(user=self.owner)
        self.dataset = factories.Dataset(user=self.owner,
                                         owner_org=self.org['name'])
        self.app = self._get_test_app()

    def test_not_found_issue_raises_404(self):
        env = {'REMOTE_USER': self.owner['name'].encode('ascii')}
        response = self.app.get(
            url=toolkit.url_for('issues_show',
                                dataset_id=self.dataset['id'],
                                issue_number='some nonsense'),
            extra_environ=env,
            expect_errors=True,
        )
        assert_equals(response.status_int, 404)

    def test_issue_show_with_non_existing_package_404s(self):
        env = {'REMOTE_USER': self.owner['name'].encode('ascii')}
        response = self.app.get(
            url=toolkit.url_for('issues_show',
                                dataset_id='does not exist',
                                issue_number=1),
            extra_environ=env,
            expect_errors=True,
        )
        assert_equals(response.status_int, 404)


class TestDelete(helpers.FunctionalTestBase):
    def setup(self):
        super(TestDelete, self).setup()
        self.owner = factories.User()
        self.org = factories.Organization(user=self.owner)
        self.dataset = factories.Dataset(user=self.owner,
                                         owner_org=self.org['name'])
        self.issue = issue_factories.Issue(user=self.owner,
                                           user_id=self.owner['id'],
                                           dataset_id=self.dataset['id'])
        self.app = self._get_test_app()

    def test_delete(self):
        env = {'REMOTE_USER': self.owner['name'].encode('ascii')}
        response = self.app.post(
            url=toolkit.url_for('issues_delete',
                                dataset_id=self.dataset['id'],
                                issue_number=self.issue['number']),
            extra_environ=env,
        )
        # check we get redirected back to the issues overview page
        assert_equals(302, response.status_int)
        response = response.follow()
        assert_equals(200, response.status_int)
        assert_equals(
            toolkit.url_for('issues_dataset', dataset_id=self.dataset['id']),
            response.request.path
        )
        # check the issue is now deleted.
        assert_raises(toolkit.ObjectNotFound,
                      helpers.call_action,
                      'issue_show',
                      issue_number=self.issue['number'],
                      dataset_id=self.dataset['id'])

    def test_delete_unauthed_401s(self):
        user = factories.User()
        env = {'REMOTE_USER': user['name'].encode('ascii')}
        response = self.app.post(
            url=toolkit.url_for('issues_delete',
                                dataset_id=self.dataset['id'],
                                issue_number=self.issue['number']),
            extra_environ=env,
            expect_errors=True
        )
        assert_equals(401, response.status_int)

    def test_delete_button_appears_for_authed_user(self):
        env = {'REMOTE_USER': self.owner['name'].encode('ascii')}
        response = self.app.get(
            url=toolkit.url_for('issues_show',
                                dataset_id=self.dataset['id'],
                                issue_number=self.issue['number']),
            extra_environ=env,
        )
        form = response.forms['issue-comment-form']
        soup = bs4.BeautifulSoup(form.text)
        delete_link = soup.find_all('a')[-1]
        # check the link of the delete
        assert_equals('Delete', delete_link.text)
        assert_equals(
            toolkit.url_for('issues_delete',
                            dataset_id=self.dataset['id'],
                            issue_number=self.issue['number']),
            delete_link.attrs['href']
        )

    def test_delete_confirm_page(self):
        '''test the confirmation page renders and cancels correctly'''
        env = {'REMOTE_USER': self.owner['name'].encode('ascii')}
        response = self.app.get(
            url=toolkit.url_for('issues_delete',
                                dataset_id=self.dataset['id'],
                                issue_number=self.issue['number']),
            extra_environ=env,
        )
        form = response.forms['ckanext-issues-confirm-delete']
        # check the form target
        assert_equals(
            toolkit.url_for('issues_delete',
                            dataset_id=self.dataset['id'],
                            issue_number=self.issue['number']),
            form.action
        )
        assert_equals([u'cancel', u'delete'], form.fields.keys())
        response = helpers.submit_and_follow(self.app, form, env, 'cancel')
        # check we have been redirected without deletion
        assert_equals(
            toolkit.url_for('issues_show',
                            dataset_id=self.dataset['id'],
                            issue_number=self.issue['number']),
            response.request.path_qs
        )

    def test_delete_button_not_present_for_unauthed_user(self):
        user = factories.User()
        env = {'REMOTE_USER': user['name'].encode('ascii')}
        response = self.app.get(
            url=toolkit.url_for('issues_show',
                                dataset_id=self.dataset['id'],
                                issue_number=self.issue['number']),
            extra_environ=env,
        )
        form = response.forms['issue-comment-form']
        assert_not_in('Delete', form.text)


class TestOrganization(helpers.FunctionalTestBase):
    def setup(self):
        super(TestOrganization, self).setup()
        self.owner = factories.User()
        self.org = factories.Organization(user=self.owner)
        self.dataset = factories.Dataset(user=self.owner,
                                         owner_org=self.org['name'])
        self.issue = issue_factories.Issue(user=self.owner,
                                           user_id=self.owner['id'],
                                           dataset_id=self.dataset['id'])
        self.app = self._get_test_app()

    def test_basic(self):
        env = {'REMOTE_USER': self.owner['name'].encode('ascii')}
        response = self.app.get(
            url=toolkit.url_for('issues_for_organization',
                                org_id=self.org['id']),
            extra_environ=env
        )
        soup = bs4.BeautifulSoup(response.body)
        issues = soup.find('section', {'class': 'issues-home'}).text
        assert '1 issue found' in issues
        issue_page = soup.find('div', {'id': 'issue-page'}).text
        assert self.dataset['title'] in issue_page
        assert self.issue['title'] in issue_page
        assert self.issue['description'] not in issue_page
