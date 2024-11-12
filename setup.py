import codecs
from setuptools import setup
from setuptools import find_namespace_packages

entry_points = {
    'console_scripts': [
        'nti_mailer_qp_console = nti.mailer.queue:run_console',
        'nti_mailer_qp_process = nti.mailer.queue:run_process',
        'nti_qp = nti.mailer.queue:run_console' # backwards compatibility
    ],
}

TESTS_REQUIRE = [
    'nti.testing',
    'zope.testrunner',
    'nti.app.pyramid-zope >= 0.0.3',
    'pyramid_chameleon',
    'pyramid_mako',
]


def _read(fname):
    with codecs.open(fname, encoding='utf-8') as f:
        return f.read()


setup(
    name='nti.mailer',
    version="1.0.0",
    author='Josh Zuech',
    author_email='open-source@nextthought.com',
    description="Integrates pyramid_mailer and repoze.sendmail with Amazon SES.",
    long_description=(
        _read('README.rst')
        + '\n\n'
        + _read("CHANGES.rst")
    ),
    license='Apache',
    keywords='Base',
    classifiers=[
        'Framework :: Zope3',
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Programming Language :: Python :: 3.13',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
    ],
    url="https://github.com/OpenNTI/nti.mailer",
    zip_safe=True,
    packages=find_namespace_packages('src'),
    package_dir={'': 'src'},
    include_package_data=True,
    install_requires=[
        'gevent',
        'setuptools',
        'boto3',
        'BTrees',
        'itsdangerous',
        'nti.schema',
        'repoze.sendmail',
        'premailer >= 3.7.0',
        # The < 2.0 part is from nti.app.pyramid_zope, a test
        # dependency. But older released versions on PyPI (< 0.0.3)
        # do not specify this correctly.
        #'pyramid < 2.0',
        'pyramid_mailer',
        'six',
        'ZODB',
        'zc.displayname',
        'zope.annotation',
        'zope.catalog',
        'zope.component',
        'zope.container',
        'zope.dottedname',
        'zope.i18n',
        'zope.interface',
        'zope.intid',
        'zope.location',
        'zope.schema',
        'zope.security',
    ],
    extras_require={
        'test': TESTS_REQUIRE,
        'docs': [
            'Sphinx',
            'repoze.sphinx.autointerface',
            'sphinxcontrib-programoutput',
            'sphinx_rtd_theme',
        ],
    },
    entry_points=entry_points,
    python_requires=">=3.10",
)
