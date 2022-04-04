FROM python:3.7-alpine
RUN pip install --upgrade pip

RUN adduser -D taxi
USER taxi
WORKDIR /home/taxi

COPY --chown=taxi:taxi requirements.txt requirements.txt
RUN pip install --user -r requirements.txt

COPY --chown=taxi:taxi . .
CMD ["python", "main.py"]