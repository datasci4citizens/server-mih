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

As entidades clínicas legadas (`Patient`, `Mih`, `TrackingRecord`) não são mais persistidas como tabelas próprias. O backend é **OMOP** para dados clínicos, mantendo compatibilidade de contratos HTTP por meio de camada de mapeamento nas views.

## 3. Guia Prático: Como Rodar o Backend

### 3.1 Pré-requisitos

- Python 3.11+
- Docker + Docker Compose
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

4. Subir a infraestrutura via Docker Compose:

```bash
cd dbms
export MINIO_ACCESS_KEY=minioadmin
export MINIO_SECRET_KEY=minioadmin123
docker compose -f docker-compose-model.yml up -d
docker compose -f docker-compose-model.yml ps
cd ..
```

5. Definir variáveis de ambiente do backend:

```bash
export DB_NAME=postgres
export DB_USER=postgres
export DB_PASSWORD=postgres
export DB_HOST=127.0.0.1
export DB_PORT=5432
export SECRET_KEY='trocar-em-producao'
export ALLOWED_HOSTS='localhost,127.0.0.1,0.0.0.0'
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
cd dbms
export MINIO_ACCESS_KEY=minioadmin MINIO_SECRET_KEY=minioadmin123
docker compose -f docker-compose-model.yml up -d
cd ..
export DB_NAME=postgres DB_USER=postgres DB_PASSWORD=postgres DB_HOST=127.0.0.1 DB_PORT=5432 SECRET_KEY='trocar-em-producao' ALLOWED_HOSTS='localhost,127.0.0.1,0.0.0.0'
python server_mih/manage.py runserver
```

### 3.4 Testes automatizados

```bash
cd server-mih-dev-migration/server-django
source .venv/bin/activate
export DB_NAME=postgres DB_USER=postgres DB_PASSWORD=postgres DB_HOST=127.0.0.1 DB_PORT=5432 SECRET_KEY='trocar-em-producao' ALLOWED_HOSTS='localhost,127.0.0.1,0.0.0.0'
python server_mih/manage.py test --verbosity=2
```

Cobertura atual inclui:

- modelos OMOP base
- autenticação (sessão → JWT, `/user/me/`, `/users/`)
- upload de imagem via multipart

### 3.5 Modo Docker Model (PostgreSQL + MinIO)


- `dbms/docker-compose-model.yml`

Esse compose sobe:

- `db`: PostgreSQL 16 (porta `5432`)
- `minio`: armazenamento S3 compatível (API `9000`, console `9001`)

Pré-requisito para o MinIO (no shell atual):

```bash
export MINIO_ACCESS_KEY=minioadmin
export MINIO_SECRET_KEY=minioadmin123
```

Subir infraestrutura:

```bash
cd server-mih-dev-migration/server-django/dbms
docker compose -f docker-compose-model.yml up -d
docker compose -f docker-compose-model.yml ps
```

Parar infraestrutura:

```bash
docker compose -f docker-compose-model.yml down
```

Observações importantes:

- os volumes são bind mounts para `../../volumes/pg-data`, `../../volumes/pg-impexp` e `../../volumes/minio`
- ajuste permissões/pastas se estiver em outro ambiente
- se já houver PostgreSQL local usando `5432`, ajuste a porta no compose para evitar conflito

### 3.6 Armazenamento de imagens no backend atual

No backend Django desta branch, o upload em `POST /api/images/` persiste arquivo no MinIO (bucket definido em `MINIO_IMAGES_BUCKET`) e retorna `{"id": ...}`.

Para consumo da imagem pelo frontend, utilize:

- `GET /api/images/{id}/content/`

O arquivo binário é servido pelo endpoint `GET /api/images/{id}/content/` a partir do objeto armazenado no MinIO.

## 4. Guia de Rotas e Endpoints

Base local padrão: `http://127.0.0.1:8000`

### 4.1 Rotas de autenticação e sessão

