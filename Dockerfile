FROM jfloff/alpine-python:latest-onbuild

WORKDIR /home/app
COPY spinarak.py /home/app

CMD python3 /home/app/spinarak.py
