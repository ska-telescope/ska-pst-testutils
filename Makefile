PROJECT = ska-pst-testutils

DOCS_SOURCEDIR=./docs/src

# This Makefile uses templates defined in the .make/ folder, which is a git submodule of
# https://gitlab.com/ska-telescope/sdi/ska-cicd-makefile.

include .make/base.mk
include .make/oci.mk
include .make/python.mk

# common pst makefile library
include .pst/base.mk

# include your own private variables for custom deployment configuration
-include PrivateRules.mak

# PYTHON_RUNNER:= .venv/bin/python -m
PYTHON_LINT_TARGET:=src/ tests/
PYTHON_PUBLISH_URL:=https://artefact.skao.int/repository/pypi-internal/
PYTHON_SWITCHES_FOR_BLACK :=
PYTHON_SWITCHES_FOR_ISORT :=

DEV_IMAGE					?=ska-pst-testutils
DEV_TAG						?=`grep -m 1 -o '[0-9].*' .release`
TESTUTILS_BASE				?=library/ubuntu:22.04
OCI_BUILD_ADDITIONAL_ARGS	= --build-arg TESTUTILS_BASE=$(TESTUTILS_BASE)

python-pre-lint:
	pip install isort black flake8 pylint-junit pytest build

python-pre-build:
	pip install build

docs-pre-build:
	pip install isort black flake8 pylint-junit pytest build
	pip install -r docs/requirements.txt

# DEPENDENCIES INSTALLATION
.PHONY: local-pkg-install
PKG_CLI_CMD 		?=apt-get # Package manager executable
PKG_CLI_PAYLOAD 	?= 		# Payload file
PKG_CLI_PARAMETERS 	?= 	# Package manager installation parameters

local-pkg-install:
	$(PKG_CLI_CMD) $(PKG_CLI_PARAMETERS) `cat $(PKG_CLI_PAYLOAD)`
