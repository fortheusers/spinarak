FROM python:3.10.0-slim

WORKDIR /home/app

COPY spinarak.py /home/app
COPY galvantula.py /home/app
COPY requirements.txt /home/app

RUN pip install -r requirements.txt

CMD python3 /home/app/galvantula.py
