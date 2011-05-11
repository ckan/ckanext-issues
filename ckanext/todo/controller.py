"""
CKAN Todo Extension
"""
from logging import getLogger
log = getLogger(__name__)

from pylons.i18n import _
from pylons.decorators import jsonify
from pylons import request, tmpl_context as c
from ckan.lib.base import BaseController, response, render, abort
from ckanext.todo import model

class TodoController(BaseController):
    """
    The CKANEXT-Todo Controller.
    """
    @jsonify
    def index(self):
        """
        default API endpoint.
        """
        # just return a default message
        return {'doc': __doc__,
                'doc_url': 'http://ckan.org/wiki/Extensions'}
