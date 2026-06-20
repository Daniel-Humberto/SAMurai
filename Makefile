.PHONY: help up down logs models build restart env-setup status

help: ## Muestra los comandos disponibles
	@echo "Opciones disponibles:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

up: ## Inicia todos los contenedores de SAMurAI FutBotMX
	./samurai-futbot.sh up

down: ## Detiene la plataforma
	./samurai-futbot.sh down

build: ## Reconstruye backend y frontend
	./samurai-futbot.sh build

frontend: ## Reconstruye y actualiza solo el frontend
	./samurai-futbot.sh frontend

restart: ## Reinicia los contenedores
	./samurai-futbot.sh restart

logs: ## Muestra los logs en tiempo real de todos los contenedores
	./samurai-futbot.sh logs

models: ## Prepara checkpoints y voces locales
	./samurai-futbot.sh models

env-setup: ## Copia .env.example a .env si es necesario
	./samurai-futbot.sh env-setup

status: ## Muestra estado del stack y GPU
	./samurai-futbot.sh status
