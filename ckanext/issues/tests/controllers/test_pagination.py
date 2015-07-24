from ckan.plugins import toolkit
try:
    from ckan.tests import helpers
    from ckan.tests import factories
except ImportError:
    from ckan.new_tests import helpers
    from ckan.new_tests import factories

from ckanext.issues import model as issue_model
from ckanext.issues.controller.controller import ISSUES_PER_PAGE
from ckanext.issues.tests import factories as issue_factories
from nose.tools import (assert_is_not_none, assert_equals, assert_in,
                        assert_not_in)


class TestPagination(helpers.FunctionalTestBase):
    def setup(self):
        super(TestPagination, self).setup()
        self.owner = factories.User()
        self.org = factories.Organization(user=self.owner)
        self.dataset = factories.Dataset(user=self.owner,
                                         owner_org=self.org['name'])
        self.issues = [
            issue_factories.Issue(user=self.owner,
                                  dataset_id=self.dataset['id'])
            for x in range(0, 51)
        ]
        self.app = self._get_test_app()

    def test_click_per_page_link(self):
        response = self.app.get(
            url=toolkit.url_for(
                'issues_dataset',
                dataset_id=self.dataset['id'],
                sort='oldest',
            ),
        )
        for per_page in ISSUES_PER_PAGE:
            response = response.click(linkid='per-page-{0}'.format(per_page))
            for i in self.issues[:per_page]:
                assert_in(i['title'], response)
            for i in self.issues[per_page:]:
                assert_not_in(i['title'], response)

    def test_next_button(self):
        for per_page in ISSUES_PER_PAGE:
            response = self.app.get(
                url=toolkit.url_for(
                    'issues_dataset',
                    dataset_id=self.dataset['id'],
                    sort='oldest',
                    per_page=per_page
                ),
            )
            self.click_through_all_pages_using_next_button(response, per_page)

    def click_through_all_pages_using_next_button(self, response, step):
        num_issues = len(self.issues)
        pages = num_issues / step

        for page, x in enumerate(range(0, num_issues, step)):
            for i in self.issues[x:x+step]:
                assert_in(i['title'], response)

            for i in self.issues[:x]:
                assert_not_in(i['title'], response)

            for i in self.issues[x+step:]:
                assert_not_in(i['title'], response)

            if page != pages:
                # we're on the last page, so there is no link to click
                response = response.click(linkid='pagination-next-link')
