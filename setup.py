from setuptools import setup, find_packages


setup(
    name='Lektor',
    version='0.96',
    url='http://github.com/lektor/lektor/',
    license='BSD',
    author='Armin Ronacher',
    author_email='armin.ronacher@active-4.com',
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    platforms='any',
    install_requires=[
        'Jinja2>=2.4',
        'click>=6.0',
        'watchdog',
        'mistune',
        'Flask',
        'EXIFRead',
        'inifile',
        'Babel',
        'setuptools',
        'pip',
    ],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Software Development :: Libraries :: Python Modules'
    ],
    entry_points='''
        [console_scripts]
        lektor=lektor.cli:main
    '''
)
