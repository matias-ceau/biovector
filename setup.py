from setuptools import find_packages, setup
import pathlib

here = pathlib.Path(__file__).parent.resolve()
long_description = (here / "README.md").read_text(encoding="utf-8")

setup(
    name='biovector',
    packages=find_packages(where='src'),
    version='0.0.0',
    description='Scientific work out app',
    author='Matias Ceau',
    author_email="matias@ceau.net",
    long_description=long_description,
    long_description_content_type="text/markdown",
    include_package_data=True,
    license='GPLv3',
    url="https://github.com/matias-ceau/biovector",
    install_requires=['numpy','scipy','pandas','pyyaml','datetime','seaborn','matplotlib'],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3 :: Only",
        "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
        "Operating System :: Unix",
        "Topic :: Scientific/Engineering",
        "Intended Audience :: Science/Research",
        "Intended Audience :: Developers"
    ],
    test_suite='tests',
    package_dir={'': 'src'}
)
