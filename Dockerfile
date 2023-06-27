ARG TESTUTILS_BASE=""

FROM ${TESTUTILS_BASE}

ENV DEBIAN_FRONTEND noninteractive

LABEL \
    author="Jesmigel A. Cantos <jesmigel.developer@gmail.com>" \
    description="This image includes the dependencies for building ska-pst-send" \
    base="${TESTUTILS_BASE}" \
    org.skatelescope.team="PST Team" \
    org.skatelescope.version="0.0.0" \
    int.skao.application="ska-pst-testutils"

# COPY repository to container filesystem
COPY . /mnt/ska-pst-testutils
WORKDIR /mnt/ska-pst-testutils
RUN apt-get update -y && apt-get install -y make

# Install common apt dependencies
ARG DEPENDENCIES_PATH=dependencies
ARG PKG_CLI_PAYLOAD=${DEPENDENCIES_PATH}/apt.txt
ARG PKG_CLI_CMD=apt-get
ARG PKG_CLI_PARAMETERS='install --no-install-recommends -y'
RUN stat ${PKG_CLI_PAYLOAD} \
    && PKG_CLI_PAYLOAD=${PKG_CLI_PAYLOAD} PKG_CLI_PARAMETERS=${PKG_CLI_PARAMETERS} make local-pkg-install

# Install poetry as a binary
ENV POETRY_HOME=/opt/poetry
ARG POETRY_VERSION=""
RUN curl -sSL https://install.python-poetry.org | python3 - --yes

RUN ln -sfn /usr/bin/python3 /usr/bin/python && \
    ln -sfn /opt/poetry/bin/poetry /usr/local/bin/poetry && \
    poetry env use python3

# Install python dependencies through poetry
RUN poetry install && \
    poetry run bash -c 'make python-test'

CMD [ "bash" ]