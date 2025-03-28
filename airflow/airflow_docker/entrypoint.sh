#!/bin/bash
set -e

echo "🚨 Checking airflow.cfg:"
ls -l /opt/airflow/airflow.cfg && cat /opt/airflow/airflow.cfg | grep sql_alchemy_conn || echo " Not found"


# 🔒 Freeze airflow.cfg to prevent auto-overwrites
chmod 444 /opt/airflow/airflow.cfg
echo "🔒 airflow.cfg is now read-only"


echo "🚨 Environment variable:"
echo "$AIRFLOW__DATABASE__SQL_ALCHEMY_CONN"

echo "🚨 airflow config:"
airflow config get-value database sql_alchemy_conn || echo "⚠️ Airflow failed to read config!"



# Source environment variables (if airflow_env.sh adds anything extra)
source /opt/airflow/airflow_env.sh || echo "Warning: airflow_env.sh not found or failed"

# Debug: Print key environment variables to confirm they’re set
echo "DEBUG: AIRFLOW_HOME=$AIRFLOW_HOME"
echo "DEBUG: AIRFLOW__DATABASE__SQL_ALCHEMY_CONN=$AIRFLOW__DATABASE__SQL_ALCHEMY_CONN"
echo "DEBUG: AIRFLOW__CORE__EXECUTOR=$AIRFLOW__CORE__EXECUTOR"


# Wait for PostgreSQL to be ready
echo "⏳ Waiting for PostgreSQL to be available..."
while ! pg_isready -h postgres_container -p 5432 -U airflow; do
  sleep 2
done
echo "✅ PostgreSQL is ready!"

# Test PostgreSQL connection explicitly
echo "Testing PostgreSQL connection..."
python -c "import psycopg2; conn = psycopg2.connect('dbname=airflow user=airflow password=airflow host=postgres_container port=5432'); conn.close(); print('Connection successful!')" || {
  echo "ERROR: PostgreSQL connection failed!"
  exit 1
}

if [ -f /opt/airflow/airflow.cfg ]; then
    echo "Using pre-defined airflow.cfg – skipping db initialization"
else
    echo "airflow.cfg not found, generating new config..."
    airflow db init
    airflow db upgrade
fi


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
