# SYN Tracker API

View the site: [here](https://synapse.dorime.org)

# Run

```sh
$ pip3 install -r requirements.txt
$ gunicorn --worker-class=gevent -w 1 -b 0.0.0.0:1337 main:app --capture-output
[2021-10-11 19:30:17 +0000] [1] [INFO] Starting gunicorn 20.1.0
[...]
```

# Dockerfile

```sh
$ docker-compose up
Building web
Sending build context to Docker daemon   21.5kB
Step 1/7 : FROM python:3.9-slim
 ---> 0d9b718e2063
[...]
```
