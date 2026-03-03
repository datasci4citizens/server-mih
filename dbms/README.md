# PostgreSQL
https://www.postgresql.org

# Infra Docker (PostgreSQL + MinIO)

Images:

- PostgreSQL: https://hub.docker.com/_/postgres
- MinIO: https://hub.docker.com/r/minio/minio

O arquivo `docker-compose-model.yml` contém a infraestrutura local:

- `db`: PostgreSQL 16 na porta `5432`
- `minio`: storage S3 compatível nas portas `9000` (API) e `9001` (console)
- volumes bind para `../../volumes/pg-data`, `../../volumes/pg-impexp` e `../../volumes/minio`

Pré-requisitos (no shell atual):

~~~
export MINIO_ACCESS_KEY=miniodev
export MINIO_SECRET_KEY=miniodev
~~~

Para subir:

~~~
docker compose -f docker-compose-model.yml up -d
docker compose -f docker-compose-model.yml ps
~~~

Para parar:

~~~
docker compose -f docker-compose-model.yml down
~~~

# Interaction

~~~
docker exec -it dbms-db-1 bash
psql -U postgres postgres
~~~

# PostgreSQL on Ubuntu

These are Ubuntu instructions. They may vary on Windows and Mac.

## Install Ubuntu

Installation instructions:
https://www.postgresql.org/download/linux/ubuntu/

The simplest approach probably will not install the latest version:
~~~
apt install postgresql
~~~

To install the latest one, follow the instructions of "manually configure the Apt repository".

## pgAdmin
https://www.pgadmin.org/

Detailed instructions to install pgAdmin via apt:
https://www.pgadmin.org/download/pgadmin-4-apt/

## Changing the Password

~~~
sudo -u postgres psql -c "ALTER USER postgres PASSWORD 'postgres';"
~~~

## Server Management

The three following commands start, stop, and show the status of the server at Ubuntu, respectively:

~~~
sudo systemctl start postgresql
sudo systemctl stop postgresql
sudo systemctl status postgresql
~~~

Reference: https://tableplus.com/blog/2018/10/how-to-start-stop-restart-postgresql-server.html

## Repository Location

To change the database location at Ubuntu:
https://www.digitalocean.com/community/tutorials/how-to-move-a-postgresql-data-directory-to-a-new-location-on-ubuntu-20-04
