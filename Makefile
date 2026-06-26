.PHONY: start stop restart logs shell status

## Start n8n in the background
start:
	cd docker && docker-compose up -d
	@echo "n8n is running at http://localhost:5678"

## Stop n8n
stop:
	cd docker && docker-compose down

## Restart n8n
restart:
	cd docker && docker-compose down && docker-compose up -d

## Follow n8n logs in real time
logs:
	cd docker && docker-compose logs -f n8n

## Open a shell inside the n8n container
shell:
	docker exec -it n8n-marketing /bin/sh

## Show running container status
status:
	cd docker && docker-compose ps
