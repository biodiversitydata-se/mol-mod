#
# This makefile is intended to be used for creating, publishing,
# and running the molmod produciton environment
#
compose = docker-compose.prod.yml
SHELL = bash

#
# GENERAL DOCKER
#

# Build service, or rebuild to implement changes in Dockerfile
build:
	docker-compose -f $(compose) build --no-cache

push:
	docker-compose -f $(compose) push

pull:
	docker-compose -f $(compose) pull

# Start service in background
up:
	docker-compose -f $(compose) up -d

stop:
	docker-compose -f $(compose) stop

# Stop and remove containers
down:
	docker-compose -f $(compose) down --remove-orphans

# Stop and remove containers, and remove network and volumes
clean:
	docker-compose -f $(compose) down -v

logs:
	docker-compose -f $(compose) logs -f

ps:
	docker-compose -f $(compose) ps

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

# Restore from latest (or specified) db dump
# Example: make restore (OR make restore file=some-db-dump.sql.tar)
restore:
	./scripts/database-backup.sh restore $(file)

#
# BLAST & FASTA
#

# Build blastdb from datasets with in_bioatlas = true
blastdb:
	python3 ./scripts/build_blast_db.py -v

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
# Test import
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
	./scripts/update-annotation.sh $(file) && make stats

#
# UPLOADS
#

# List uploaded files
uplist:
	docker exec asv-main ls /uploads

# Copy file(s) to host folder
# Apply to single file, if specified, or all files in dir
cpfile := $(if $(file),$(file),.)
# Example: make upcopy file=some-file.xlsx
upcopy:
	mkdir -p uploads && docker cp asv-main:/uploads/$(cpfile) uploads

# Delete files in container
delfile := $(if $(file),$(file),*)
updel:
	docker exec asv-main sh -c 'rm -rf /uploads/$(delfile)'
