from setuptools import setup, find_packages

version = '0.3'

setup(
	name='ckanext-issues',
	version=version,
	description='CKAN Extension providing Issues (Task/Todos/...)',
	classifiers=[],
	keywords='',
	author='CKAN Project',
	author_email='info@okfn.org',
	url='',
	license='mit',
    packages=find_packages(exclude=['tests']),
    namespace_packages=['ckanext', 'ckanext.issues'],
    package_data = {'ckanext.issues' : ['public/ckanext-issues/*.js',
                                      'public/ckanext-issues/css/*.css',
                                      'public/ckanext-issues/images/*.png',
                                      'templates/*.html']},
	include_package_data=True,
	zip_safe=False,
	install_requires=[
        'enum34',
    ],
	entry_points=\
	"""
    [ckan.plugins]
	issues=ckanext.issues.plugin:IssuesPlugin

    [paste.paster_command]
    issues = ckanext.issues.commands:Issues
    
    [babel.extractors]
    ckan = ckan.lib.extract:extract_ckan
	""",
    # If you are changing from the default layout of your extension, you may
    # have to change the message extractors, you can read more about babel
    # message extraction at
    # http://babel.pocoo.org/docs/messages/#extraction-method-mapping-and-configuration
    message_extractors={
        'ckanext': [
            ('**.py', 'python', None),
            ('**.js', 'javascript', None),
            ('**/templates/**.html', 'ckan', None),
        ],
    }
)

