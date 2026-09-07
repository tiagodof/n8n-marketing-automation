.PHONY: build start stop restart logs shell status test

## Build the n8n and reporting-service stack
build:
	cd docker && docker-compose build

## Start n8n and the private reporting service in the background
start:
	cd docker && docker-compose up -d --build
	@echo "n8n is running at http://localhost:5678"

## Stop the complete local stack
stop:
	cd docker && docker-compose down

## Restart the complete local stack
restart:
	cd docker && docker-compose down && docker-compose up -d --build

## Follow n8n logs in real time
logs:
	cd docker && docker-compose logs -f n8n

## Follow the private reporting service logs in real time
logs-reporting:
	cd docker && docker-compose logs -f reporting-service

## Open a shell inside the n8n container
shell:
	docker exec -it n8n-marketing /bin/sh

## Show running container status
status:
	cd docker && docker-compose ps

## Run automated tests for Module 01
test:
	python3 -m unittest discover -s modules/01-reporting-agent/tests -p 'test_*.py' -v
