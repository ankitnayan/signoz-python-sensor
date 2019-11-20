from setuptools import setup
from setuptools import find_packages
setup(
    # Needed to silence warnings (and to be a worthwhile package)
    name='Signoz Python Sensor',
    url='',
    author='Ankit Nayan',
    author_email='ankit@signoz.io',
    # Needed to actually package something
    packages=find_packages(),
    # Needed for dependencies
    install_requires=['autowrapt>=1.0', 'datadog==0.29.3', 'six'],
    entry_points={
        'signoz':  ['string = signoz:load'],
    },
    # *strongly* suggested for sharing
    version='0.5',
    # The license can be anything you like
    license='MIT',
    description='An example of a python package from pre-existing code',
    # We will also need a readme eventually (there will be a warning)
    # long_description=open('README.txt').read(),
)