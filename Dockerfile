FROM python:latest

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements-prod.txt .

RUN pip install --upgrade pip
RUN pip install -r requirements-prod.txt

COPY .env.prod .env
COPY config_app.py config_app.py
COPY app.py app.py

EXPOSE 5000

CMD [ "python3", "-m" , "flask", "run", "--host=0.0.0.0"]