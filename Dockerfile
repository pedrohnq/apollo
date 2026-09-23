# Imagem base: Python 3.12 na variante "slim" (menor, sem libs desnecessárias)
FROM python:3.12-slim

# Evita que o Python grave arquivos .pyc (desnecessário em container efêmero)
ENV PYTHONDONTWRITEBYTECODE=1
# Garante que logs apareçam em tempo real (sem buffer), essencial para docker logs
ENV PYTHONUNBUFFERED=1

# Diretório de trabalho dentro do container — todo comando abaixo roda a partir daqui
WORKDIR /app

# Copiamos APENAS o requirements.txt primeiro (não o projeto inteiro).
# Isso é proposital: o Docker cacheia cada instrução (layer). Se o código
# mudar mas as dependências não, essa camada de "pip install" é reaproveitada
# do cache, economizando minutos em cada build.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Só agora copiamos o restante do código-fonte da aplicação
COPY . .

# Copia o script de entrypoint e dá permissão de execução
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# EXPOSE é DOCUMENTAÇÃO, não faz a porta ser acessível de fato (ver seção 6.4)
EXPOSE 8000

# ENTRYPOINT define o "processo principal" que sempre roda ao iniciar o container
ENTRYPOINT ["/entrypoint.sh"]

# CMD é o argumento padrão passado ao ENTRYPOINT (pode ser sobrescrito na hora do "docker run")
CMD ["gunicorn", "apollo.wsgi:application", "--bind", "0.0.0.0:8000"]