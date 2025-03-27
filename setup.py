from setuptools import find_packages, setup

setup(
    name="FastApiSimpleCRUD",
    version="0.1",
    packages=find_packages(),
    install_requires=["fastapi", "pydantic", "sqlalchemy"],
    entry_points={},
    )
