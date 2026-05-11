#!/bin/bash

echo "========================================="
echo "Запуск HA проекта для диплома"
echo "========================================="

# Переход в директорию проекта
cd "$(dirname "$0")/.."

# Остановка старых контейнеров
echo "Останавливаю старые контейнеры..."
docker-compose down

# Сборка образов
echo "Собираю Docker образы..."
docker-compose build --no-cache

# Запуск
echo "Запускаю контейнеры..."
docker-compose up -d

# Ожидание готовности
echo "Ожидаю запуска сервисов (30 секунд)..."
sleep 30

# Проверка статуса
echo ""
echo "========================================="
echo "Проверка работоспособности:"
echo "========================================="

# Проверка Nginx
echo "Nginx:"
curl -s http://localhost:8080/health
echo ""

# Проверка приложения
echo ""
echo "FastAPI App:"
curl -s http://localhost:8080/ | python3 -m json.tool 2>/dev/null || curl -s http://localhost:8080/

echo ""
echo "========================================="
echo "Проект запущен!"
echo ""
echo "Доступные endpoints:"
echo "- Приложение: http://localhost:8080"
echo "- Документация API: http://localhost:8080/docs"
echo "- Prometheus: http://localhost:9090"
echo "- Grafana: http://localhost:3000 (admin/admin)"
echo ""
echo "Для остановки: docker-compose down"
echo "========================================="