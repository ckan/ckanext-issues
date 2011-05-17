import json
from paste.deploy import appconfig
import paste.fixture
from ckan.config.middleware import make_app
from ckan.tests import conf_dir, url_for, CreateTestData, TestController
from testdata import CreateTodoTestData

class TestTodoController(TestController):
    @classmethod
    def setup_class(cls):
        config = appconfig('config:test.ini', relative_to=conf_dir)
        config.local_conf['ckan.plugins'] = 'todo'
        wsgiapp = make_app(config.global_conf, **config.local_conf)
        cls.app = paste.fixture.TestApp(wsgiapp)
        CreateTestData.create()
        CreateTodoTestData.create()

    @classmethod
    def teardown_class(self):
        CreateTestData.delete()
        CreateTodoTestData.delete()

    def test_get(self):
        """
        Tests that a GET request to the 'todo' controller returns a
        JSON formatted response, with 0 items.
        """
        response = self.app.get(url_for('todo'))
        # make sure that the response content type is JSON
        assert response.header('Content-Type') == "application/json" ,\
            "controller not returning a JSON object"
        # parse the JSON response and check the values
        json_response = json.loads(response.body)
        print response.body
        assert len(json_response) == 0
