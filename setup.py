from setuptools import setup, find_packages

setup(
    name="wordle",
    version="0.1.0",
    description="A simple wordle-like guessing game and word frequency generator.",
    author="Mohammadamin Albooyeh",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[],
    python_requires=">=3.7",
)
