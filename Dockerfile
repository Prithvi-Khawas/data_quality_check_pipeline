FROM apache/airflow:2.9.0-python3.11

# Install any additional dependencies
USER root
RUN apt-get update && apt-get install -y \
    libpq-dev gcc

# Switch to the airflow user to install Python packages
USER airflow
RUN pip install --no-cache-dir pandas pendulum
