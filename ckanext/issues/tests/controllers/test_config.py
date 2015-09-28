'''Test config options
'''
from ckan.plugins import toolkit
from ckan.new_tests import helpers, factories
from ckanext.issues.tests import factories as issue_factories

from nose.tools import assert_equals


class TestEnabledForDatasets(helpers.FunctionalTestBase):
    def setup(self):
        super(TestEnabledForDatasets, self).setup()
        self.dataset = factories.Dataset()
        self.dataset_enabled = factories.Dataset(name='dataset-enabled')
        self.dataset_misleading_extra = \
            factories.Dataset(
                extras=[{
                    'key': 'issues_enabled',
                    'value': True
                }],
                )
        self.app = self._get_test_app()

    @classmethod
    def _apply_config_changes(cls, config):
        config['ckanext.issues.enabled_for_datasets'] = 'dataset-enabled'

    def test_dataset_enabled_by_config(self):
        self.app.get(toolkit.url_for('issues_dataset',
                                     dataset_id=self.dataset_enabled['id']),
                     status=200)

    def test_other_datasets_disabled(self):
        self.app.get(toolkit.url_for('issues_dataset',
                                     dataset_id=self.dataset['id']),
                     status=404)

    def test_cant_enable_with_extra_with_this_config(self):
        '''test that issues are disabled even with the extra issues_enabled
        set'''
        self.app.get(toolkit.url_for(
            'issues_dataset',
            dataset_id=self.dataset_misleading_extra['id']),
            status=404)


class TestEnabledForOrganizations(helpers.FunctionalTestBase):
    def setup(self):
        super(TestEnabledForOrganizations, self).setup()
        self.dataset = factories.Dataset()
        self.org = factories.Organization(name='org')
        self.enabled_org = factories.Organization(name='enabled-org')
        self.dataset_enabled = factories.Dataset(
            name='dataset-enabled', owner_org=self.enabled_org['id'])
        self.dataset_misleading_extra = \
            factories.Dataset(
                extras=[{
                    'key': 'issues_enabled',
                    'value': True
                }],
                )
        self.app = self._get_test_app()

    @classmethod
    def _apply_config_changes(cls, config):
        config['ckanext.issues.enabled_for_organizations'] = 'enabled-org'
        # try and confuse it with also enabling another dataset
        config['ckanext.issues.enabled_for_datasets'] = 'random-dataset'

    def test_dataset_enabled_by_config(self):
        self.app.get(toolkit.url_for('issues_dataset',
                                     dataset_id=self.dataset_enabled['id']),
                     status=200)

    def test_other_datasets_disabled(self):
        self.app.get(toolkit.url_for('issues_dataset',
                                     dataset_id=self.dataset['id']),
                     status=404)

    def test_org_enabled_by_config(self):
        self.app.get(toolkit.url_for('issues_for_organization',
                                     org_id=self.enabled_org['id']),
                     status=200)

    def test_other_orgs_disabled(self):
        self.app.get(toolkit.url_for('issues_for_organization',
                                     org_id=self.org['id']),
                     status=404)

    def test_cant_enable_dataset_with_extra_with_this_config(self):
        '''test that issues are disabled even with the extra issues_enabled
        set'''
        self.app.get(toolkit.url_for(
            'issues_dataset',
            dataset_id=self.dataset_misleading_extra['id']),
            status=404)


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
        config['ckanext.issues.enabled_without_extra'] = 'false'

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
