#!/bin/bash
set -e

echo "Running Airflow DB initialization script"
/opt/airflow/init_db.sh

# Source environment variables
source /opt/airflow/airflow_env.sh


export SPARK_HOME=/opt/spark-${SPARK_VERSION}-bin-hadoop${SPARK_HADOOP_VERSION}
export PATH=$PATH:${SPARK_HOME}/bin:${SPARK_HOME}/sbin


# Check if the admin user already exists
ADMIN_USER_EXISTS=$(airflow users list | grep "admin" | wc -l)

# Create the admin user if it does not exist
if [ "$ADMIN_USER_EXISTS" == "0" ]; then
    airflow users create \
        --username admin \
        --password admin \
        --firstname Admin \
        --lastname Admin \
        --role Admin \
        --email admin@example.com
fi

# Start supervisord to run both webserver and scheduler
exec supervisord -c /etc/supervisor/conf.d/supervisord.conf
