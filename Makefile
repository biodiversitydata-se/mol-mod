#
# This makefile is intended to be used for creating, publishing,
# and running the molmod produciton environment
#
compose = docker-compose.prod.yml
SHELL = bash

run: pull up

# Implement (updated) image, restore db, blastdb and stats page
test: clean pull up wait restore blast-copy stats

#
# GENERAL DOCKER
#

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
	docker-compose -f $(compose) down --remove-orphans

logs:
	docker-compose -f $(compose) logs -f

ps:
	docker-compose -f $(compose) ps

# Stop and remove containers, and remove network and volumes
clean:
	docker-compose -f $(compose) down -v

wait:
	$(info Waiting for services to start)
	sleep 10

#
# SECRETS
#

secrets:
	python3 ./scripts/generate_secrets.py --skip-existing

#
# DB BACKUP & RESTORE
#

backup:
	./scripts/database-backup.sh data

# Restore latest db dump in db container
restore:
	./scripts/database-backup.sh restore

#
# BLAST & FASTA
#

# Build blastdb from datasets with in_bioatlas = true
blast-build:
	python3 ./scripts/build_blast_db.py -v

# Copy blastdb into worker container
blast-copy:
	for file in blast-databases/*; do docker cp $$file mol-mod_blast-worker_1:/blastdbs/; done;

# Build and copy blastdb into container
blast: blast-build blast-copy

# Export a fasta file of all ASVs currently annotated with reference database
# Example: make fasta ref=UNITE:8.0
fasta:
	python3 ./scripts/build_blast_db.py --ref $(ref) -v

#
# DATA MANIPULATION
#

# Import Excel
# Example: make import file=/some/path/to/file.xlsx
import:
	python3 ./scripts/import_excel.py $(file) -v
dry-import:
	python3 ./scripts/import_excel.py $(file) -v --dry-run

# Update dataset status
# Example: make status pid=1 status=0 ruid=dr188
status:
	python3 ./scripts/update_bas_status.py --pid $(pid) --status $(status) --ruid $(ruid) -v
# Update stats view
stats:
	python3 ./scripts/update_bas_status.py -v

# Display menu for deleting datasets and related data
delete:
	./scripts/delete-dataset.sh

# Reannotate ASVs
reannot:
	# Example: make reannot file=/some/path/to/file.xlsx
	./scripts/update-annotation.sh $(file)
