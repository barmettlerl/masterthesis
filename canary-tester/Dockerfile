FROM python:3.12-slim as build 


WORKDIR /app

COPY requirements.txt ./requirements.txt

RUN pip3 install --no-cache-dir \
               --trusted-host pypi.org \
               --trusted-host files.pythonhosted.org \
               --trusted-host pypi.python.org \
               -r requirements.txt

COPY canary-tester/ .

EXPOSE 8000

CMD ["python", "./waitress_server.py"]
