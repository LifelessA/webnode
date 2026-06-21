from setuptools import setup, find_packages
import os


def find_package_data(package_dir):
    """Recursively find all files in _project_template and _editor_files."""
    result = []
    for root, dirs, files in os.walk(package_dir):
        for fname in files:
            full = os.path.join(root, fname)
            rel = os.path.relpath(full, os.path.dirname(package_dir))
            # Make it relative to the package (webnode/)
            rel = os.path.relpath(full, os.path.join(os.path.dirname(__file__), 'webnode'))
            result.append(rel)
    return result


setup(
    name='webnode',
    version='1.4.0',
    packages=find_packages(),
    package_data={
        'webnode': find_package_data(os.path.join(os.path.dirname(__file__), 'webnode', '_project_template'))
    },
    include_package_data=True,
    entry_points={
        'console_scripts': [
            'node-web=webnode.cli:main',
        ],
    },
    python_requires='>=3.8',
    author='LifelessA',
    description='WebNode Framework — Visual node-based web framework for Python (v1.4.0)',
    long_description=open('README.md', encoding='utf-8').read() if os.path.exists('README.md') else '',
    long_description_content_type='text/markdown',
    url='https://github.com/LifelessA/webnode',
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
)
