from setuptools import setup, find_packages

setup(
    name='webnode',
    version='0.1.0',
    packages=find_packages(),
    install_requires=[
        # Add any dependencies here if needed in the future
    ],
    entry_points={
        'console_scripts': [
            'node=webnode.cli:main',
        ],
    },
    author='User',
    description='A custom node-based web framework.',
)
