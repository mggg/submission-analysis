from setuptools import find_packages, setup

with open("./README.md") as f:
    long_description = f.read()

requirements = [
    # package requirements go here
    "pandas",
    "scipy",
    "networkx",
    "geopandas",
    "shapely",
    "matplotlib",
    "pathos"
]

setup(
    name="submission_analysis",
    description="Tools for analyzing COI submissions",
    author="MGGG Redistricting Lab",
    author_email="gerrymandr@gmail.com",
    maintainer="Parker Rule",
    maintainer_email="parker@mggg.org",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/mggg/GerryChain",
    package_dir={
        "submission_analysis": "submission_analysis",
        "submission_analysis.ccdb": "submission_analysis/ccdb"
    },
    packages=["submission_analysis", "submission_analysis.ccdb"],
    version="0.1.0",
    install_requires=requirements,
    classifiers=[
        "Programming Language :: Python :: 3.9",
        "Operating System :: OS Independent",
        "License :: OSI Approved :: BSD License",
    ],
)
