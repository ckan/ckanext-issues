"""
Create test data for the CKAN Todo extension.
"""
from ckanext.todo import model
from ckan.model import repo

class CreateTodoTestData(object):
    @classmethod
    def create(cls):
        rev = repo.new_revision()
        cls.todo_category_names = [u'test-category']
        for category_name in cls.todo_category_names:
            tc = model.TodoCategory(category_name)
            model.Session.add(tc)
        repo.commit_and_remove()

    @classmethod
    def delete(cls):
        for category_name in cls.todo_category_names:
            category = model.TodoCategory.get(unicode(category_name))
            if category:
                model.Session.delete(category)

    @classmethod
    def reset(cls):
        cls.todo_category_names = []
