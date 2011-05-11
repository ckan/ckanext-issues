"""
CKAN Todo Extension Data Model
"""
import sqlalchemy as sa
from ckan import model
from ckan.model import meta, User, Package, Session
from ckan.model.types import make_uuid
from datetime import datetime

todo_table = meta.Table('todo', meta.metadata,
    meta.Column('id', meta.types.UnicodeText, primary_key=True, 
                default=make_uuid),
    meta.Column('created', meta.DateTime, default=datetime.now))
    # sa.UniqueConstraint('user_id', 'id'))

class Todo(object):
    def __init__(self, user_id):
        self.user_id = user_id
        self.created = None
    
    def __repr__(self):
        return "<Todo('%s')>" % (self.user_id)

meta.mapper(Todo, todo_table)
