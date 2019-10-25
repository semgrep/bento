# Build Python Wheel
FROM python:3.7.4-stretch as builder

WORKDIR /
COPY . bento/

WORKDIR /bento
RUN pip install requests
RUN make package

#######################################

FROM circleci/python:3.6.9-stretch-node

USER root

RUN pip install pytest

COPY --from=builder /bento/dist/*.whl ./
RUN pip install *.whl

# Verify Installation
RUN node --version
RUN git --version
RUN bento --version

COPY ./tests /tests

RUN pytest tests/acceptance/qa.py