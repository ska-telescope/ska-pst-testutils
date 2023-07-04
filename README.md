SKA PST Testutils
=================

[![Documentation Status](https://readthedocs.org/projects/ska-telescope-ska-pst-testutils/badge/?version=latest)](https://developer.skao.int/projects/ska-pst-testutils/en/latest/)
The `ska-pst-testutils` repository is used as a Python library for testing PST. This package should be imported as a `dev` package when used in
another project.

Code from this package has been ported from the the [SKA PST](https://gitlab.com/ska-telescope/pst/ska-pst) respository.

# Developer setup

This project uses `PyTango` via the [ska-tango-base](https://gitlab.com/ska-telescope/ska-tango-base) project.

To make sure your development environment is ready, follow the [Installation instructions](https://gitlab.com/ska-telescope/ska-tango-examples#installation)  of the `ska-tango-examples` project (this is specific for Ubuntu but you should be able to work it out for other environments).

At the very least have [Docker](https://docs.docker.com/get-docker/) and install [Minikube](https://minikube.sigs.k8s.io/docs/) - (see - [SKA Deploy Minikube](https://gitlab.com/ska-telescope/sdi/ska-cicd-deploy-minikube))

## Download the source code

First, clone this repo and submodules to your local file system

    git clone --recursive git@gitlab.com:ska-telescope/pst/ska-pst-testutils.git

then change to the newly cloned directory and create the build/ sub-directory

    cd ska-pst-testutils
    mkdir build

## Poetry setup

No matter what enviroment that you use, you will need to make sure that Poetry is
installed and that you have the Poetry shell running.

Install Poetry based on [Poetry Docs](https://python-poetry.org/docs/). Ensure that you're using at least 1.2.0, as the
`pyproject.toml` and `poetry.lock` files have been migrated to the Poetry 1.2.

After having Poetry installed, run the following command to be able to install the project. This will create a virtual env for you before starting.

    poetry install


If the is successful you should be able to use your favourite editor/IDE to develop in this project.

To activate the poetry environment then run in the same directory:

    poetry shell

(For VS Code, you can then set your Python Interpreter to the path of this virtual env.)

## Code Formatting and Linting

This project requires that the code is well formated and had been linted by `pylint` and `mypy`.

Your code can be formated by running:

    make python-format

While the code can be linted by running:

    make python-lint

A developer can ensure formatting happens as part of the linting by adding the folling to their
`PrivateRules.mak`

```make
python-pre-lint: python-format

.PHONY: python-pre-lint
```

## Ensuring Linting before commit

It is highly recommended that linting is performed **before** commiting your code.  This project
has a `pre-commit` hook that can be enabled.  SKA Make machinery provides the following command
that can be used by developers to enable the lint check pre-commit hook.

    make dev-git-hooks

After this has been applied, `git commit` commands will run the pre-commit hook. If you
want to avoid doing that for some work in progress (WIP) then run the following command
instead

    git commit --no-verify <other params>

## EditorConfig

This project has an `.editorconfig` file that can be used with IDEs/editors that support
[EditorConfig](https://editorconfig.org/).  Both VS Code and Vim have plugins for this,
please check your favourite editor for use of the plugin.

For those not familiar with EditorConfig, it uses a simple configuration file that
instructs your editor to do some basic formatting, like tabs as 4 spaces for Python or
leaving tabs as tabs for Makefiles, or even triming trailing whitespace of lines.

# License

See the LICENSE file for details.

