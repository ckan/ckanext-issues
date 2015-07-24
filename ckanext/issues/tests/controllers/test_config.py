'''Test config options

ckanext.issues.enabled_for_datasets
ckanext.issues.enabled_per_dataset_default
'''
from ckan.plugins import toolkit
from ckan.new_tests import helpers, factories
from ckanext.issues.tests import factories as issue_factories

from nose.tools import assert_equals


class TestDatasetList(helpers.FunctionalTestBase):
    def setup(self):
        super(TestDatasetList, self).setup()
        self.owner = factories.User()
        self.org = factories.Organization(user=self.owner)
        self.dataset = factories.Dataset(user=self.owner,
                                         owner_org=self.org['id'],
                                         name='test-dataset',
                                         )
        self.dataset_1 = factories.Dataset(
            user=self.owner,
            extras=[{
                'key': 'issues_enabled',
                'value': True
            }],
            owner_org=self.org['name']
        )
        self.issue = issue_factories.Issue(user=self.owner,
                                           user_id=self.owner['id'],
                                           dataset_id=self.dataset['id'],
                                           visibility='hidden')
        self.app = self._get_test_app()

    @classmethod
    def _apply_config_changes(cls, config):
        config['ckanext.issues.enabled_for_datasets'] = 'test-dataset'

    def test_issues_enabled_for_test_dataset(self):
        env = {'REMOTE_USER': self.owner['name'].encode('ascii')}
        response = self.app.get(
            url=toolkit.url_for('issues_dataset',
                                dataset_id=self.dataset['id']),
            extra_environ=env,
        )
        assert_equals(200, response.status_int)

    def test_issues_disabled_for_test_dataset_1(self):
        '''test that issues are disabled even with the extra issues_enabled

        set'''
        env = {'REMOTE_USER': self.owner['name'].encode('ascii')}
        response = self.app.get(
            url=toolkit.url_for('issues_dataset',
                                dataset_id=self.dataset_1['id']),
            extra_environ=env,
            expect_errors=True
        )
        assert_equals(404, response.status_int)


class TestDatasetExtra(helpers.FunctionalTestBase):
    def setup(self):
        super(TestDatasetExtra, self).setup()
        self.owner = factories.User()
        self.org = factories.Organization(user=self.owner)
        self.dataset = factories.Dataset(user=self.owner,
                                         owner_org=self.org['id'],
                                         name='test-dataset')

        self.dataset_1 = factories.Dataset(
            user=self.owner,
            extras=[{
                'key': 'issues_enabled',
                'value': True
            }],
            owner_org=self.org['name']
        )
        self.issue = issue_factories.Issue(user=self.owner,
                                           user_id=self.owner['id'],
                                           dataset_id=self.dataset['id'],
                                           visibility='hidden')
        self.app = self._get_test_app()

    @classmethod
    def _apply_config_changes(cls, config):
        config['ckanext.issues.enabled_per_dataset_default'] = 'false'

    def test_issues_disabled_for_test_dataset(self):
        '''test-dataset has no extra'''
        env = {'REMOTE_USER': self.owner['name'].encode('ascii')}
        response = self.app.get(
            url=toolkit.url_for('issues_dataset',
                                dataset_id=self.dataset['id']),
            extra_environ=env,
            expect_errors=True
        )
        assert_equals(404, response.status_int)

    def test_issues_enabled_for_test_dataset_1(self):
        env = {'REMOTE_USER': self.owner['name'].encode('ascii')}
        response = self.app.get(
            url=toolkit.url_for('issues_dataset',
                                dataset_id=self.dataset_1['id']),
            extra_environ=env,
        )
        assert_equals(200, response.status_int)
