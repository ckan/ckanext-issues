from logging import getLogger
from pylons import config
import ckan.model as model
import ckan.lib.helpers as h
import ckan.logic as logic
import ckan.plugins as p
from ckan.plugins import toolkit
from pylons.i18n import _
import ckanext.issues.model as issuemodel

log = getLogger(__name__)

def issue_created_in_dataset(data_dict):

    review_system = toolkit.asbool(config.get("ckanext.issues.review_system", False))

    log.debug("review_system issue_created: %s %s",data_dict,review_system)

    if review_system:
        issue_count = toolkit.get_action('issue_count')(data_dict={'dataset_id':data_dict['dataset_id'],'status':issuemodel.ISSUE_STATUS.open})

        if issue_count > 0:
            try:
                logic.get_action('package_patch')(data_dict={'id':data_dict['dataset_id'],'private':True})
            except logic.NotAuthorized:
                abort(401, _('Not authorized to modify the dataset'))

        if issue_count == 1:
            h.flash_error(_('The dataset has now been made private.'))

            log.debug("Dataset %s made private",data_dict['dataset_id'])

def issue_deleted_from_dataset(data_dict):

    review_system = toolkit.asbool(config.get("ckanext.issues.review_system", False))

    log.debug("review_system issue_deleted: %s %s",data_dict,review_system)

    if review_system:
        issue_count = toolkit.get_action('issue_count')(data_dict={'dataset_id':data_dict['dataset_id'],'status':issuemodel.ISSUE_STATUS.open})

        if issue_count == 0:
            try:
                logic.get_action('package_patch')(data_dict={'id':data_dict['dataset_id'],'private':False})
            except logic.NotAuthorized:
                abort(401, _('Not authorized to modify the dataset'))

            h.flash_success(_('The dataset has now been made public.'))

            log.debug("Dataset %s made public",data_dict['dataset_id'])
