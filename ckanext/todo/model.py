"""
CKAN Todo Extension Data Model
"""
import sqlalchemy as sa
from ckan import model
from ckan.model import meta, User, Package, Session
from ckan.model.meta import types, Table, ForeignKey, DateTime
from ckan.model.types import make_uuid
from datetime import datetime

TODO_CATEGORY_NAME_MAX_LENGTH = 100
DEFAULT_CATEGORIES = [u"broken-resource-link", u"no-author", u"bad-format", 
                      u"add-description"]

todo_table = Table('todo', meta.metadata,
    meta.Column('id', types.Integer, primary_key = True, 
                autoincrement = True),
    meta.Column('todo_category_id', types.Integer,
                ForeignKey('todo_category.id', onupdate = 'CASCADE', ondelete = 'CASCADE'),
                nullable = False),
    meta.Column('package_id', types.UnicodeText,
                ForeignKey('package.id', onupdate = 'CASCADE', ondelete = 'CASCADE'),
                nullable = True),
    meta.Column('description', types.UnicodeText),
    meta.Column('creator', types.UnicodeText, 
                ForeignKey('user.id', onupdate='CASCADE', ondelete='SET NULL'),
                nullable = False),
    meta.Column('resolver', types.UnicodeText, 
                ForeignKey('user.id', onupdate='CASCADE', ondelete='SET NULL'),
                nullable = True),
    meta.Column('resolved', DateTime),
    meta.Column('created', DateTime, default = datetime.now, nullable = False))

class Todo(object):
    """A Todo Object"""
    def __init__(self, creator):
        self.creator = creator

    def __repr__(self):
        return "<Todo('%s')>" % (self.user_id)

meta.mapper(Todo, todo_table)

# ------------------------------------------------------------------------------

todo_category_table = Table('todo_category', meta.metadata,
    meta.Column('id', types.Integer, primary_key = True, 
                autoincrement = True),
    meta.Column('name', types.Unicode(TODO_CATEGORY_NAME_MAX_LENGTH),
                nullable=False, unique=True),
    meta.Column('created', DateTime, default = datetime.now, nullable = False))

class TodoCategory(object):
    """A Todo Category Object"""
    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return "<Todo('%s')>" % (self.name)

meta.mapper(TodoCategory, todo_category_table)
