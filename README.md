# Molar Check
System for the identification of Molar Incisor Hypomineralization.

This project embraces the server implementation for the MIH application.

## Directory Structure (Old)

* `install` - installation instructions of the PostgreSQL in docker plus the SQLModel and FastAPI libraries;
* `model` - schemas and diagrams of the data model;
* `src` - server source code in Python.

## Running the Main Server Application

### 0 - Clone the repository
~~~
git clone https://github.com/seu-usuario/mih-backend.git
cd mih-backend
~~~

### 1 - Start the PostgreSQL database with docker
* Create a copy of **/install/dbms/docker-compose-model.yml** and rename it **docker-compose.yml**.
* Make 2 directories, **docker** and **impexp**, and use their path on their respective volumes inside **docker-compose.yml**.
~~~
docker-compose up
~~~

### 3 - Create a virtual environment and install the requirements
~~~
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
~~~

### 5 - Start FastAPI
* Copy **.env-model**, rename it **.env** and change the needed environment variables.
~~~
fastapi dev main.py
~~~