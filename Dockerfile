FROM docker.io/library/python:3.14.0-slim-trixie
LABEL maintainer="github@mails.fudeus.net"

COPY requirements.txt /tmp
RUN pip3 install --no-cache-dir -r /tmp/requirements.txt

COPY pvoutput_reporter.py /usr/local/bin/pvoutput_reporter

ENTRYPOINT ["/usr/local/bin/pvoutput_reporter"]
