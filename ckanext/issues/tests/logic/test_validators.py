from ckan import model
from ckan.lib import search
from ckan.new_tests import factories, helpers
from ckanext.issues.logic import validators

from nose.tools import assert_equals

class TestAsPackageId(object):
    def setup(self):
        self.dataset = factories.Dataset()

    def teardown(self):
        helpers.reset_db()
        search.clear()

    def test_given_name_returns_id(self):
        package_id = validators.as_package_id(self.dataset['name'], 
                                              context={
                                                  'model': model,
                                                  'session': model.Session})
        assert_equals(self.dataset['id'], package_id)

    def test_given_id_returns_id(self):
        package_id = validators.as_package_id(self.dataset['id'], 
                                              context={
                                                  'model': model,
                                                  'session': model.Session})
        assert_equals(self.dataset['id'], package_id)
