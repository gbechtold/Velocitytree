from setuptools import setup, find_packages
import os

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="velocitytree",
    version="2.0.0",
    author="Guntram Bechtold",
    author_email="your.email@example.com",
    description="AI-powered development assistant with continuous monitoring, drift detection, and intelligent suggestions",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/gbechtold/Velocitytree",
    packages=find_packages(where="."),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Build Tools",
        "Topic :: Software Development :: Version Control",
        "Topic :: Software Development :: Quality Assurance",
        "Topic :: Software Development :: Libraries :: Application Frameworks",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "velocitytree=velocitytree.cli:main",
            "vtree=velocitytree.cli:main",
        ],
    },
    include_package_data=True,
    zip_safe=False,
)