from pathlib import Path

from setuptools import find_packages, setup

here = Path(__file__).parent
README = (here / "README.md").read_text()
CHANGES = (here / "CHANGES.md").read_text()


requires = """
    pyramid>=1.9
    passlib
    sqlalchemy
    pyramid_di
""".split()

dev_requires = ["pytest"]

setup(
    name="tet",
    version="0.4.3-dev",
    description="Unearthly intelligent batteries-included application framework built on Pyramid",
    long_description=README + "\n\n" + CHANGES,
    long_description_content_type="text/markdown",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Framework :: Pyramid",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Programming Language :: Python :: 3.14",
        "Programming Language :: Python :: 3 :: Only",
        "Topic :: Internet :: WWW/HTTP :: WSGI",
        "Topic :: Internet :: WWW/HTTP :: WSGI :: Application",
        "Topic :: Internet :: WWW/HTTP :: WSGI :: Middleware",
        "Topic :: Software Development :: Libraries :: Application Frameworks",
    ],
    author="Antti Haapala",
    author_email="antti.haapala@anttipatterns.com",
    url="https://github.com/tetframework/tet",
    keywords="web wsgi bfg pylons pyramid",
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    test_suite="tet",
    install_requires=requires,
    extras_require={"dev": dev_requires},
)
