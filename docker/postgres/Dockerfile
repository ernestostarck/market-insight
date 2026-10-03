FROM postgis/postgis:17-3.5

COPY conf/postgresql.conf /etc/postgresql/postgresql.conf
COPY conf/pg_hba.conf /etc/postgresql/pg_hba.conf
COPY healthcheck.sh /usr/local/bin/healthcheck.sh
COPY init /docker-entrypoint-initdb.d

RUN apt-get update \
    && apt-get install -y --no-install-recommends postgresql-17-pgvector \
    && rm -rf /var/lib/apt/lists/* \
    && chmod 644 /etc/postgresql/postgresql.conf /etc/postgresql/pg_hba.conf \
    && chmod +x /usr/local/bin/healthcheck.sh

HEALTHCHECK --interval=10s --timeout=5s --retries=10 CMD ["/usr/local/bin/healthcheck.sh"]

CMD ["postgres", "-c", "config_file=/etc/postgresql/postgresql.conf", "-c", "hba_file=/etc/postgresql/pg_hba.conf"]
