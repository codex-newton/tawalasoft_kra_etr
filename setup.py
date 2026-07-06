from setuptools import setup, find_packages

with open("requirements.txt") as f:
    install_requires = f.read().strip().split("\n")

setup(
    name="tawalasoft_kra_etr",
    version="0.0.1",
    description="ERPNext integration with KRA TIMS ETR middleware",
    author="Tawalasoft",
    packages=find_packages(),
    zip_safe=False,
    include_package_data=True,
    install_requires=install_requires,
)
