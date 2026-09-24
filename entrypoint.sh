#!/bin/sh
set -e

echo "Aguardando banco de dados ficar disponível..."

tentativa=0
until python -c "import socket; socket.create_connection(('db', 5432), timeout=2)" 2>/dev/null; do
  tentativa=$((tentativa + 1))
  if [ "$tentativa" -ge 30 ]; then
    echo "Banco não respondeu após 30 tentativas. Abortando." >&2
    exit 1
  fi
  sleep 1
done

echo "Aplicando migrações do Django..."
python manage.py migrate --noinput

echo "Coletando arquivos estáticos (relevante em produção)..."
python manage.py collectstatic --noinput --clear

echo "Iniciando servidor..."

exec "$@"