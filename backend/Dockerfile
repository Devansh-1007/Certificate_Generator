FROM python:3.10.6-slim
COPY . /app
WORKDIR /app
RUN apt-get -y update && \
  apt-get install -y python3-dev default-libmysqlclient-dev build-essential && \
  pip install -r requirements.txt && \
  apt-get clean && apt-get autoremove
ENTRYPOINT python manage.py runserver 0.0.0.0:5000
EXPOSE 5000
