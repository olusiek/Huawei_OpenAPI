FROM python:3.7.13-alpine3.14

LABEL author="olusiek"

ENV NODE_ENV=PROD

WORKDIR /
 
COPY huawei.py /usr/bin

RUN echo "*/2 * * * * root python3 /usr/bin/huawei.py >> /var/log/syslog 2>&1" >> /etc/crontabs/root