- `GET /user/me/` — retorna usuário autenticado (compatibilidade com frontend legado).
- `PUT /users/` — cria/atualiza dados de perfil do usuário autenticado.
- `GET /api/auth/user/` — retorna usuário autenticado (rota API equivalente ao `/user/me/`).
- `POST /api/auth/token/` — converte sessão autenticada em token JWT.

### 4.2 Rotas OAuth (Google)

As rotas são expostas por `social_django` sob o prefixo `/auth/`:

- `GET /auth/login/google-oauth2/` — inicia fluxo de login Google.
- `GET /auth/complete/google-oauth2/` — callback do provedor após autenticação.
- `GET /auth/logout/` — encerra sessão social/autenticada.

### 4.3 Rotas de recursos (`/api/`)

Os recursos abaixo seguem padrão de ViewSet REST (`list`, `retrieve`, `create`, `update`, `destroy`):

- `GET /api/patients/` — lista pacientes
- `GET /api/patients/{id}/` — detalha paciente
- `POST /api/patients/` — cria paciente
- `PUT /api/patients/{id}/` — atualiza paciente
- `DELETE /api/patients/{id}/` — remove paciente

- `GET /api/mih/` — lista casos MIH
- `GET /api/mih/{id}/` — detalha caso MIH
- `POST /api/mih/` — cria caso MIH
- `PUT /api/mih/{id}/` — atualiza caso MIH
- `DELETE /api/mih/{id}/` — remove caso MIH

- `GET /api/tracking-records/` — lista acompanhamentos
- `GET /api/tracking-records/{id}/` — detalha acompanhamento
- `POST /api/tracking-records/` — cria acompanhamento
- `PUT /api/tracking-records/{id}/` — atualiza acompanhamento
- `DELETE /api/tracking-records/{id}/` — remove acompanhamento

- `GET /api/images/` — lista imagens
- `GET /api/images/{id}/` — detalha imagem
- `GET /api/images/{id}/content/` — retorna o arquivo da imagem por `id`
- `POST /api/images/` — upload de imagem (`multipart/form-data`, campo `file`)
- `PUT /api/images/{id}/` — atualiza metadados de imagem
- `DELETE /api/images/{id}/` — remove imagem

### 4.4 Rotas administrativas e utilitárias

- `GET /admin/` — painel administrativo Django.


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

Armazenamento: MinIO (`MINIO_IMAGES_BUCKET`), com chave de objeto persistida na tabela `Image`.

## 6. Mapeamento Detalhado FastAPI → OMOP

O backend persiste os dados clínicos nas estruturas OMOP `Person`, `ConditionOccurrence`, `Observation`, `Measurement`, `VisitOccurrence` e `FactRelationship`, com a tradução de payloads concentrada em `mih/views.py`.

Para paciente, `Person` representa identidade clínica base (`id`, `person_source_value`, `year_of_birth`, `month_of_birth`, `day_of_birth`, `birth_datetime`, `gender_concept_id`). Os indicadores clínicos (`highFever`, `premature`, `deliveryProblems`, `lowWeight`) são gravados em `Observation` com `observation_concept_id` clínico e `value_as_concept_id` (`YES`/`NO`). Campos categóricos (`deliveryType`, `consultType`) usam `Observation` com conceito da pergunta em `observation_concept_id` e conceito da resposta em `value_as_concept_id`. `brothersNumber` é persistido em `Observation.value_as_number`.

 Para MIH, o registro é representado como episódio clínico em `ConditionOccurrence` com `condition_concept_id` (Molar incisor hypomineralization). As datas de início e fim do registro são persistidas em `condition_start_date` e `condition_end_date`. A intensidade de dor (`painLevel`) é mapeada para `Measurement.value_as_number` com `measurement_concept_id` (escala numérica de dor 0–10). Sensibilidade e mancha são representadas em `Observation.value_as_concept_id` usando os conceitos clínicos `4247583` e `440758`, respectivamente, com resposta booleana codificada (`YES`/`NO`). O campo de desconforto estético permanece com conceito local de observação por ausência de um único `concept_id` OMOP padrão para essa pergunta específica. Notas do responsável, notas do especialista e diagnóstico seguem em `Observation.value_as_string`, e as referências de imagem (`photo_id1`, `photo_id2`, `photo_id3`) seguem em `Observation.value_as_number` com conceito local de aplicação.

