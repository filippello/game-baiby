from setuptools import setup, find_packages

setup(
    name="baibysitter",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "web3",
        "python-dotenv",
        "httpx",
        "game-sdk",  # si este es un requisito
        "goat-sdk",  # si este es un requisito
    ],
    author="Tu Nombre",
    author_email="tu@email.com",
    description="Un plugin de baibysitter para GAME SDK",
) 