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

PYTHON_SWITCHES_FOR_FLAKE8 := --extend-ignore=BLK,T --enable=DAR104 --ignore=E203,FS003,W503,N802 --max-complexity=10 \
    --max-line-length=110 --rst-roles=py:attr,py:class,py:const,py:exc,py:func,py:meth,py:mod \
		--rst-directives deprecated,uml --exclude=src/ska_pst_lmc_proto
PYTHON_SWITCHES_FOR_BLACK := --line-length=110 --force-exclude=src/ska_pst_lmc_proto
PYTHON_SWITCHES_FOR_ISORT := --skip-glob="*/__init__.py" -w=110 --py 39 --thirdparty=ska_pst_lmc_proto
PYTHON_SWITCHES_FOR_PYLINT = --disable=W,C,R --ignored-modules="ska_pst_lmc_proto"
PYTHON_SWITCHES_FOR_AUTOFLAKE ?= --in-place --remove-unused-variables --remove-all-unused-imports --recursive --ignore-init-module-imports src tests
PYTHON_VARS_AFTER_PYTEST = --cov-config=$(PWD)/.coveragerc

DEV_IMAGE ?=ska-pst-testutils
DEV_TAG ?=`grep -m 1 -o '[0-9].*' .release`
TESTUTILS_BASE ?=library/ubuntu:22.04
OCI_BUILD_ADDITIONAL_ARGS = --build-arg TESTUTILS_BASE=$(TESTUTILS_BASE)

mypy:
	$(PYTHON_RUNNER) mypy --config-file mypy.ini src/ tests/

flake8:
	$(PYTHON_RUNNER) flake8 --show-source --statistics $(PYTHON_SWITCHES_FOR_FLAKE8) $(PYTHON_LINT_TARGET)

python-post-format:
	$(PYTHON_RUNNER) autoflake $(PYTHON_SWITCHES_FOR_AUTOFLAKE)

python-post-lint:
	$(PYTHON_RUNNER) mypy --config-file mypy.ini src/ tests/

.PHONY: python-post-format, python-post-lint

python-pre-build:
	pip install build

docs-pre-build:
	pip install -r docs/requirements.txt

# DEPENDENCIES INSTALLATION
.PHONY: local-pkg-install
PKG_CLI_CMD 		?=apt-get # Package manager executable
PKG_CLI_PAYLOAD 	?= 		# Payload file
PKG_CLI_PARAMETERS 	?= 	# Package manager installation parameters

local-pkg-install:
	$(PKG_CLI_CMD) $(PKG_CLI_PARAMETERS) `cat $(PKG_CLI_PAYLOAD)`
