# TXEngine (Py)

TXEngine is a text-based game engine, originally written in Java. The goal of this project is to create a rich toolset of game elements that empower designers to build flexible and unique worlds. With TXEngine, designers create games entirely by manipulating a set of JSON files--no code needed. TXEngine also features a rich content designer that can assist users of the engine with writing, tracking, and checking their JSON game components (coming soon).

This repository houses a Python rewrite and overhaul of the original TXEngine code. 

## How to Install
- TBD

## What's New?
TXEngine (Py) features a number of major improvements as compared to TXEngine (Java):

### Microservice Architecture
TXEngine (Py) splits the core logic of the engine away from the text rendering logic. This split increases the engine's maintainability, flexibility, and customizability.

TXEngine's backend makes use of FastAPI and comes bundled with a Python-Native text rendering client based on Rich!

### Improved Asset Schema
One major flaw of TXEngine (Java) was the confusing and complicated nature of the JSON asset schema. It was inflexible and difficult to document. TXEngine (Py) makes use of a streamlined JSON schema that is self-documenting, easy to update, and flexible!

### Remote Play
Since TXEngine (Py)'s backend is built on top of a REST-API framework, it can easily be set up to run on a remote machine. Access TXEngine (Py) from anywhere, even your phone!

# Contributing

TXEngine (Py) is open to contribution. Open a pull-request, and I'll do my best to review it quickly. Any PR that is poorly documented or does not adhere to the coding standards for this repository will be rejected.

## Developing

I recommend using Jetbrains PyCharm as your IDE when developing for TXEngine. As such, these instructions will include PyCharm-specific steps.

 - Clone the repository to your PC. Using command-line git: `git clone https://github.com/SlappedWithSilence/TXEnginePy`
 - Set up your virtual environment. We recommend using Poetry, as that's our build system.
   - Install `pipx`: https://pipx.pypa.io/stable/installation/
   - Install `poetry`: https://python-poetry.org/docs/#installation
   - Create a virtual environment and install dependencies: `poetry install`
 - (Optional) Install pre-commit and the `ruff` hook
   - Run `pipx install pre-commit` OR install pre-commit via Poetry: `poetry add pre-commit`
   - 
 - [Install PyCharm](https://www.jetbrains.com/pycharm/)
 - Open TXEnginePy in PyCharm
 - Install the [Pydantic PyCharm plugin](https://docs.pydantic.dev/pycharm_plugin/)
 - Run the application:
   - `fastapi dev` or `uvicorn --app-dir=src/ main:tx_engine --reload`
   - For more info, [see here](https://fastapi.tiangolo.com/tutorial/first-steps/)
- Run a TXEnginePY Client
  - TXEnginePY comes bundled with a primitive client, suitable only for debugging. It implements the bare minimum features to simulate what a user of a proper client would see.
  - To run, `cd` to the root of the TXEnginePy repo
  - (optional) Activate your `venv`
  - `python src\viewer\viewer.py`
- You should now be connected to the TXEnginePY backend. Verify that your Client is correctly communicating with the backend by playing around a bit!

## Acknowledgements

[FastAPI](https://fastapi.tiangolo.com/)

[Pydantic](https://docs.pydantic.dev/)

[Rich](https://pypi.org/project/rich/)
