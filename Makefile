DOCKER_COMPOSE ?= docker compose

.PHONY: start stop build seed

start:
	@echo "Starting GitLytix stack..."
	$(DOCKER_COMPOSE) up --detach

stop:
	@echo "Stopping GitLytix stack..."
	$(DOCKER_COMPOSE) down --remove-orphans

build:
	@echo "Building GitLytix images..."
	$(DOCKER_COMPOSE) build

seed:
	@echo "Ensuring ClickHouse is running..."
	$(DOCKER_COMPOSE) up --detach clickhouse
	@echo "Building latest db-init image..."
	$(DOCKER_COMPOSE) build db-init
	@echo "Seeding ClickHouse with demo data..."
	$(DOCKER_COMPOSE) run --rm db-init
