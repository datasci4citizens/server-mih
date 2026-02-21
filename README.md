# Backend MIH (Django) — README

Este é o documento do backend do projeto MIH em Django. Ele serve como guia para manutenção, onboarding e evolução do sistema.

## 1. Visão Geral

O backend foi migrado de uma base anterior em FastAPI para Django + Django REST Framework (DRF), com os seguintes objetivos:

- padronizar a stack de backend
- manter compatibilidade com o frontend
- usar PostgreSQL como banco principal
- suportar autenticação por sessão e JWT
- consolidar persistência clínica em modelo OMOP

## 2. Arquitetura e Stack

### 2.1 Stack principal

- Python 3.11+
- Django 6.x
- Django REST Framework
- PostgreSQL (`psycopg2-binary`)
- `social-auth-app-django` (Google OAuth)
- `djangorestframework-simplejwt` (JWT)
- `django-cors-headers`

### 2.2 Organização do projeto

- `server_mih/manage.py`: entrada principal de execução
- `server_mih/server_mih/`: settings, urls, wsgi, asgi
- `mih/`: app principal com modelos, serializers, views e testes

### 2.3 Decisão arquitetural central

As entidades clínicas legadas (`Patient`, `Mih`, `TrackingRecord`) não são mais persistidas como tabelas próprias. O backend é **OMOP-only** para dados clínicos, mantendo compatibilidade de contratos HTTP por meio de camada de mapeamento nas views.

## 3. Guia Prático: Como Rodar o Backend

### 3.1 Pré-requisitos

- Python 3.11+
- PostgreSQL disponível
- `pip` e `venv`

### 3.2 Passo a passo (primeira execução)

1. Entrar na pasta do backend:

```bash
cd server-mih-dev-migration/server-django
```

2. Criar e ativar ambiente virtual:

```bash
python -m venv .venv
source .venv/bin/activate
```

3. Instalar dependências:

```bash
pip install -r requirements.txt
```

4. Subir o PostgreSQL do projeto (Docker):

```bash
docker start mih-postgres
docker ps | grep mih-postgres
```

5. Definir variáveis de ambiente (obrigatório: `DB_NAME`):

```bash
export DB_NAME=mi_db
export DB_USER=mi_user
export DB_PASSWORD=mi_pass
export DB_HOST=127.0.0.1
export DB_PORT=55432
export SECRET_KEY='trocar-em-producao'
```

6. Executar migrations:

```bash
python server_mih/manage.py migrate
```

7. Subir servidor de desenvolvimento:

```bash
python server_mih/manage.py runserver
```

Servidor padrão: `http://127.0.0.1:8000`

### 3.3 Fluxo diário recomendado

```bash
cd server-mih-dev-migration/server-django
source .venv/bin/activate
docker start mih-postgres
export DB_NAME=mi_db DB_USER=mi_user DB_PASSWORD=mi_pass DB_HOST=127.0.0.1 DB_PORT=55432 SECRET_KEY='trocar-em-producao'
python server_mih/manage.py runserver
```

### 3.4 Testes automatizados

```bash
cd server-mih-dev-migration/server-django
source .venv/bin/activate
export DB_NAME=mi_db DB_USER=mi_user DB_PASSWORD=mi_pass DB_HOST=127.0.0.1 DB_PORT=55432 SECRET_KEY='trocar-em-producao'
python server_mih/manage.py test --verbosity=2
```

Cobertura atual inclui:

- modelos OMOP base
- autenticação (sessão → JWT, `/user/me/`, `/users/`)
- upload de imagem via multipart

## 4. Endpoints Principais

### 4.1 Compatibilidade e autenticação

- `GET /user/me/` (compat frontend)
- `PUT /users/` (compat frontend)
- `GET /api/auth/user/`
- `POST /api/auth/token/` (sessão → JWT)

### 4.2 Recursos da API (`/api/`)

- `/api/patients/`
- `/api/mih/`
- `/api/tracking-records/`
- `/api/images/`

