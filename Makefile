#
# This makefile is intended to be used for creating, publishing, and running
# the molmod produciton environment (locally).
#
compose = docker-compose.prod.yml

all: build

run: pull up

build:
	docker-compose -f $(compose) build --no-cache

pull:
	docker-compose -f $(compose) pull

push:
	docker-compose -f $(compose) push

up:
	docker-compose -f $(compose) up -d

stop:
	docker-compose -f $(compose) stop

down:
	docker-compose -f $(compose) down

logs:
	docker-compose -f $(compose) logs -f

secrets:
	python3 ./scripts/generate_secrets.py

ps:
	docker-compose -f $(compose) ps

restore:
	bash ./backup.sh restore
