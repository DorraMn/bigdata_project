FROM bitnami/java:1.8

USER root

ENV HBASE_VERSION=2.1.3
ENV HBASE_HOME=/opt/hbase-$HBASE_VERSION
ENV PATH="$HBASE_HOME/bin:$PATH"

RUN apt-get update && apt-get install -y python3 python3-pip curl tar && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /home/hbaseuser && \
    echo "hbaseuser:x:1001:1001::/home/hbaseuser:/bin/bash" >> /etc/passwd && \
    chown -R 1001:1001 /home/hbaseuser

RUN curl -sL https://archive.apache.org/dist/hbase/${HBASE_VERSION}/hbase-${HBASE_VERSION}-bin.tar.gz \
    | tar -xz -C /opt && \
    chown -R 1001:1001 $HBASE_HOME

# S'assurer que les fichiers existent au même niveau que le Dockerfile
COPY hbase-site.xml $HBASE_HOME/conf/hbase-site.xml
COPY get_hbase_config_dynamic.py $HBASE_HOME/get_hbase_config_dynamic.py

RUN chown 1001:1001 $HBASE_HOME/conf/hbase-site.xml $HBASE_HOME/get_hbase_config_dynamic.py && \
    chmod +x $HBASE_HOME/get_hbase_config_dynamic.py

USER 1001
ENV HOME=/home/hbaseuser

EXPOSE 16010 16020 2181

CMD ["hbase", "master", "start"]
