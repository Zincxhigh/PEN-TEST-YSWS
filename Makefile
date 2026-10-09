# PEN-TEST: `make` composes the docker arena and runs server.py.
#
#   make          # CTFd arena up in docker (detached) + server.py in foreground
#   make up       # full stack (site + arena) in docker, foreground
#   make run      # just server.py (expects the arena reachable)
#   make down     # stop everything
#   make help     # list targets

PORT ?= 5000
PYTHON ?= python3
COMPOSE ?= docker compose
INFRA ?= ctfd db cache nginx

.DEFAULT_GOAL := all
.PHONY: all help env install infra run up up-d down logs ps build clean

all: env infra run

help:
	@echo "Targets:"
	@echo "  make          - docker arena (detached) + run server.py (:$(PORT))"
	@echo "  make run      - run server.py locally on :$(PORT)"
	@echo "  make infra    - start CTFd arena services in docker (detached)"
	@echo "  make up       - full stack (web + arena) in docker, foreground"
	@echo "  make up-d     - full stack (web + arena) in docker, detached"
	@echo "  make down     - stop all compose services"
	@echo "  make logs     - follow compose logs"
	@echo "  make ps       - compose status"
	@echo "  make build    - build/rebuild images"
	@echo "  make install  - pip install requirements"
	@echo "  make env      - create .env from .env.example if missing"
	@echo "  make clean    - stop compose + drop CTFd volumes"

env:
	@test -f .env || { cp .env.example .env && echo "Created .env from .env.example"; }

install:
	$(PYTHON) -m pip install -r requirements.txt

# Arena only (no `web` service) so local server.py owns :$(PORT) with no conflict.
infra: env
	$(COMPOSE) up -d --build $(INFRA)
	@echo "Arena starting. Site: http://localhost:$(PORT)  CTFd: http://localhost:8000"

run: env
	PORT=$(PORT) $(PYTHON) server.py

up: env
	$(COMPOSE) up --build

up-d: env
	$(COMPOSE) up -d --build
	@echo "Full stack up. Site: http://localhost:$(PORT)  CTFd: http://localhost:8000"

down:
	$(COMPOSE) down

logs:
	$(COMPOSE) logs -f

ps:
	$(COMPOSE) ps

build:
	$(COMPOSE) build

clean:
	$(COMPOSE) down -v
