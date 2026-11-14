.PHONY: help up down logs db migrate migrations seed seed-reference test lint format check shell backup restore admin

PYTHON ?= python
MANAGE = $(PYTHON) backend/manage.py

help:
	@echo "make up              Demarre PostgreSQL et le backend (Docker)"
	@echo "make down            Arrete les conteneurs"
	@echo "make db              Demarre uniquement PostgreSQL"
	@echo "make migrate         Applique les migrations"
	@echo "make seed            Charge les donnees de demonstration"
	@echo "make seed-reference  Charge uniquement les referentiels"
	@echo "make test            Lance la suite de tests avec couverture"
	@echo "make lint            Verifie le style (ruff) et les migrations"
	@echo "make format          Formate le code"
	@echo "make admin           Cree un compte administrateur (Docker)"
	@echo "make backup          Sauvegarde base et medias dans backups/"
	@echo "make restore DUMP=... Restaure une sauvegarde (ecrase les donnees)"

up:
	docker compose up --build -d

down:
	docker compose down

logs:
	docker compose logs -f backend

db:
	docker compose up -d db

migrate:
	$(MANAGE) migrate

migrations:
	$(MANAGE) makemigrations

seed:
	$(MANAGE) seed_demo

seed-reference:
	$(MANAGE) seed_reference

test:
	$(PYTHON) -m pytest --cov --cov-report=term-missing

lint:
	$(PYTHON) -m ruff check .
	$(PYTHON) -m ruff format --check .
	$(MANAGE) makemigrations --check --dry-run

format:
	$(PYTHON) -m ruff check --fix .
	$(PYTHON) -m ruff format .

check:
	DJANGO_SETTINGS_MODULE=config.settings.prod $(MANAGE) check --deploy

shell:
	$(MANAGE) shell

STAMP := $(shell date +%Y%m%d-%H%M)
PG_USER ?= afridev
PG_DB ?= afridev

admin:
	docker compose exec backend python manage.py createsuperuser

backup:
	mkdir -p backups
	docker compose exec -T db pg_dump -U $(PG_USER) -d $(PG_DB) -Fc > backups/afridev-$(STAMP).dump
	docker compose cp backend:/app/media backups/media-$(STAMP)

restore:
	@test -n "$(DUMP)" || (echo "Usage : make restore DUMP=backups/fichier.dump" && exit 1)
	docker compose stop backend
	docker compose exec -T db pg_restore -U $(PG_USER) -d $(PG_DB) --clean --if-exists --no-owner < $(DUMP)
	docker compose start backend
