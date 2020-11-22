import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="panserver",
    version="0.1.0",
    author="Marcel Fischer",
    description=(
        "A simple HTTP server to view rendered Markdown documents, which "
        "automatically refresh"
    ),
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Marfisc/panserver",
    py_modules=["panserver"],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.6",
    install_requires=["bottle"],
    entry_points={"console_scripts": ["panserver=panserver:main"]},
)
