# Build Stage
FROM --platform=linux/amd64 ubuntu:20.04 as builder

## Install build dependencies.
RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y cmake clang

## Add source code to the build stage.
ADD . /audioflux
WORKDIR /audioflux

## TODO: ADD YOUR BUILD INSTRUCTIONS HERE.
RUN mkdir build && \
    cd build/ && \
    cmake .. && \
    make

# Package Stage
FROM --platform=linux/amd64 ubuntu:20.04

## TODO: Change <Path in Builder Stage>
COPY --from=builder /audioflux/build/fuzzme /