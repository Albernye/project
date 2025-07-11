# Utilisez une image plus légère et sécurisée
FROM python:3.11-alpine

# Configuration des variables d'environnement
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    FLASK_APP=web/app.py \
    FLASK_ENV=production \
    PIP_NO_CACHE_DIR=on

# Créez un utilisateur non-root pour la sécurité
RUN adduser -D appuser
WORKDIR /app

# Installez les dépendances système uniquement nécessaires
RUN apk add --no-cache --virtual .build-deps gcc g++ python3-dev musl-dev postgresql-dev && \
    apk add --no-cache postgresql-libs
    
# Copiez d'abord les requirements pour bénéficier du cache Docker
COPY requirements.txt .

# Installez les dépendances Python avec cache pip
RUN pip install --cache-dir=/tmp/pip-cache --upgrade pip && \
    pip install --cache-dir=/tmp/pip-cache -r requirements.txt && \
    rm -rf /tmp/pip-cache

# Copiez l'application
COPY . .

# Nettoyez les dépendances de build inutiles
RUN apk del .build-deps

# Changez les permissions et propriétaire
RUN chown -R appuser:appuser /app
USER appuser

# Commande d'exécution optimisée
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "--worker-class", "gevent", "web.app:app"]
