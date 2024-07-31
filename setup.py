from setuptools import setup, find_namespace_packages


if __name__ == '__main__':
    with open('./src/jule/__init__.py', 'r') as f:
        version_line = [line for line in f.readlines() if 'VERSION' in line][0]
        version = version_line.split('=')[1].strip(" '\n")

    setup(
        name='jule',
        version=version,
        packages=find_namespace_packages(where='src'),
        package_dir={'': 'src'},
        description='JULE - LDAP Explorer',
        install_requires=[
            'python-ldap',
            'coloredlogs',
            'textual[syntax]',
            'tabulate',
            'pandas',
            'pandasql',
        ],
        package_data={
            'jule.data': ['*'],
        }
    )
