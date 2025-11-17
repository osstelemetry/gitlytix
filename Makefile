DOCKER_COMPOSE ?= docker compose

.PHONY: start stop build

start:
	@echo "Starting GitLytix stack..."
	$(DOCKER_COMPOSE) up --detach

stop:
	@echo "Stopping GitLytix stack..."
	$(DOCKER_COMPOSE) down --remove-orphans

build:
	@echo "Building GitLytix images..."
	$(DOCKER_COMPOSE) build

