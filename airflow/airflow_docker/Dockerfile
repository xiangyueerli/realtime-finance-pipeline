

# Use the official Airflow 2.8.1 image with Python 3.8 as the base
FROM apache/airflow:2.8.1-python3.8

# Set Airflow home directory
ENV AIRFLOW_HOME=/opt/airflow
# Set SQLAlchemy connection string explicitly so it's baked in early
ENV AIRFLOW__DATABASE__SQL_ALCHEMY_CONN=postgresql+psycopg2://airflow:airflow@postgres_container:5432/airflow
ENV AIRFLOW__CORE__EXECUTOR=LocalExecutor

# Switch to root for system-level installations
USER root

# Add Bullseye repository for openjdk-11-jre, install system dependencies
RUN echo "deb http://deb.debian.org/debian bullseye main" >> /etc/apt/sources.list.d/bullseye.list \
    && apt-get update \
    && apt-get install -y \
        openjdk-11-jre \
        wget \
        supervisor \
        postgresql-client \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && rm -f /etc/apt/sources.list.d/bullseye.list

# Set Java environment variables for Spark 3.2.1 compatibility
ENV JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64
ENV PATH=$JAVA_HOME/bin:$PATH

# Install Spark 3.2.1
ENV SPARK_VERSION=3.2.1
ENV SPARK_HADOOP_VERSION=3.2
RUN wget -q https://archive.apache.org/dist/spark/spark-${SPARK_VERSION}/spark-${SPARK_VERSION}-bin-hadoop${SPARK_HADOOP_VERSION}.tgz \
    && tar -xzf spark-${SPARK_VERSION}-bin-hadoop${SPARK_HADOOP_VERSION}.tgz -C /opt/ \
    && rm spark-${SPARK_VERSION}-bin-hadoop${SPARK_HADOOP_VERSION}.tgz

# Set Spark environment variables
ENV SPARK_HOME=/opt/spark-${SPARK_VERSION}-bin-hadoop${SPARK_HADOOP_VERSION}
ENV PATH=$PATH:${SPARK_HOME}/bin:${SPARK_HOME}/sbin

# Copy custom JAR files for Spark
COPY kafka-clients-3.4.0.jar $SPARK_HOME/jars/kafka-clients-3.4.0.jar
COPY postgresql-42.5.4.jar $SPARK_HOME/jars/postgresql-42.5.4.jar



# Switch to airflow user for Python installations
USER airflow

# Ensure .local/bin is in PATH for user-installed packages
ENV PATH="/home/airflow/.local/bin:$PATH"

# Install Python dependencies
WORKDIR /opt/airflow
COPY requirements.txt .
COPY deps /deps/
# RUN pip install --user psycopg2-binary pyspark==3.2.1 \
#     && if [ -f requirements.txt ]; then pip install --user -r requirements.txt; fi \
#     && rm -rf /home/airflow/.local/lib/python3.8/site-packages/airflow/example_dags \
#     && rm -rf /home/airflow/.cache/pip

# RUN pip install --user --no-index --find-links=/deps -r requirements.txt \
#     && pip install --user --no-index --find-links=/deps pyspark==3.2.1

RUN pip install --user --no-index --find-links=/deps psycopg2-binary pyspark==3.2.1 \
    && if [ -f requirements.txt ]; then pip install --user --no-index --find-links=/deps -r requirements.txt; fi \
    && rm -rf /home/airflow/.local/lib/python3.8/site-packages/airflow/example_dags \
    && rm -rf /home/airflow/.cache/pip

# Switch back to root to copy config files and set permissions
USER root

# Copy supervisor and entrypoint configuration
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf
COPY entrypoint.sh /opt/airflow/entrypoint.sh
RUN chmod +x /opt/airflow/entrypoint.sh

# Set permissions for Airflow directories
RUN mkdir -p /opt/airflow/logs && chown -R airflow:$(id -gn airflow) /opt/airflow/logs

# Expose ports (optional, controlled by docker-compose.yml)
EXPOSE 22 3000 4040 8000

# Use customedised airflow.cfg
COPY airflow.cfg /opt/airflow/airflow.cfg
RUN chown 50000:0 /opt/airflow/airflow.cfg


# Switch to airflow user for runtime
USER airflow




