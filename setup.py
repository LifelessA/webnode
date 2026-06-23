from setuptools import setup, find_packages
import os


def find_package_data(package_dir):
    """Recursively find all non-python files in the package."""
    result = []
    for root, dirs, files in os.walk(package_dir):
        for fname in files:
            if fname.endswith('.py') or fname.endswith('.pyc') or '__pycache__' in root:
                continue
            full = os.path.join(root, fname)
            rel = os.path.relpath(full, os.path.dirname(package_dir))
            # Make it relative to the package (webnode/)
            rel = os.path.relpath(full, os.path.join(os.path.dirname(__file__), 'webnode'))
            result.append(rel)
    return result


setup(
    name='webnode',
    version='1.5.1',
    packages=find_packages(),
    package_data={
        'webnode': find_package_data(os.path.join(os.path.dirname(__file__), 'webnode'))
    },
    include_package_data=True,
    python_requires='>=3.8',
    author='LifelessA',
    description='WebNode Framework — Visual node-based web framework for Python (v1.5.1)',
    long_description=open('README.md', encoding='utf-8').read() if os.path.exists('README.md') else '',
    long_description_content_type='text/markdown',
    url='https://github.com/LifelessA/webnode',
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
)
