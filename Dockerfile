FROM python:3.9

ENV PYTHONUNBUFFERED=1

RUN pip install pipenv
COPY Pipfile* ./
RUN pipenv install --system

COPY thevyshka-reporter thevyshka-reporter/
CMD python -m thevyshka-reporter