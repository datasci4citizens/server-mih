# Molar Check - Servidor (API)

## Backend do Projeto Molar Check

Este é o repositório do **back-end** para o **Molar Check**, um sistema dedicado à identificação da Hipomineralização Molar-Incisivo (HMI).

A API foi desenvolvida para servir a aplicação front-end, gerenciando usuários, pacientes, registros, diagnósticos e o armazenamento seguro de imagens.

---

## ✨ Features

- **Autenticação e Autorização:**
    - Login social com Google OAuth2.
    - Sistema de papéis (roles) para distinguir `responsáveis` e `especialistas`.
- **Gerenciamento de Usuários e Pacientes:** Endpoints para criar, ler, atualizar e deletar usuários e seus pacientes associados.
- **Fluxo de Registros (MIH):**
    - Criação de registros de HMI com dados clínicos e observações.
    - Endpoints para especialistas avaliarem e atualizarem registros com um diagnóstico.
- **Upload de Imagens Seguro:**
    - Gera URLs pré-assinadas para o upload de imagens diretamente para um serviço de object storage (MinIO), evitando sobrecarga no servidor.
    - Associa os IDs das imagens aos registros dos pacientes.

---

## 🚀 Tecnologias Utilizadas

- [FastAPI](https://fastapi.tiangolo.com/)
- [Python 3.12+](https://www.python.org/)
- [SQLModel](https://sqlmodel.tiangolo.com/) para interação com o banco de dados e validação de dados.
- [PostgreSQL](https://www.postgresql.org/) como banco de dados relacional.
- [MinIO](https://min.io/) para armazenamento de objetos (imagens).
- [Docker](https://www.docker.com/) e [Docker Compose](https://docs.docker.com/compose/) para orquestração dos serviços.
- [Alembic](https://alembic.sqlalchemy.org/) para migrações de banco de dados.

---

## 🏁 Começando

Siga estas instruções para rodar o servidor e seus serviços dependentes localmente.

### Pré-requisitos

- [Docker](https://www.docker.com/get-started) e [Docker Compose](https://docs.docker.com/compose/install/)
- [Python](https://www.python.org/downloads/) (versão 3.12 ou superior)

### 1. Configuração do Banco de Dados e Armazenamento

O ambiente utiliza Docker para rodar o PostgreSQL e o MinIO.

1.  Na raiz do projeto, crie seu arquivo de ambiente a partir do modelo:
    ```bash
    cp .env-model .env-model
    ```
    Preencha as variáveis necessárias (credenciais Google OAuth, `SECRET_KEY`, etc.).

2.  Inicie todos os serviços (API, PostgreSQL e MinIO) com:
    ```bash
    docker-compose up -d
    ```

### 2. Configuração da Aplicação

1.  Crie um ambiente virtual e instale as dependências:
    ```bash
    python -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
    ```

### 3. Rodando o Servidor

1.  Execute as migrações do banco de dados com o Alembic:
    ```bash
    alembic upgrade head
    ```

2.  Inicie o servidor FastAPI:
    ```bash
    fastapi dev main.py
    ```

A API estará disponível em `http://localhost:8000/docs` para documentação interativa.

---

## 🌐 Visão Geral da API

A API é modularizada em diferentes roteadores:

- `/auth`: Lida com a autenticação (login com Google).
- `/users`: Gerenciamento de usuários (responsáveis e especialistas).
- `/users/patients`: Gerenciamento dos pacientes de um usuário.
- `/mih`: Gerenciamento dos registros de HMI e seus diagnósticos.
- `/images`: Geração de URLs para upload de imagens.
- `/healthz`: Health check do servidor.
