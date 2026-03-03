from setuptools import setup, find_packages

setup(
    name='webnode',
    version='0.3.0',
    packages=find_packages(),
    package_data={
        'webnode': ['_editor_files/*'],
    },
    install_requires=[
        # Standard library only — no external dependencies!
    ],
    entry_points={
        'console_scripts': [
            'node-web=webnode.cli:main',
        ],
    },
    author='LifelessA',
    description='A custom node-based web framework with a visual Node Editor.',
)