Para acompanhamento (`tracking-records`), o texto é gravado em `Observation` (`observation_concept_id`), `image_id` em `value_as_number` e o vínculo com o caso MIH é representado por `FactRelationship`.

### 6.1 Padrão adotado para IDs OMOP

O padrão adotado para IDs foi:

- **priorizar IDs OMOP oficiais** (OHDSI Athena) quando há conceito clínico claro e estável;
- **separar conceito da pergunta e conceito da resposta** em campos categóricos;
- **usar conceitos custom locais** somente quando não há um único conceito OMOP padrão para a pergunta de negócio.

Fonte principal dos IDs oficiais: **OHDSI Athena** (`https://athena.ohdsi.org`).

Mapeamento adotado no backend (`mih/views.py`):

#### 6.1.1 IDs OMOP oficiais

- `highFever` → `44810013` (`Observation`)
- `premature` → `4272248` (`Observation`)
- `deliveryProblems` → `43530950` (`Observation`)
- `lowWeight` → `4171115` (`Observation`)
- `deliveryType` (conceito-pergunta) → `4145318` (`Observation`)
- `brothersNumber` (conceito-pergunta) → `4072485` (`Observation`)
- `mih` (condição principal) → `44783854` (`ConditionOccurrence`)
- `painLevel` (escala 0–10) → `43055141` (`Measurement`)
- `sensitivityField` → `4247583` (`Observation`)
- `stain` → `440758` (`Observation`)
- `YES` / `NO` (booleanos) → `4188539` / `4188540` (`value_as_concept_id`)

Valores categóricos com IDs oficiais utilizados:

- `deliveryType=cesarean` → `4015701`
- `deliveryType=normal` → `4125611`
- `consultType=public` → `44804377`
- `consultType=private` → `44803901`

#### 6.1.2 IDs custom locais (não OMOP)

Conceitos locais (IDs técnicos da aplicação) usados no backend:

- `deliveryProblemsTypes` (conceito-pergunta) → `910006`
- `consultType` (conceito-pergunta) → `910007`
- `tracking-records` texto livre (`Observation`) → `920002`
- `userObservations` (notas do responsável) → `920003`
- `specialistObservations` (notas do especialista) → `920004`
- `diagnosis` (texto de diagnóstico) → `920005`
- `aestheticDiscomfort` (conceito-pergunta de MIH) → `920008`
- `photo_id1` (referência de mídia) → `920009`
- `photo_id2` (referência de mídia) → `920010`
- `photo_id3` (referência de mídia) → `920011`

Conceitos que permanecem **custom locais** por ausência de ID OMOP único para a pergunta de negócio:

- `deliveryProblemsTypes` (`910006`)
- `consultType` (`910007`)
- `aestheticDiscomfort` (`920008`)
- `userObservations`, `specialistObservations` e `diagnosis` (`920003`, `920004`, `920005`)
- `photo_id1`, `photo_id2`, `photo_id3` (`920009`, `920010`, `920011`)
- `tracking-records` texto livre (`920002`)

Observação importante: quando houver atualização oficial do dicionário de mapeamento do MolarCheck com novos `concept_id`, os valores locais custom devem ser substituídos e versionados em migration dedicada.

### 6.2. Modelos Fora do OMOP (Suporte de Aplicação)

- `UserProfile`: perfil de usuário, role e dados de autorização
- `Image`: arquivo enviado pelo usuário e metadados de upload
- `PatientNonClinicalInfos`: metadados não clínicos do paciente para suporte de contrato da API
- `ProviderNonClinicalInfos`: metadados não clínicos do especialista para suporte de autorização e contato

Esses modelos continuam fora do OMOP por serem dados de infraestrutura/aplicação, não eventos clínicos padronizados.

