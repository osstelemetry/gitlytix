#!/bin/bash

echo "🚀 Starting GitLytix Full Stack Application..."

# Build and start all services
echo "📦 Building and starting services..."
docker compose up --build --detach

echo "⏳ Waiting for services to start..."
sleep 15

# Check if all containers are running
echo "📋 Checking service status..."
docker compose ps

# Check ClickHouse
echo "🔍 Checking ClickHouse status..."
docker compose exec clickhouse clickhouse-client --query "SELECT 1" || echo "❌ ClickHouse not ready"

# Check if table was created and populated
echo "📊 Checking if github_events table was created..."
docker compose exec clickhouse clickhouse-client --query "SELECT COUNT(*) FROM github_events" || echo "❌ Table not found"

# Show sample data
echo "📈 Sample data by repository:"
docker compose exec clickhouse clickhouse-client --query "SELECT repo_name, event_type, COUNT(*) as count FROM github_events GROUP BY repo_name, event_type ORDER BY repo_name, count DESC LIMIT 20"

echo ""
echo "✅ Setup complete!"
echo "🌐 Frontend available at: http://localhost:3000"
echo "🔌 Backend API available at: http://localhost:8000"
echo "💾 ClickHouse available at: localhost:9001"
echo ""
echo "To stop services: docker compose down"
echo "To view logs: docker compose logs -f [service_name]"
echo "  Available services: frontend, backend, db-init, clickhouse" 