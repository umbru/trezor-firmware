# initialize from the image

FROM python:3.7.3

ARG TOOLCHAIN_FLAVOR=linux
ENV TOOLCHAIN_FLAVOR=$TOOLCHAIN_FLAVOR

# install build tools and dependencies

RUN apt-get update && apt-get install -y \
    build-essential wget git libsodium-dev graphviz \
    valgrind check libssl-dev libusb-1.0-0-dev libudev-dev zlib1g-dev \
    libsdl2-dev libsdl2-image-dev

# install clang-format 6 from backports
RUN echo "deb http://deb.debian.org/debian stretch-backports main" > /etc/apt/sources.list.d/backports.list
RUN apt-get update && apt-get install -t stretch-backports -y clang-format-6.0
RUN ln -s clang-format-6.0 /usr/bin/clang-format

# TODO are all apt packages actually needed?

# Install Python 3.5 from Debian
RUN apt-get install -y python3.5-dev

# Install Python 3.6 and 3.8 from source, assuming we have 3.7 from the docker image
RUN wget --no-verbose https://www.python.org/ftp/python/3.6.9/Python-3.6.9.tgz
RUN tar zxf Python-3.6.9.tgz
RUN cd Python-3.6.9/ && ./configure && make && make install

RUN wget --no-verbose https://www.python.org/ftp/python/3.8.0/Python-3.8.0b3.tgz
RUN tar zxf Python-3.8.0b3.tgz
RUN cd Python-3.8.0b3/ && ./configure && make && make install

# install dependencies from toolchain source build

RUN if [ "$TOOLCHAIN_FLAVOR" = "src" ]; then \
        apt-get install -y autoconf autogen bison dejagnu \
                           flex flip gawk git gperf gzip nsis \
                           openssh-client p7zip-full perl python-dev \
                           libisl-dev tcl tofrodos zip \
                           texinfo texlive texlive-extra-utils; \
    fi

# download toolchain

ENV TOOLCHAIN_SHORTVER=8-2018q4
ENV TOOLCHAIN_LONGVER=gcc-arm-none-eabi-8-2018-q4-major
ENV TOOLCHAIN_URL=https://developer.arm.com/-/media/Files/downloads/gnu-rm/$TOOLCHAIN_SHORTVER/$TOOLCHAIN_LONGVER-$TOOLCHAIN_FLAVOR.tar.bz2
ENV TOOLCHAIN_HASH_linux=fb31fbdfe08406ece43eef5df623c0b2deb8b53e405e2c878300f7a1f303ee52
ENV TOOLCHAIN_HASH_src=bc228325dbbfaf643f2ee5d19e01d8b1873fcb9c31781b5e1355d40a68704ce7

# extract toolchain

RUN cd /opt && wget --no-verbose $TOOLCHAIN_URL

RUN cd /opt && echo "$TOOLCHAIN_HASH_linux $TOOLCHAIN_LONGVER-linux.tar.bz2\n$TOOLCHAIN_HASH_src $TOOLCHAIN_LONGVER-src.tar.bz2" | sha256sum -c --ignore-missing

RUN cd /opt && tar xfj $TOOLCHAIN_LONGVER-$TOOLCHAIN_FLAVOR.tar.bz2

# build toolchain (if required)

RUN if [ "$TOOLCHAIN_FLAVOR" = "src" ]; then \
        pushd /opt/$TOOLCHAIN_LONGVER ; \
        ./install-sources.sh --skip_steps=mingw32 ; \
        ./build-prerequisites.sh --skip_steps=mingw32 ; \
        ./build-toolchain.sh --skip_steps=mingw32,manual ; \
        popd ; \
    fi

# download protobuf

ENV PROTOBUF_VERSION=3.4.0
ENV PROTOBUF_HASH=e4b51de1b75813e62d6ecdde582efa798586e09b5beaebfb866ae7c9eaadace4
RUN wget --no-verbose "https://github.com/google/protobuf/releases/download/v${PROTOBUF_VERSION}/protoc-${PROTOBUF_VERSION}-linux-x86_64.zip"
RUN echo "${PROTOBUF_HASH} protoc-${PROTOBUF_VERSION}-linux-x86_64.zip" | sha256sum -c

# setup toolchain

ENV PATH=/opt/$TOOLCHAIN_LONGVER/bin:$PATH

ENV LC_ALL=C.UTF-8 LANG=C.UTF-8

# use zipfile module to extract files world-readable
ENV PYTHON=python

RUN $PYTHON -m zipfile -e "protoc-${PROTOBUF_VERSION}-linux-x86_64.zip" /usr/local && chmod 755 /usr/local/bin/protoc

ENV WORKON_HOME=/tmp/.venvs

# download monero tests binary

ENV TREZOR_MONERO_TESTS_SHA256SUM=140a16b3d6105b5e8e88a93b451e9600a36ed23928ea3cf2f975f9c83f36dab7
ENV TREZOR_MONERO_TESTS_URL="https://github.com/ph4r05/monero/releases/download/v0.14.1.0-tests-u14.04-01/trezor_tests"
ENV TREZOR_MONERO_TESTS_PATH="/opt/trezor_monero_tests"

RUN wget --no-verbose "$TREZOR_MONERO_TESTS_URL" -O "$TREZOR_MONERO_TESTS_PATH" \
    && chmod +x "$TREZOR_MONERO_TESTS_PATH"
RUN echo "${TREZOR_MONERO_TESTS_SHA256SUM} ${TREZOR_MONERO_TESTS_PATH}" | sha256sum -c

# install python dependencies

RUN pip install pipenv

RUN $PYTHON --version
RUN pip --version
RUN pipenv --version
