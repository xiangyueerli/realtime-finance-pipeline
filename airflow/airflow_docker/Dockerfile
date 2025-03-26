
# Use an official Python runtime as a base image
FROM python:3.9-slim AS base
# Upgrade pip3 (optional, but recommended)
RUN python -m pip install --upgrade pip

# Set environment variable for Airflow home directory
ENV AIRFLOW_HOME=/opt/airflow

# Install system dependencies and pip3
RUN apt-get update && apt-get install -y \
    python3-pip \
    build-essential \
    libpq-dev \
    curl \
    && apt-get clean



# Install Airflow
FROM apache/airflow:2.5.1-python3.9
RUN pip3 install apache-airflow==2.5.1



# Install Java
USER root

RUN apt-get update && \
    apt-get install -y openjdk-11-jre wget supervisor && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

ENV JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64
ENV PATH=$JAVA_HOME/bin:$PATH


# Install Spark
ENV SPARK_VERSION=3.2.1
ENV SPARK_HADOOP_VERSION=3.2
RUN wget -q https://archive.apache.org/dist/spark/spark-${SPARK_VERSION}/spark-${SPARK_VERSION}-bin-hadoop${SPARK_HADOOP_VERSION}.tgz && \
    tar -xzf spark-${SPARK_VERSION}-bin-hadoop${SPARK_HADOOP_VERSION}.tgz -C /opt/ && \
    rm spark-${SPARK_VERSION}-bin-hadoop${SPARK_HADOOP_VERSION}.tgz

# Set Spark environment variables
ENV SPARK_HOME=/opt/spark-${SPARK_VERSION}-bin-hadoop${SPARK_HADOOP_VERSION}
ENV PATH=$PATH:${SPARK_HOME}/bin:${SPARK_HOME}/sbin

# Copy custom JAR files for Spark
COPY kafka-clients-3.4.0.jar $SPARK_HOME/jars/kafka-clients-3.4.0.jar
COPY postgresql-42.5.4.jar $SPARK_HOME/jars/postgresql-42.5.4.jar


# Install Python requirements
WORKDIR /opt/airflow/
COPY requirements.txt .
USER airflow
RUN pip3 install --user -r requirements.txt


# Copy initialization scripts
USER root
COPY init_db.sh /opt/airflow/init_db.sh
RUN chmod +x /opt/airflow/init_db.sh

# Copy supervisor configuration file
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Expose ports
EXPOSE 22
EXPOSE 3000
EXPOSE 4040
EXPOSE 8000

# Set permissions for Airflow directories
RUN mkdir -p /opt/airflow/logs && chown -R airflow:$(id -gn airflow) /opt/airflow/logs

# Switch to airflow user
USER airflow

ENTRYPOINT ["/entrypoint.sh"]
CMD ["bin/spark-class", "org.apache.spark.deploy.master.Master"]



# Install NLTK data 
# # Set the working directory
# WORKDIR /opt/airflow
# # Create a directory for NLTK data
# RUN mkdir -p /opt/airflow/nltk_data

# # Download specific NLTK data during the build
# RUN python -m nltk.downloader -d /opt/airflow/nltk_data punkt
# RUN python -m nltk.downloader -d /opt/airflow/nltk_data stopwords
# RUN python -m nltk.downloader -d /opt/airflow/nltk_data words
# RUN python -m nltk.downloader -d /opt/airflow/nltk_data wordnet
# RUN python -m nltk.downloader -d /opt/airflow/nltk_data omw-1.4
# RUN python -m nltk.downloader -d /opt/airflow/nltk_data averaged_perceptron_tagger

