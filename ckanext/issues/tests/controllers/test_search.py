from ckan.plugins import toolkit
try:
    from ckan.tests import helpers
    from ckan.tests import factories
except ImportError:
    from ckan.new_tests import helpers
    from ckan.new_tests import factories

from ckanext.issues.tests import factories as issue_factories
from ckanext.issues import model as issue_model
from nose.tools import (assert_is_not_none, assert_equals, assert_in,
                        assert_not_in)

import bs4


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

    def test_search_box_appears_issue_dataset_page(self):
        response = self.app.get(
            url=toolkit.url_for('issues_dataset',
                                dataset_id=self.dataset['id'],
                                issue_number=self.issue['number']),
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

        issue_dataset = self.app.get(
            url=toolkit.url_for('issues_dataset',
                                dataset_id=self.dataset['id'],
                                issue_number=self.issue['number']),
        )

        search_form = issue_dataset.forms[1]
        search_form['q'] = 'title'

        res = search_form.submit()
        soup = bs4.BeautifulSoup(res.body)
        issue_links = soup.find(id='issue-list').find_all('h4')
        titles = set([i.a.text.strip() for i in issue_links])
        assert_equals(set([i['title'] for i in in_search]), titles)


class TestSearchFilters(helpers.FunctionalTestBase):
    def setup(self):
        super(TestSearchFilters, self).setup()
        self.owner = factories.User()
        self.org = factories.Organization(user=self.owner)
        self.dataset = factories.Dataset(user=self.owner,
                                         owner_org=self.org['name'])
        self.issues = {
            'visible': issue_factories.Issue(user=self.owner,
                                             title='visible_issue',
                                             dataset_id=self.dataset['id']),
            'closed': issue_factories.Issue(user=self.owner,
                                            title='closed_issue',
                                            dataset_id=self.dataset['id']),
            'hidden': issue_factories.Issue(user=self.owner,
                                            title='hidden_issue',
                                            dataset_id=self.dataset['id'],
                                            spam_state='hidden'),
        }
        # close our issue
        helpers.call_action(
            'issue_update',
            issue_number=self.issues['closed']['number'],
            dataset_id=self.dataset['id'],
            context={'user': self.owner['name']},
            status='closed'
        )
        issue = issue_model.Issue.get(self.issues['hidden']['id'])
        issue.spam_state = 'hidden'
        issue.save()

        self.app = self._get_test_app()

    def test_click_visiblity_links(self):
        env = {'REMOTE_USER': self.owner['name'].encode('ascii')}
        response = self.app.get(
            url=toolkit.url_for('issues_dataset',
                                dataset_id=self.dataset['id']),
            extra_environ=env,
        )
        # visible and hidden should be shown, but not closed
        assert_in('2 issues found', response)
        assert_in('visible_issue', response)
        assert_in('hidden_issue', response)
        assert_not_in('closed_issue', response)

        # click the hidden filter
        response = response.click(linkid='hidden-filter', extra_environ=env)
        assert_in('1 issue found', response)
        assert_not_in('visible_issue', response)
        assert_in('hidden_issue', response)
        assert_not_in('closed_issue', response)

        # click the visible filter
        response = response.click(linkid='visible-filter', extra_environ=env)
        assert_in('1 issue found', response)
        assert_in('visible_issue', response)
        assert_not_in('hidden_issue', response)
        assert_not_in('closed_issue', response)

        # clear the filter by clikcing on visible again
        response = response.click(linkid='visible-filter', extra_environ=env)
        assert_in('2 issues found', response)
        assert_in('visible_issue', response)
        assert_in('hidden_issue', response)
        assert_not_in('closed_issue', response)

    def test_click_status_links(self):
        env = {'REMOTE_USER': self.owner['name'].encode('ascii')}
        response = self.app.get(
            url=toolkit.url_for('issues_dataset',
                                dataset_id=self.dataset['id']),
            extra_environ=env,
        )
        # visible and hidden should be shown, but not closed
        assert_in('2 issues found', response)
        assert_in('visible_issue', response)
        assert_in('hidden_issue', response)
        assert_not_in('closed_issue', response)

        # click the closed filter
        response = response.click(linkid='closed-filter', extra_environ=env)
        assert_in('1 issue found', response)
        assert_not_in('visible_issue', response)
        assert_not_in('hidden_issue', response)
        assert_in('closed_issue', response)

        # click the open filter
        response = response.click(linkid='open-filter', extra_environ=env)
        assert_in('2 issues found', response)
        assert_in('visible_issue', response)
        assert_in('hidden_issue', response)
        assert_not_in('closed_issue', response)

    def test_visiblity_links_do_not_appear_for_unauthed_user(self):
        response = self.app.get(
            url=toolkit.url_for('issues_dataset',
                                dataset_id=self.dataset['id']),
        )
        assert_not_in('filter-hidden', response)
        assert_not_in('filter-visible', response)
