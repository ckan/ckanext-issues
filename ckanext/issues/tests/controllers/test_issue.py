from ckan.lib import search
from ckan.plugins import toolkit
import ckan.new_tests.helpers as helpers
import ckan.new_tests.factories as factories

from ckanext.issues.tests import factories as issue_factories

import bs4
from nose.tools import assert_equals, assert_is_not_none, assert_is_none


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

        not_in_search = [issue_factories.Issue(user_id=self.owner['id'],
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
        super(TestShow, self).setup()
        import ipdb; ipdb.set_trace()
        env = {'REMOTE_USER': self.owner['name'].encode('ascii')}
        response = self.app.get(
            url=toolkit.url_for('issues_show',
                                package_id=self.dataset['id'],
                                id=1),
            extra_environ=env,
            expect_errors=True,
        )
        assert_equals(response.status_int, 404)

    def test_issue_show_with_non_existing_package_404s(self):
        super(TestShow, self).setup()
        env = {'REMOTE_USER': self.owner['name'].encode('ascii')}
        response = self.app.get(
            url=toolkit.url_for('issues_show',
                                package_id='does not exist',
                                id=1),
            extra_environ=env,
            expect_errors=True,
        )
        assert_equals(response.status_int, 404)
