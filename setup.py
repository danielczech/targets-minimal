import setuptools

requires = [
    'numpy >= 1.18.1',
    'redis >= 3.4.1',
    'PyYAML >= 6.0',
    'scipy >= 1.8.0',
    'mysql-connector-python==8.2.0'
    ]

setuptools.setup(
    name = 'target_selector',
    version = '1.0',
    url = 'https://github.com/danielczech/targets-minimal',
    license = 'MIT',
    author = 'Daniel Czech',
    author_email = 'danielc@berkeley.edu',
    description = 'Target selector for Breakthrough Listen\'s commensal observing',
    packages = [
        'target_selector',
        ],
    install_requires=requires,
    entry_points = {
        'console_scripts':[
            'targetselector = target_selector.cli:cli',
            ]
        },
    )
