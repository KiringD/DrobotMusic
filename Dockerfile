FROM ubuntu

RUN apt-get update && apt-get install -y python3 ffmpeg python3-pip

WORKDIR /code
COPY . /code
RUN pip3 install -r requirements.txt
CMD ["python3", "-u", "run.py"]