## 5. Upload de Imagens

`POST /api/images/` com `multipart/form-data`.

Exemplo:

```bash
curl -X POST -F "file=@photo.jpg" \
  -b "sessionid=<SESSION_COOKIE>" \
  http://127.0.0.1:8000/api/images/
```

Resposta esperada (201):

```json
{"id": 1}
```

Armazenamento local (dev): `media/images/YYYY/MM/DD/`

## 6. Mapeamento Detalhado FastAPI → OMOP

No servidor anterior em FastAPI, os dados clínicos eram centralizados nas tabelas `Patient`, `Mih` e `TrackingRecord`. Na migração para Django, essas tabelas deixaram de ser o núcleo de persistência e o backend passou a gravar dados clínicos em estruturas OMOP, principalmente `Person`, `ConditionOccurrence`, `Observation`, `Measurement`, `VisitOccurrence` e `FactRelationship`. A ideia foi separar melhor pessoa, eventos clínicos, observações e relacionamentos, aderindo ao padrão OMOP sem quebrar o contrato HTTP já consumido pelo frontend.

Na prática, tudo que era identidade e cadastro clínico básico de paciente passou a nascer em `Person`: o identificador legado ficou representado por `Person.id`, o nome foi preservado em `person_source_value` (em metadado JSON), e a data de nascimento foi decomposta em `year_of_birth`, `month_of_birth` e `day_of_birth`, como esperado no modelo. Os indicadores booleanos do histórico (como febre alta, prematuridade, problemas no parto e baixo peso) foram convertidos em ocorrências em `ConditionOccurrence`, usando conceitos técnicos internos (`910001` a `910004`). Já os valores descritivos, como tipo de parto e tipos de problemas no parto, migraram para `Observation.value_as_string` com os conceitos `910005` e `910006`, enquanto `brothersNumber` passou para `Observation.value_as_number` (`920001`). O tipo de consulta (`consultType`) foi modelado em `VisitOccurrence.visit_concept_id`, porque semanticamente representa um evento de atendimento.

O antigo registro de MIH foi reinterpretado como episódio clínico e, por isso, cada entrada virou uma ocorrência em `ConditionOccurrence` com `condition_concept_id=930001`. As datas de início e fim do registro passaram para `condition_start_date` e `condition_end_date`. A intensidade de dor (`painLevel`) foi mapeada para `Measurement.value_as_number` com `measurement_concept_id=930001`, já que se trata de medida clínica numérica. Campos como sensibilidade, mancha e desconforto estético foram para `Observation.value_as_concept_id` (`920006`, `920007`, `920008`) para representar booleanos de forma codificada; notas do responsável, notas do especialista e diagnóstico foram para `Observation.value_as_string` (`920003`, `920004`, `920005`); e as referências de imagem (`photo_id1`, `photo_id2`, `photo_id3`) foram armazenadas como número em `Observation.value_as_number` (`920009`, `920010`, `920011`).

No caso de `TrackingRecord`, o conteúdo textual de acompanhamento foi para `Observation` com `observation_concept_id=920002`, e o `image_id` ficou em `value_as_number` da própria observação. O vínculo entre esse acompanhamento e o episódio de MIH correspondente deixou de ser uma FK direta da tabela legada e passou a ser representado via `FactRelationship`, mantendo a ligação entre fatos clínicos sem violar a estrutura do OMOP.

Mesmo com a persistência OMOP, a API foi mantida com camada de compatibilidade em `mih/views.py`: o backend traduz payloads de entrada/saída para formatos próximos aos legados, para permitir evolução incremental do frontend sem exigir uma troca total de contrato em uma única etapa.

## 7. Modelos Fora do OMOP (Suporte de Aplicação)

- `UserProfile`: perfil de usuário, role e dados de autorização
- `Image`: arquivo enviado pelo usuário e metadados de upload

Esses modelos continuam fora do OMOP por serem dados de infraestrutura/aplicação, não eventos clínicos padronizados.

