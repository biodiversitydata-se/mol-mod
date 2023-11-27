#
# This makefile is intended to be used for creating, publishing,
# and running (primarily in the) the molmod production environment

compose = docker-compose.prod.yml
SHELL = bash

#
# GENERAL DOCKER
#

# Build service, or rebuild to implement changes in Dockerfile
build:
	docker compose -f $(compose) build --no-cache

push:
	docker compose -f $(compose) push

pull:
	docker compose -f $(compose) pull

# Start service in background
up:
	docker compose -f $(compose) up -d

stop:
	docker compose -f $(compose) stop

# Stop and remove containers
down:
	docker compose -f $(compose) down --remove-orphans

# Stop and remove containers, and remove network and volumes
clean:
	docker compose -f $(compose) down -v

logs:
	docker compose -f $(compose) logs -f

ps:
	docker compose -f $(compose) ps

#
# SECRETS
#

secrets:
	python3 ./scripts/generate_secrets.py --skip-existing

#
# BACKUP & RESTORE
#

# Just make a dabase dump
db-backup:
	./scripts/database-backup.sh data
# Make a full backup (db, logs & uploads)
backup:
	./scripts/scheduled-backup.sh

# Restore from latest (or specified) db dump
# Example: make restore (OR make restore file=some-db-dump.sql.tar)
restore:
	./scripts/database-backup.sh restore $(file)

#
# BLAST & FASTA
#

# Build blastdb from datasets with in_bioatlas = true
# First get name of blast worker as the component separator of autogenerated names
# differs between Docker Compose versions 1 ('_') & 2 ('-') on Mac, at least.
# Remember: this worker can multiply on demand, and such containers
# can't have fixed names in the Compose file (or service will break)
blastdb:
	$(eval worker=$(shell docker ps --format '{{.Names}}' | grep -E blast.*1))
	python3 ./scripts/build_blast_db.py --container ${worker} -v

# Export a fasta file to use in annotation update, filtering ASVs on target
# gene and (acronym part of) reference db.
# Example: make fasta ref="SBDI-GTDB-R07-RS207-1" target="16S rRNA"
fasta:
	$(eval worker=$(shell docker ps --format '{{.Names}}' | grep -E blast.*1))
	python3 ./scripts/build_blast_db.py --ref '$(ref)' --target '$(target)' --container ${worker} -v


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
# Example: make status pid=11 status=1 ruid=dr188 ipt=kth-2013-baltic-18s
status:
	python3 ./scripts/update_bas_status.py --pid $(pid) --status $(status) \
		--ruid $(ruid) --ipt $(ipt) -v

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
	mkdir -p backups/uploads && docker cp asv-main:/uploads/$(cpfile) backups/uploads

# Delete files in container
delfile := $(if $(file),$(file),*)
updel:
	docker exec asv-main sh -c 'rm -rf /uploads/$(delfile)'
