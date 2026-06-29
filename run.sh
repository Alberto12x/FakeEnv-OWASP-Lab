#!/bin/bash

# 1. Asegurar limpieza total antes de arrancar
docker compose down

# 2. Recrear estructura de directorios de logs si no existe
mkdir -p logs/app logs/nginx logs/drupal/apache logs/drupal/mariadb
chmod 777 logs/drupal/mariadb

# 3. Poblar la base de datos de la app Flask
docker compose run --rm web python seed.py

# 4. Levantar todo el stack en segundo plano (App, Drupal, Wazuh, Indexer, Dashboard)
docker compose up -d --build

# 5. Poblar el blog de Drupal
docker compose exec drupal bash /seed/seed_blog.sh

# 6. Pausa de 30 segundos para estabilización inicial de Wazuh
sleep 5

# 7. Monitorizar las alertas del SIEM en tiempo real
docker compose exec wazuh tail -f /var/ossec/logs/alerts/alerts.json