import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="HbeamController-ETH", # Replace with your own username
    version="2.0.0",
    author="Otto Hanski",
    author_email="otolha@utu.fi",
    description="Program for controlling Hbeam setup at ETH",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/OtHanski/HbeamController",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    package_dir={"": "src"},
    packages=setuptools.find_packages(where="src"),
    python_requires=">=3.6",
)
