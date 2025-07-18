FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y build-essential libblas-dev liblapack-dev

# Install Python dependencies
COPY requirements-prod.txt .
RUN pip install --upgrade pip && pip install -r requirements-prod.txt

# Copy app files
COPY .env.prod .env
COPY config_app.py .
COPY app.py .
COPY solvers/ solvers/
COPY utils/ utils/

EXPOSE 5000

CMD ["python3", "-m", "flask", "run", "--host=0.0.0.0"]
