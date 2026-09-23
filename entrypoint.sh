#!/bin/sh
# "set -e" interrompe o script imediatamente se qualquer comando falhar,
# evitando que a aplicação suba em um estado inconsistente.
set -e

echo "Aguardando banco de dados ficar disponível..."
# Mesmo com o healthcheck do compose, reforçamos aqui como camada extra de segurança.
# Usamos a stdlib do Python em vez do pg_isready: a imagem slim não traz utilitários
# de Postgres, e instalá-los só para isso adicionaria ~30MB e uma dependência de rede no build.
# O contador evita que uma falha permanente vire um loop infinito silencioso.
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
# "exec" substitui o processo do shell pelo processo do gunicorn.
# Isso é importante para que sinais do sistema (ex: SIGTERM ao parar o container)
# cheguem diretamente ao gunicorn, permitindo um shutdown gracioso.
exec "$@"