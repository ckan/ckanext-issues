'''Test the Issues Extension
'''
import paste.fixture
import pylons.test
import pylons.config as config
import webtest
from routes import url_for

import ckan.model as model
import ckanext.issues.model as issuemodel
import ckan.logic as logic
import ckan.tests as tests
import ckan.plugins
import ckan.new_tests.factories as factories
from ckan.tests.html_check import HtmlCheckMethods

class TestLogic(object):
    @classmethod
    def setup_class(self):
        app = ckan.config.middleware.make_app(config['global_conf'], **config)
        self.app = webtest.TestApp(app)
        ckan.plugins.load('issues')
        ckan.tests.CreateTestData.create()
        self.user = model.User.get('tester')
        # user who is not owner of the datasets
        self.otherUser = model.User(name='issues')
        model.Session.add(self.otherUser)
        model.Session.commit()
        self.dataset = model.Package.get('annakarenina')
        # test fixture
        self.context = {
            'model': model,
            'auth_user_obj': self.user,
            'user': self.user.name
        }
        # fixture issue
        self.issue = logic.get_action('issue_create')(self.context, {
            'title': 'General test issue',
            'description': 'Abc\n\n## Section',
            'dataset_id': self.dataset.id
        })
        self.issue2 = logic.get_action('issue_create')(self.context, {
            'title': 'General test issue 2',
            'description': '',
            'dataset_id': self.dataset.id
        })

    @classmethod
    def teardown_class(cls):
        ckan.plugins.unload('issues')
        model.repo.rebuild_db()

    def test_create_requires_auth(self):
        out = tests.call_action_api(self.app, 'issue_create', status=403)

    def test_create_fails_if_no_dataset(self):
        issue = {
            'title': u'A data issue',
            'description': u'xxx',
            'dataset_id': 'made-up'
        }
        out = tests.call_action_api(self.app, 'issue_create',
                apikey=self.user.apikey, status=409,
                **issue
                )
        assert out['dataset_id'] == ['No dataset exists with id made-up'] , out

    def test_create_ok(self):
        issue = {
            'title': u'A data issue',
            'description': u'xxx',
            'dataset_id': self.dataset.name
        }
        out = tests.call_action_api(self.app, 'issue_create',
                apikey=self.user.apikey, status=200,
                **issue
                )
        assert out['title'] == issue['title'], out
        assert out['dataset_id'] == self.dataset.id, out
        assert out['status'] == 'open'
        assert len(out['comments']) == 0

    def test_update(self):
        # Note no way to check permissions properly here as ...
        #
        # Default setup for testing is one in which all authenticated users
        # are "dataset editors" and hence can edit issues too (including
        # changing the status flag)
        #
        # Expected behaviour
        # Not-Auth user: NO
        # Dataset Editor: YES
        # Issue Owner (not Dataset Editor): YES but not status change

        # context with non-dataset owner user
        context = self._context(self.otherUser)
        issue = logic.get_action('issue_create')(context, {
            'title': 'General test issue',
            'description': 'Abc\n\n## Section',
            'dataset_id': self.dataset.id
        })
        newdata = dict(issue)
        newdata.update({
            'title': 'A new title',
            # should fail really but see above
            'status': issuemodel.ISSUE_STATUS.closed
            })

        updated = logic.get_action('issue_update')(context, newdata)
        assert updated['title'] == newdata['title'], updated
        assert updated['status'] == issuemodel.ISSUE_STATUS.closed
        assert updated['resolved'] != None
        assert updated['resolver_id'] == self.otherUser.id
        # TODO: test non owner user cannot update ...

    def _context(self, user):
        return {
            'model': model,
            'auth_user_obj': user,
            'user': user.name if user else None
        }

    # disabled as cannot properly test with default permission setup
    # see above note
    def _test_update_status_change(self):
        context = self._context(self.otherUser)
        # context with non-dataset owner user
        issue = logic.get_action('issue_create')(context, {
            'title': 'General test issue',
            'description': 'Abc\n\n## Section',
            'dataset_id': self.dataset.id
        })
        error = False
        newdata = dict(issue)
        newdata.update({
            'status': issuemodel.ISSUE_STATUS.closed
            })
        try:
            updated = logic.get_action('issue_update')(context, newdata)
        except logic.NotAuthorized:
            error = True
            pass
        assert error, 'Allowed unauthorized user to update issue'

        updated = logic.get_action('issue_update')(
                    self._context(self.tester), newdata)
        assert updated['status'] == issuemodel.ISSUE_STATUS.closed

    def test_show(self):
        new_issue_id = self.issue['id']
        out = tests.call_action_api(self.app, 'issue_show',
                apikey=self.user.apikey, status=200,
                id=new_issue_id
                )
        assert out['title'] == self.issue['title'], out
        assert len(out['comments']) == 0, out

    def test_create_comment(self):
        comment = {
            'comment': u'xxx',
            'issue_id': self.issue2['id']
        }
        out = tests.call_action_api(self.app, 'issue_comment_create',
                apikey=self.user.apikey,
                status=200,
                **comment
            )
        assert out['id'], out
        assert out['comment'] == comment['comment'], out

