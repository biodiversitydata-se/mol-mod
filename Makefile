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

psa:
	docker compose -f $(compose) ps -a

#
# SECRETS
#

secrets:
	python3 ./scripts/generate_secrets.py --skip-existing

#
# BACKUP & RESTORE
#

# Make full backup (db, logs & uploads)
backup:
	./scripts/scheduled-backup.sh
# Just make db dump
db-backup:
	./scripts/database-backup.sh data
# Make backup without db dump
nbackup:
	./scripts/scheduled-backup.sh -n

# Restore from latest (or specified) db dump
# Example: make restore (OR make restore file=some-db-dump.sql.tar)
restore:
	./scripts/database-backup.sh restore $(file)

#
# BLAST
#

# Build blastdb from datasets with in_bioatlas = true
# First get name of blast worker as the component separator of autogenerated names
# differs between Docker Compose versions 1 ('_') & 2 ('-') on Mac, at least.
# Remember: this worker can multiply on demand, and such containers
# can't have fixed names in the Compose file (or service will break)
blastdb:
	$(eval worker=$(shell docker ps --format '{{.Names}}' | grep -E blast.*1))
	python3 ./scripts/build_blast_db.py --container ${worker} -v

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
# Example: make status pid=3 status=1 ruid=dr963 ipt=kth-2013-baltic-18s
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
# VOLUME FILE MANAGEMENT - GENERAL
#

# Manage files in named volumes
# Set vol=[uploads|exports|fasta-exports] or see lazy options further down

# List files
# Example: make flist vol=uploads
flist:
	docker exec asv-main ls /app/$(vol)

# Copy file(s) to host
# Apply to single file, if specified, or all files in dir
cpfile := $(if $(file),$(file),.)
# Example: make fcopy vol=uploads [file=some-file.xlsx]
fcopy:
	mkdir -p $(vol) && docker cp asv-main:/app/$(vol)/$(cpfile) $(vol)

# Delete file(s) in container
delfile := $(if $(file),$(file),*)
# Example: make fdel vol=uploads [file=some-file.xlsx]
fdel:
	docker exec asv-main sh -c 'rm -rf /app/$(vol)/$(delfile)'

#
# UPLOADS
#

# List files
uplist:
	export vol=uploads && make flist

# Copy file(s) to host
# Apply to single file, if specified, or all files in dir
cpfile := $(if $(file),$(file),.)
# Example: make facopy [file=export-240202-114802.fasta]
upcopy:
	export vol=uploads file=$(cpfile) && make fcopy

# Delete file(s) in container
delfile := $(if $(file),$(file),*)
# Example: make exdel [file=export-240202-114802.fasta]
updel:
	export vol=uploads file=$(delfile) && make fdel

#
# DATASET-EXPORTS
#

# Export dataset(s) for download
# Apply to specified dataset_pid(s), or to all datasets if argument is omitted
# Or read dataset_pid(s) from file
# Examples: make export ds="1 4"
# Example: export ds=$(cat datasets.txt | tr '\n' ' ' | xargs)
#          make export ds="$ds"
export:
	python3 ./scripts/export_data.py -v $(if $(ds),--ds "$(ds)",)

# List files
exlist:
	export vol=exports && make flist

# Copy file(s) to host
# Apply to single file, if specified, or all files in dir
cpfile := $(if $(file),$(file),.)
# Example: make excopy [file=GU-2022-Wallhamn-18S.zip]
excopy:
	export vol=exports file=$(cpfile) && make fcopy

# Delete file(s) in container
delfile := $(if $(file),$(file),*)
# Example: make exdel [file=GU-2022-Wallhamn-18S.zip]
exdel:
	export vol=exports file=$(delfile) && make fdel

#
# FASTA-EXPORTS
#

# Export a fasta file to use in annotation update, filtering ASVs on target
# gene and (acronym part of) reference db.
# Example: make fasta ref="SBDI-GTDB-R07-RS207-1" target="16S rRNA"
fasta:
	python3 ./scripts/export_data.py -v --ref '$(ref)' --target '$(target)'
# Handle 'make fasta export' typo:
ifeq (fasta,$(filter fasta,$(MAKECMDGOALS)))
  ifeq (export,$(filter export,$(MAKECMDGOALS)))
    $(error "Don't mix 'make fasta' and 'make export', please")
  endif
endif


# List files
falist:
	export vol=fasta-exports && make flist

# Copy file(s) to host
# Apply to single file, if specified, or all files in dir
cpfile := $(if $(file),$(file),.)
# Example: make facopy [file=export-240202-114802.fasta]
facopy:
	export vol=fasta-exports file=$(cpfile) && make fcopy

# Delete file(s) in container
delfile := $(if $(file),$(file),*)
# Example: make exdel [file=export-240202-114802.fasta]
fadel:
	export vol=fasta-exports file=$(delfile) && make fdel

#
# MAINTENANCE
#

# Toggle maintenance message.
# (setting var directly in container (docker exec...), not useful as
# change is reversed during container restart)
# Example: make main routes="blast filter"
main:
	export MAINTENANCE_MODE=1 && \
	$(if $(routes), export MAINTENANCE_ROUTES="$(routes)" && ) \
	make up
nomain:
	export MAINTENANCE_MODE=0 && make up

# In development
dmain:
	export MAINTENANCE_MODE=1 && \
	$(if $(routes), export MAINTENANCE_ROUTES="$(routes)" && ) \
	docker compose -f docker-compose.yml up -d
dnomain:
	export MAINTENANCE_MODE=0 && \
	docker compose -f docker-compose.yml up -d
