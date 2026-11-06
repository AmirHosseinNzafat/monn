from setuptools import find_packages, setup

setup(
    name="monn-lang",
    version="1.0.0",
    description="A dot-command DSL for building Tkinter interfaces",
    packages=find_packages(),
    py_modules=["monn_cli"],
    python_requires=">=3.8",
    entry_points={"console_scripts": ["monn=monn_cli:main"]},
    include_package_data=True,
)
