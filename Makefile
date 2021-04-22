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

# Generate passwords, or use existing
secrets:
	python3 ./scripts/generate_secrets.py --skip-existing

wait:
	$(info Waiting for services to start)
	sleep 10

# Restore latest db dump in db container
restore:
	./backup.sh restore

# Build blastdb from datasets with in_bioatlas = true
blast-build:
	python3 ./scripts/build_blast_db.py

# Copy blastdb into worker container
blast-copy:
	for file in blast-databases/*; do docker cp $$file mol-mod_blast-worker_1:/blastdbs/; done;

# Build and copy blastdb into container
blast: blast-build blast-copy

# Update in_bioatlas status (to 0/1) for dataset pid and / or (when pid=0)
# stats view for datasets in_bioatlas = 1
status-update:
	python3 ./scripts/update_bas_status.py --container mol-mod_asv-main_1 $(pid) $(status) -v
