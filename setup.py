from setuptools import setup, find_packages

version = '0.1'

setup(
	name='ckanext-issues',
	version=version,
	description='CKAN Extension providing Issues (Task/Todos/...)',
	classifiers=[], # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
	keywords='',
	author='CKAN Project (Open Knowledge Foundation)',
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
		# -*- Extra requirements: -*-
	],
	entry_points=\
	"""
    [ckan.plugins]
	issues=ckanext.issues.plugin:IssuesPlugin
	""",
)
