from setuptools import find_packages, setup

with open('README.md', 'r') as fh:
    long_description = fh.read()

setup(
    name='django-serfilter',
    zip_safe=False,
    version='0.1.1',
    description=(
        'Easy to use, highly customizable filter backend for '
        'Django Rest Framework'),
    long_description=long_description,
    long_description_content_type='text/markdown',
    classifiers=[],
    keywords=['django', 'filter', 'backend', 'serializer'],
    author='Teemu Husso',
    author_email='teemu.husso@gmail.com',
    url='https://github.com/Raekkeri/django-serfilter',
    packages=find_packages(exclude=['tests']),
    install_requires=[
        'Django>=1.11,<3.0',
        'djangorestframework>=3.0,<4.0',
        'setuptools',
    ],
)
