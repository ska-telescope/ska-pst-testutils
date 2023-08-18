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
PYTHON_PUBLISH_URL:=https://artefact.skao.int/repository/pypi-internal/
PYTHON_LINT_TARGET = src/ tests/
PYTHON_LINE_LENGTH = 110
PYTHON_SWITCHES_FOR_FLAKE8 := --extend-ignore=BLK,T --enable=DAR104 --ignore=E203,FS003,W503,N802 --max-complexity=10 \
    --rst-roles=py:attr,py:class,py:const,py:exc,py:func,py:meth,py:mod \
		--rst-directives deprecated,uml
PYTHON_SWITCHES_FOR_ISORT = --skip-glob="*/__init__.py" --py 39
PYTHON_SWITCHES_FOR_PYLINT = --disable=W,C,R
PYTHON_SWITCHES_FOR_AUTOFLAKE ?= --in-place --remove-unused-variables --remove-all-unused-imports --recursive --ignore-init-module-imports

PYTHON_VARS_AFTER_PYTEST = --cov-config=$(PWD)/.coveragerc

DEV_IMAGE ?=ska-pst-testutils
DEV_TAG ?=`grep -m 1 -o '[0-9].*' .release`

SKA_RELEASE_REGISTRY=artefact.skao.int
PST_DEV_REGISTRY=registry.gitlab.com/ska-telescope/pst

SKA_TANGO_PYTANGO_BUILDER_REGISTRY=$(SKA_RELEASE_REGISTRY)
SKA_TANGO_PYTANGO_BUILDER_IMAGE=ska-tango-images-pytango-builder
SKA_TANGO_PYTANGO_BUILDER_TAG=9.3.32
SKA_PST_TESTUTILS_BASE_IMAGE=$(SKA_TANGO_PYTANGO_BUILDER_REGISTRY)/$(SKA_TANGO_PYTANGO_BUILDER_IMAGE):$(SKA_TANGO_PYTANGO_BUILDER_TAG)

OCI_BUILD_ADDITIONAL_ARGS = --build-arg SKA_PST_TESTUTILS_BASE_IMAGE=$(SKA_PST_TESTUTILS_BASE_IMAGE)

mypy:
	$(PYTHON_RUNNER) mypy --config-file mypy.ini $(PYTHON_LINT_TARGET)

flake8:
	$(PYTHON_RUNNER) flake8 --show-source --statistics $(PYTHON_SWITCHES_FOR_FLAKE8) $(PYTHON_LINT_TARGET)

python-post-format:
	$(PYTHON_RUNNER) autoflake $(PYTHON_SWITCHES_FOR_AUTOFLAKE) $(PYTHON_LINT_TARGET)

python-post-lint: mypy

.PHONY: python-post-format, python-post-lint, mypy, flake8

docs-pre-build:
	poetry install --only docs

# DEPENDENCIES INSTALLATION
.PHONY: local-pkg-install
PKG_CLI_CMD 		?=apt-get # Package manager executable
PKG_CLI_PAYLOAD 	?= 		# Payload file
PKG_CLI_PARAMETERS 	?= 	# Package manager installation parameters

local-pkg-install:
	$(PKG_CLI_CMD) $(PKG_CLI_PARAMETERS) `cat $(PKG_CLI_PAYLOAD)`
