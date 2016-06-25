import os

from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))
README = open(os.path.join(here, 'README.txt')).read()
CHANGES = open(os.path.join(here, 'CHANGES.txt')).read()

requires = """
    pyramid
    passlib
    six
    sqlalchemy
    pyramid_services
    backports.typing
""".split()

setup(name='tet',
      version='0.2',
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
      entry_points = """\
        [pyramid.scaffold]
        basictet=tet.scaffolds:BasicTetTemplate
      """,
      install_requires=requires,
)
