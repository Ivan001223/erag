#!/bin/bash

set -e

# 环境变量默认值
export APP_ENV=${APP_ENV:-production}
export WORKERS=${WORKERS:-4}
export HOST=${HOST:-0.0.0.0}
export PORT=${PORT:-8000}

echo "Starting Knowledge System Backend..."
echo "Environment: $APP_ENV"
echo "Workers: $WORKERS"
echo "Host: $HOST"
echo "Port: $PORT"

# 等待数据库连接
echo "Waiting for database connections..."

# 等待PostgreSQL
if [ ! -z "$DATABASE_URL" ]; then
    echo "Waiting for PostgreSQL..."
    until python -c "
import psycopg2
import os
import sys
try:
    conn = psycopg2.connect(os.environ['DATABASE_URL'])
    conn.close()
    print('PostgreSQL is ready!')
except:
    sys.exit(1)
"; do
        echo "PostgreSQL is unavailable - sleeping"
        sleep 2
    done
fi

# 等待Neo4j
if [ ! -z "$NEO4J_URL" ]; then
    echo "Waiting for Neo4j..."
    until python -c "
from neo4j import GraphDatabase
import os
import sys
try:
    driver = GraphDatabase.driver(
        os.environ['NEO4J_URL'],
        auth=(os.environ.get('NEO4J_USER', 'neo4j'), os.environ.get('NEO4J_PASSWORD', 'password'))
    )
    with driver.session() as session:
        session.run('RETURN 1')
    driver.close()
    print('Neo4j is ready!')
except:
    sys.exit(1)
"; do
        echo "Neo4j is unavailable - sleeping"
        sleep 2
    done
fi

# 等待Redis
if [ ! -z "$REDIS_URL" ]; then
    echo "Waiting for Redis..."
    until python -c "
import redis
import os
import sys
try:
    r = redis.from_url(os.environ['REDIS_URL'])
    r.ping()
    print('Redis is ready!')
except:
    sys.exit(1)
"; do
        echo "Redis is unavailable - sleeping"
        sleep 2
    done
fi

# 运行数据库迁移
if [ "$APP_ENV" != "test" ]; then
    echo "Running database migrations..."
    alembic upgrade head
fi

# 创建必要的目录
mkdir -p /app/logs /app/uploads /app/backups

echo "All services are ready!"

# 执行传入的命令
exec "$@" 