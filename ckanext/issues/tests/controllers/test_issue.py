from ckan.lib import search
from ckan.plugins import toolkit
import ckan.new_tests.helpers as helpers
import ckan.new_tests.factories as factories

from ckanext.issues.tests import factories as issue_factories

import bs4
from nose.tools import (assert_equals, assert_is_not_none, assert_is_none,
                        assert_raises, assert_in, assert_not_in)


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
                                package_id=dataset['id'],
                                id=issue['id']),
            params={'title': 'edit', 'description': 'edited description'},
            extra_environ=env,
            expect_errors=True
        )
        assert_equals(response.status_int, 401)


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
                                package_id=self.dataset['id'],
                                id=self.issue['id']),
            extra_environ=env,
            expect_errors=True
        )

        soup = bs4.BeautifulSoup(response.body)
        edit_button = soup.find('div', {'class': 'issue-edit-button'})
        assert_is_not_none(edit_button)

    def test_edit_button_does_not_appear_for_unauthorized_user(self):
        user = factories.User()
        env = {'REMOTE_USER': user['name'].encode('ascii')}

        response = self.app.get(
            url=toolkit.url_for('issues_show',
                                package_id=self.dataset['id'],
                                id=self.issue['id']),
            extra_environ=env,
            expect_errors=True
        )

        soup = bs4.BeautifulSoup(response.body)
        edit_button = soup.find('div', {'class': 'issue-edit-button'})
        assert_is_none(edit_button)


class TestSearchBox(helpers.FunctionalTestBase):
    def setup(self):
        super(TestSearchBox, self).setup()
        self.owner = factories.User()
        self.org = factories.Organization(user=self.owner)
        self.dataset = factories.Dataset(user=self.owner,
                                         owner_org=self.org['name'])
        self.issue = issue_factories.Issue(user=self.owner,
                                           dataset_id=self.dataset['id'])

        self.app = self._get_test_app()

    def test_search_box_appears_issue_home_page(self):
        response = self.app.get(
            url=toolkit.url_for('issues_home',
                                package_id=self.dataset['id'],
                                id=self.issue['id']),
        )

        soup = bs4.BeautifulSoup(response.body)
        edit_button = soup.find('form', {'class': 'search-form'})
        assert_is_not_none(edit_button)

    def test_search_box_submits_q_get(self):
        in_search = [issue_factories.Issue(user_id=self.owner['id'],
                                           dataset_id=self.dataset['id'],
                                           title=title)
                     for title in ['some titLe', 'another Title']]

        # some issues not in the search
        [issue_factories.Issue(user_id=self.owner['id'],
                               dataset_id=self.dataset['id'],
                               title=title)
         for title in ['blah', 'issue']]

        issue_home = self.app.get(
            url=toolkit.url_for('issues_home',
                                package_id=self.dataset['id'],
                                id=self.issue['id']),
        )

        search_form = issue_home.forms[1]
        search_form['q'] = 'title'

        res = search_form.submit()
        soup = bs4.BeautifulSoup(res.body)
        issue_links = soup.find(id='issue-list').find_all('h4')
        titles = set([i.a.text for i in issue_links])
        assert_equals(set([i['title'] for i in in_search]), titles)


class TestShow(helpers.FunctionalTestBase):
    def setup(self):
        super(TestShow, self).setup()
        self.owner = factories.User()
        self.org = factories.Organization(user=self.owner)
        self.dataset = factories.Dataset(user=self.owner,
                                         owner_org=self.org['name'])
        self.app = self._get_test_app()

    def teardown(self):
        helpers.reset_db()
        search.clear()

    def test_not_found_issue_raises_404(self):
        env = {'REMOTE_USER': self.owner['name'].encode('ascii')}
        response = self.app.get(
            url=toolkit.url_for('issues_show', package_id=self.dataset['id'],
                                id='some nonsense'),
            extra_environ=env,
            expect_errors=True,
        )
        assert_equals(response.status_int, 404)

    def test_issue_show_with_non_existing_package_404s(self):
        env = {'REMOTE_USER': self.owner['name'].encode('ascii')}
        response = self.app.get(
            url=toolkit.url_for('issues_show',
                                package_id='does not exist',
                                id=1),
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

    def teardown(self):
        helpers.reset_db()
        search.clear()

    def test_delete(self):
        env = {'REMOTE_USER': self.owner['name'].encode('ascii')}
        response = self.app.post(
            url=toolkit.url_for('issues_delete', dataset_id=self.dataset['id'],
                                issue_id=self.issue['id']),
            extra_environ=env,
        )
        # check we get redirected back to the issues overview page
        assert_equals(302, response.status_int)
        response = response.follow()
        assert_equals(200, response.status_int)
        assert_equals(
            toolkit.url_for('issues_home', package_id=self.dataset['id']),
            response.request.path
        )
        # check the issue is now deleted.
        assert_raises(toolkit.ObjectNotFound, helpers.call_action,
                      'issue_show', id=self.issue['id'])

    def test_delete_unauthed_401s(self):
        user = factories.User()
        env = {'REMOTE_USER': user['name'].encode('ascii')}
        response = self.app.post(
            url=toolkit.url_for('issues_delete', dataset_id=self.dataset['id'],
                                issue_id=self.issue['id']),
            extra_environ=env,
            expect_errors=True
        )
        assert_equals(401, response.status_int)


    def test_delete_button_appears_for_authed_user(self):
        env = {'REMOTE_USER': self.owner['name'].encode('ascii')}
        response = self.app.get(
            url=toolkit.url_for('issues_show', package_id=self.dataset['id'],
                                id=self.issue['id']),
            extra_environ=env,
        )
        form = response.forms['issue-comment-form']
        soup = bs4.BeautifulSoup(form.text)
        delete_link = soup.find_all('a')[-1]
        # check the link of the delete
        assert_equals('Delete', delete_link.text)
        assert_equals(
            toolkit.url_for('issues_delete', dataset_id=self.dataset['id'],
                            issue_id=self.issue['id']),
            delete_link.attrs['href']
        )

    def test_delete_confirm_page(self):
        '''test the confirmation page renders and cancels correctly'''
        env = {'REMOTE_USER': self.owner['name'].encode('ascii')}
        response = self.app.get(
            url=toolkit.url_for('issues_delete', dataset_id=self.dataset['id'],
                                issue_id=self.issue['id']),
            extra_environ=env,
        )
        form = response.forms['ckanext-issues-confirm-delete']
        # check the form target
        assert_equals(
            toolkit.url_for('issues_delete', dataset_id=self.dataset['id'],
                            issue_id=self.issue['id']),
            form.action
        )
        assert_equals([u'cancel', u'delete'], form.fields.keys())
        response = helpers.submit_and_follow(self.app, form, env, 'cancel')
        # check we have been redirected without deletion
        assert_equals(
            toolkit.url_for('issues_show', package_id=self.dataset['id'],
                            id=self.issue['id']),
            response.request.path_qs
        )

    def test_delete_button_not_present_for_unauthed_user(self):
        user = factories.User()
        env = {'REMOTE_USER': user['name'].encode('ascii')}
        response = self.app.get(
            url=toolkit.url_for('issues_show', package_id=self.dataset['id'],
                                id=self.issue['id']),
            extra_environ=env,
        )
        form = response.forms['issue-comment-form']
        assert_not_in('Delete', form.text)
