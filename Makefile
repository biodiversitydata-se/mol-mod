#
# This makefile is intended to be used for creating, publishing, and running
# the molmod produciton environment (locally).
#


all: build

run: pull up

build:
	docker-compose -f docker-compose.prod.yml build --no-cache

pull:
	docker-compose -f docker-compose.prod.yml pull

push:
	docker-compose -f docker-compose.prod.yml push

up:
	docker-compose -f docker-compose.prod.yml up -d
