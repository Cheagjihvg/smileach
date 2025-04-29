from setuptools import setup, find_packages

setup(
    name='smileach',                      # 👈 must match import name
    version='0.1.0',
    packages=find_packages(),
    install_requires=[
        'requests',
    ],
    author='NANG',
    description='SmileOne API integration bot',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    python_requires='>=3.7',
)
