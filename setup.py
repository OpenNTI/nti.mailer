import codecs
from setuptools import setup, find_packages

entry_points = {
    'console_scripts': [
        'nti_mailer_qp_console = nti.mailer.queue:run_console',
        'nti_mailer_qp_process = nti.mailer.queue:run_process',
        'nti_qp = nti.mailer.queue:run_console' # backwards compatibility
    ],
}

TESTS_REQUIRE = [
    'fudge',
    'nti.testing',
    'zope.testrunner',
    'nti.app.pyramid_zope',
    'pyramid_chameleon',
    'pyramid_mako',
    'nose'
]


def _read(fname):
    with codecs.open(fname, encoding='utf-8') as f:
        return f.read()


setup(
    name='nti.mailer',
    version=_read('version.txt').strip(),
    author='Josh Zuech',
    author_email='josh.zuech@nextthought.com',
    description="NTI mailer",
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
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
    ],
    url="https://github.com/NextThought/nti.mailer",
    zip_safe=True,
    packages=find_packages('src'),
    package_dir={'': 'src'},
    include_package_data=True,
    namespace_packages=['nti'],
    tests_require=TESTS_REQUIRE,
    install_requires=[
        'gevent',
        'setuptools',
        'boto',
        'BTrees',
        'itsdangerous',
        'nti.schema',
        'repoze.sendmail',
        'premailer',
        'pyramid',
        'pyramid_mailer',
        'six',
        'ZODB',
        'zc.displayname',
        'zope.annotation',
        'zope.catalog',
        'zope.component',
        'zope.container',
        'zope.dottedname',
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
            'sphinx_rtd_theme',
        ],
    },
    entry_points=entry_points,
)
