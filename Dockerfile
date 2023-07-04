ARG SKA_PST_TESTUTILS_BASE_IMAGE=""

FROM ${SKA_PST_TESTUTILS_BASE_IMAGE}

ENV DEBIAN_FRONTEND noninteractive

LABEL \
    author="Jesmigel A. Cantos <jesmigel.developer@gmail.com>" \
    description="This image includes the dependencies for building ska-pst-testutils" \
    base="${SKA_PST_TESTUTILS_BASE_IMAGE}" \
    org.skatelescope.team="PST Team" \
    org.skatelescope.version="0.1.0" \
    int.skao.application="ska-pst-testutils"

WORKDIR /mnt

RUN apt-get update -y && apt-get install -y make

# Install common apt dependencies
ARG DEPENDENCIES_PATH=dependencies
ARG PKG_CLI_PAYLOAD=${DEPENDENCIES_PATH}/apt.txt
ARG PKG_CLI_CMD=apt-get
ARG PKG_CLI_PARAMETERS='install --no-install-recommends -y'

COPY dependencies/ /mnt/dependencies/
RUN stat ${PKG_CLI_PAYLOAD} && \
    apt-get install --no-install-recommends -y <${PKG_CLI_PAYLOAD}

COPY pyproject.toml poetry.lock* /mnt/
RUN poetry config virtualenvs.create false && \
  poetry install --with dev --without docs

COPY src/ /mnt/src/
COPY tests/ /mnt/tests/
RUN PYTHONPATH="/mnt/src" pytest --forked tests/

CMD [ "bash" ]
