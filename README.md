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

O backend persiste os dados clínicos nas estruturas OMOP `Person`, `ConditionOccurrence`, `Observation`, `Measurement`, `VisitOccurrence` e `FactRelationship`, com a tradução de payloads concentrada em `mih/views.py`.

Para paciente, `Person` representa identidade clínica base (`id`, `person_source_value`, `year_of_birth`, `month_of_birth`, `day_of_birth`, `birth_datetime`, `gender_concept_id`). Os indicadores clínicos (`highFever`, `premature`, `deliveryProblems`, `lowWeight`) são gravados em `Observation` com `observation_concept_id` clínico e `value_as_concept_id` (`YES`/`NO`). Campos categóricos (`deliveryType`, `consultType`) usam `Observation` com conceito da pergunta em `observation_concept_id` e conceito da resposta em `value_as_concept_id`. `brothersNumber` é persistido em `Observation.value_as_number`.

 Para MIH, o registro é representado como episódio clínico em `ConditionOccurrence` com `condition_concept_id=44783854` (Molar incisor hypomineralization). As datas de início e fim do registro são persistidas em `condition_start_date` e `condition_end_date`. A intensidade de dor (`painLevel`) é mapeada para `Measurement.value_as_number` com `measurement_concept_id=43055141` (escala numérica de dor 0–10). Sensibilidade e mancha são representadas em `Observation.value_as_concept_id` usando os conceitos clínicos `4247583` e `440758`, respectivamente, com resposta booleana codificada (`YES`/`NO`). O campo de desconforto estético permanece com conceito local de observação por ausência de um único `concept_id` OMOP padrão para essa pergunta específica. Notas do responsável, notas do especialista e diagnóstico seguem em `Observation.value_as_string`, e as referências de imagem (`photo_id1`, `photo_id2`, `photo_id3`) seguem em `Observation.value_as_number` com conceito local de aplicação.

Para acompanhamento (`tracking-records`), o texto é gravado em `Observation` (`observation_concept_id=920002`), `image_id` em `value_as_number` e o vínculo com o caso MIH é representado por `FactRelationship`.

### 6.1 Padrão adotado para IDs OMOP

O padrão adotado para `concept_id` foi:

- **priorizar IDs OMOP oficiais** (OHDSI Athena) quando há conceito clínico claro e estável;
- **separar conceito da pergunta e conceito da resposta** em campos categóricos;
- **usar conceitos custom locais** somente quando não há um único conceito OMOP padrão para a pergunta de negócio.

Fonte principal dos IDs oficiais: **OHDSI Athena** (`https://athena.ohdsi.org`).

Mapeamento adotado no backend (`mih/views.py`):

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

Valores categóricos utilizados:

- `deliveryType=cesarean` → `4015701`
- `deliveryType=normal` → `4125611`
- `consultType=public` → `44804377`
- `consultType=private` → `44803901`

Conceitos que permanecem **custom locais** por ausência de ID OMOP único para a pergunta de negócio:

- `deliveryProblemsTypes` (conceito-pergunta)
- `consultType` (conceito-pergunta)
- `aestheticDiscomfort` (conceito-pergunta de MIH)
- `userObservations`, `specialistObservations` e `diagnosis` em texto livre
- `photo_id1`, `photo_id2`, `photo_id3` como referência técnica de mídia

Observação importante: quando houver atualização oficial do dicionário de mapeamento do MolarCheck com novos `concept_id`, os valores locais custom devem ser substituídos e versionados em migration dedicada.

## 7. Modelos Fora do OMOP (Suporte de Aplicação)

- `UserProfile`: perfil de usuário, role e dados de autorização
- `Image`: arquivo enviado pelo usuário e metadados de upload
- `PatientNonClinicalInfos`: metadados não clínicos do paciente para suporte de contrato da API
- `ProviderNonClinicalInfos`: metadados não clínicos do especialista para suporte de autorização e contato

Esses modelos continuam fora do OMOP por serem dados de infraestrutura/aplicação, não eventos clínicos padronizados.

