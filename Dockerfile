from ubuntu:14.04

# Install prerequisites
run apt-get update && apt-get install -y \
    build-essential \
    cmake \
    curl \
    git \
    libcurl3-dev \
    libleptonica-dev \
    liblog4cplus-dev \
    libopencv-dev \
    libtesseract-dev \
    wget \
    python-setuptools \
    python-dev \
    build-essential \
    python-pip

run wget -O - http://deb.openalpr.com/openalpr.gpg.key | sudo apt-key add - && \
    echo "deb http://deb.openalpr.com/master/ openalpr main" | sudo tee /etc/apt/sources.list.d/openalpr.list && \
    sudo apt-get update && \
    sudo apt-get install -y openalpr openalpr-daemon openalpr-utils libopenalpr-dev

# Copy all data
copy . /srv/openalpr

# Setup the build directory
run mkdir /srv/openalpr/src/build
workdir /srv/openalpr/src/build

# Setup the compile environment
run cmake -DCMAKE_INSTALL_PREFIX:PATH=/usr -DCMAKE_INSTALL_SYSCONFDIR:PATH=/etc .. && \
    make -j2 && \
    make install

run pip install /srv/openalpr/src/bindings/python

workdir /data

entrypoint ["/usr/bin/python", "/srv/openalpr/listener.py", "3000"]