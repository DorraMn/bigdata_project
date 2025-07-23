FROM harisekhon/hbase:latest

# Passer root temporairement pour les installations
USER root

# Installer Python 3 (base Alpine)
RUN apk add --no-cache python3

# Créer le dossier de logs avec les permissions adéquates
RUN mkdir -p /hbase/logs && chown -R 1001:1001 /hbase

# Copier le script Python dans le conteneur
COPY get_hbase_config_dynamic.py /hbase-2.1.3/get_hbase_config_dynamic.py

# Donner les permissions nécessaires au script
RUN chmod +x /hbase-2.1.3/get_hbase_config_dynamic.py && chown 1001:1001 /hbase-2.1.3/get_hbase_config_dynamic.py

# Revenir à l'utilisateur HBase (user ID 1001)
USER 1001

# Définir le répertoire utilisateur
ENV HOME=/home/hbaseuser

# Lancer automatiquement le service HBase Master
CMD ["master"]
