try:
    from ckan.lib.search import clear_all
except ImportError:
    # clear_all is clear() < 2.5
    from ckan.lib.search import clear as clear_all
try:
    from ckan.tests import helpers
except ImportError:
    from ckan.new_tests import helpers


class ClearOnSetupClassMixin(object):
    @classmethod
    def setupClass(self):
        helpers.reset_db()
        clear_all()


class ClearOnTearDownMixin(object):
    def teardown(self):
        helpers.reset_db()
        clear_all()
