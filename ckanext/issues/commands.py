from ckan.lib.cli import CkanCommand

import logging
import sys

from pylons import config

class Issues(CkanCommand):
    """
    Usage:

        paster issues init_db
           - Creates the database table issues needs to run
    """
    summary = __doc__.split('\n')[0]
    usage = __doc__

    def command(self):
        """
        Parse command line arguments and call appropriate method.
        """
        if not self.args or self.args[0] in ['--help', '-h', 'help']:
            print self.usage
            sys.exit(1)

        cmd = self.args[0]
        self._load_config()

        self.log = logging.getLogger(__name__)

        if cmd == 'init_db':
            from ckanext.issues.model import setup
            setup()
            self.log.info('Issues tables are initialized')
        else:
            self.log.error('Command %s not recognized' % (cmd,))
