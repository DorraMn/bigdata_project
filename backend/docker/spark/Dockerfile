FROM bitnami/spark:latest

# Passer en root pour les installations système
USER root

# Installer Python3 et pip
RUN apt-get update && \
    apt-get install -y python3 python3-pip && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Créer le HOME et enregistrer l'utilisateur pour éviter les erreurs Ivy
RUN mkdir -p /home/sparkuser && \
    echo "sparkuser:x:1001:1001::/home/sparkuser:/bin/bash" >> /etc/passwd && \
    chown -R 1001:1001 /home/sparkuser

# ✅ Installer PySpark en tant que root
RUN pip3 install pyspark

# Revenir à l'utilisateur Bitnami (UID 1001)
USER 1001

# Variables d’environnement
ENV PYSPARK_PYTHON=python3
ENV PYSPARK_DRIVER_PYTHON=python3
ENV SPARK_LOCAL_IP=127.0.0.1
ENV JAVA_HOME=/opt/bitnami/java
ENV PATH="$JAVA_HOME/bin:$PATH"
ENV HOME=/home/sparkuser
ENV IVY_HOME=/home/sparkuser/.ivy2

# Copier le script de récupération de configuration
COPY get_spark_config.py /opt/bitnami/spark/get_spark_config.py

# Laisser le conteneur actif (à remplacer si nécessaire)
CMD /opt/bitnami/spark/bin/spark-submit /opt/bitnami/spark/get_spark_config.py && tail -f /dev/null

