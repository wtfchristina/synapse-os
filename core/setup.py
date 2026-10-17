from setuptools import setup, find_packages

setup(
    name="synapse-dsp",
    version="0.1.0",
    packages=find_packages(),
    package_data={
        "synapse_dsp": ["*.dylib", "*.so", "*.dll"],
    },
    include_package_data=True,
    install_requires=[
        "cffi>=1.15.0",
        "numpy>=1.24.0",
    ],
)
