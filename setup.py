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
    'nti.app.pyramid-zope >= 0.0.3',
    'pyramid_chameleon',
    'pyramid_mako',
]


def _read(fname):
    with codecs.open(fname, encoding='utf-8') as f:
        return f.read()


setup(
    name='nti.mailer',
    version="0.0.1a2",
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
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
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
        'boto3',
        'BTrees',
        'itsdangerous',
        'nti.schema',
        'repoze.sendmail',
        # premailer dropped Python 2 support in version 3.7;
        # unfortunately, they don't have the proper ``python_requires`` metadata
        # to let installers know this.
        'premailer < 3.7.0; python_version == "2.7"',
        'premailer >= 3.7.0; python_version != "2.7"',
        # The < 2.0 part is from nti.app.pyramid_zope, a test
        # dependency. But older released versions on PyPI (< 0.0.3)
        # do not specify this correctly.
        'pyramid < 2.0',
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
    python_requires=">=2.7,!=3.0.*,!=3.1.*,!=3.2.*,!=3.3.*,!=3.4.*,!=3.5",
)
