FROM python:3.9-slim

WORKDIR /site

COPY requirements.txt requirements.txt
RUN python -m pip install -r requirements.txt

# When rebuilding the docker image, the cache will end from here.
COPY . .

# Allow print statements to work.
ENV PYTHONUNBUFFERED=TRUE

CMD [ "gunicorn", "--worker-class=gevent", "-w", "4", "-b", "0.0.0.0:1337", "main:app", "--capture-output"]
