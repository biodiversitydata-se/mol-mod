#
# This makefile is intended to be used for creating, publishing, and running
# the molmod produciton environment (locally).
#
compose = docker-compose.prod.yml
SHELL = bash

all: build

run: pull up

rebuild: clean secrets build up wait restore blast

# Build service, or rebuild to implement changes in Dockerfile
build:
	docker-compose -f $(compose) build --no-cache

pull:
	docker-compose -f $(compose) pull

push:
	docker-compose -f $(compose) push

# Start service in background
up:
	docker-compose -f $(compose) up -d

stop:
	docker-compose -f $(compose) stop

# Stop and remove containers
down:
	docker-compose -f $(compose) down

logs:
	docker-compose -f $(compose) logs -f

ps:
	docker-compose -f $(compose) ps

# Stop and remove containers, and remove network and volumes
clean:
	docker-compose -f $(compose) down -v

<<<<<<< HEAD
# Generate passwords, or use existing
secrets:
	python3 ./scripts/generate_secrets.py --skip-existing

# Restore latest db dump
restore:
	./backup.sh restore

# Copy blast database files into worker
=======
wait:
	$(info Waiting for services to start)
	sleep 10

>>>>>>> ac4198ebd180a9a809f19cc400b8d41c577859db
blast:
	for file in blast-databases/*; do docker cp $$file mol-mod_blast-worker_1:/blastdbs/; done;
