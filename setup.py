"""
Setup script for Content Research Pipeline.
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README file
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text()

# Read requirements
with open("requirements.txt") as f:
    requirements = [line.strip() for line in f if line.strip() and not line.startswith("#")]

setup(
    name="content-research-pipeline",
    version="1.0.0",
    author="Siddhant Gadamsetti",
    author_email="siddhant.gadamsetti@gmail.com",
    description="A comprehensive, AI-powered content research and analysis system",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/siddhant61/content-research-pipeline",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: Researchers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Scientific/Engineering :: Information Analysis",
        "Topic :: Internet :: WWW/HTTP :: Indexing/Search",
        "Topic :: Text Processing :: Linguistic",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.4.3",
            "pytest-asyncio>=0.21.1",
            "pytest-cov>=4.1.0",
            "black>=23.11.0",
            "flake8>=6.1.0",
            "mypy>=1.7.1",
            "pre-commit>=3.5.0",
        ],
        "api": [
            "fastapi>=0.104.1",
            "uvicorn>=0.24.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "content-research=content_research_pipeline.cli:cli",
        ],
    },
    include_package_data=True,
    package_data={
        "content_research_pipeline": [
            "templates/*.html",
            "static/*",
        ],
    },
    keywords=[
        "research",
        "content analysis",
        "ai",
        "nlp",
        "web scraping",
        "sentiment analysis",
        "topic modeling",
        "entity extraction",
        "data mining",
        "information retrieval",
    ],
    project_urls={
        "Documentation": "https://github.com/siddhant61/content-research-pipeline/docs",
        "Source": "https://github.com/siddhant61/content-research-pipeline",
        "Tracker": "https://github.com/siddhant61/content-research-pipeline/issues",
    },
) 