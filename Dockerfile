FROM python:3.9

RUN mkdir /app
WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip3 install -r /app/requirements.txt

COPY iss_tracker_app.py /app/iss_tracker_app.py
COPY test/test_iss_tracker.py /app/test/test_iss_tracker.py

ENTRYPOINT ["python"]
CMD ["iss_tracker_app.py"]
