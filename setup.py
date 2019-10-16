import setuptools

import bento as bento

with open("README.md", "r") as fh:
    long_description = fh.read()

with open("requirements.txt") as req_lines:
    install_requires = [str(r).strip() for r in req_lines]

# I apologize in advance, but this issue https://github.com/pypa/pipenv/issues/3305
# makes me very very sad
all_deps = [
    line
    for line in install_requires
    if line and not line.startswith("-i") and not line.startswith("#")
]

setuptools.setup(
    name=bento.__name__,
    version=bento.__version__,
    author=bento.__author__,
    author_email=bento.R2C_SUPPORT_EMAIL,
    description="Bento is a free command-line tool that finds the bugs that matter to you",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://r2c.dev",
    install_requires=all_deps,
    packages=setuptools.find_packages(),
    python_requires=">=3.6",
    include_package_data=True,
    license="Proprietary",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: Other/Proprietary License",
        "Operating System :: OS Independent",
    ],
    entry_points={"console_scripts": ["bento=bento.__main__:main"]},
)
