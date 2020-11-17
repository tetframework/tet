import os, sys

from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))

def readfile(name):
    with open(os.path.join(here, name)) as f:
        return f.read()

README = readfile('README.txt')
CHANGES = readfile('CHANGES.txt')

requires = """
    pyramid>=1.9
    passlib
    sqlalchemy
    pyramid_services
""".split()

if sys.version_info < (3, 5, 2):
    requires.append('backports.typing>=1.1,<1.2')


setup(name='tet',
      version='0.4.0.dev0',
      description='Unearthly intelligent batteries-included application framework built on Pyramid',
      long_description=README + '\n\n' + CHANGES,
      classifiers=[
          "Development Status :: 4 - Beta",
          "Framework :: Pyramid",
          "Intended Audience :: Developers",
          "License :: OSI Approved :: Python Software Foundation License",
          "Programming Language :: Python :: 3.3",
          "Programming Language :: Python :: 3.4",
          "Programming Language :: Python :: 3.5",
          "Programming Language :: Python :: 3.6",
          "Programming Language :: Python :: 3.7",
          "Programming Language :: Python :: 3.8",
          "Programming Language :: Python :: 3.9",
          "Programming Language :: Python :: 3 :: Only",
          "Topic :: Internet :: WWW/HTTP :: WSGI",
          "Topic :: Internet :: WWW/HTTP :: WSGI :: Application",
          "Topic :: Internet :: WWW/HTTP :: WSGI :: Middleware",
          "Topic :: Software Development :: Libraries :: Application Frameworks"
      ],
      author='Antti Haapala',
      author_email='antti.haapala@anttipatterns.com',
      url='http://www.anttipatterns.com',
      keywords='web wsgi bfg pylons pyramid',
      packages=find_packages(),
      include_package_data=True,
      zip_safe=False,
      test_suite='tet',
      install_requires=requires,
)
