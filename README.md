# LeRoboto

This repository contains a library and utilities for interacting with Hugging Face LeRobot data in Roboto.

## Developer Setup
### Requirements
* Pantsbuild 2.26 or higher
* Python 3.10
* Docker

### IDE Support

Pantsbuild is able to generate an immutable symlink to a virtual environment that can be used by IDEs for code
completion and type checking. You can generate this symlink with the following command:

`pants export --py-resolve-format=symlinked_immutable_virtualenv --resolve=python-default`

After this is done, you can configure your IDE to use the virtual environment at it creates in
`dist/export/python`

### Testing
You can re-build the action and run it locally with the following command:

`pants package :: && docker run -v ~/.roboto:/root/.roboto import_lerobot_dataset_action:latest`