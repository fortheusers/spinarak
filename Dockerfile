FROM jfloff/alpine-python:latest-onbuild

WORKDIR /home/app
COPY pkggen.py /home/app

CMD python3 /home/app/spinarak.py
