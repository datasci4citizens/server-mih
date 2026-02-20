# Documentação Técnica do Backend (Django)

## 1. Visão Geral

Este documento descreve de forma detalhada a construção do backend do projeto **MIH**, migrado de uma base anterior em FastAPI para **Django + Django REST Framework (DRF)**, com foco em:

- padronização da API
- compatibilidade com o frontend existente
- uso de PostgreSQL
- suporte a autenticação social e JWT
- estrutura inicial para mapeamento OMOP

A implementação foi realizada no diretório `server-mih-dev-migration/server-django`.

---

## 2. Objetivos da Migração

### 2.1 Objetivos funcionais

1. Reimplementar os recursos principais da API anterior em Django.
2. Manter continuidade operacional do frontend (compatibilidade de endpoints).
3. Centralizar autenticação em sessão + JWT.
4. Suportar upload e persistência de imagens.
5. Estruturar base de domínio para evolução em padrão OMOP.

### 2.2 Objetivos técnicos

1. Padronizar stack Python em Django/DRF.
2. Utilizar PostgreSQL como banco principal (sem fallback para SQLite em runtime).
3. Garantir versionamento de schema com migrations.
4. Cobrir fluxo principal com testes automatizados.

---

## 3. Stack Tecnológica

### 3.1 Linguagem e framework

- **Python 3.11+**
- **Django (>=4.2)**
- **Django REST Framework**

### 3.2 Banco de dados

- **PostgreSQL**
- Driver: `psycopg2-binary`

### 3.3 Autenticação e segurança

- `social-auth-app-django` (Google OAuth)
- `djangorestframework-simplejwt` (JWT)
- `django-cors-headers` (CORS)

### 3.4 Configuração

- `python-dotenv` para carga de variáveis de ambiente

Dependências em `requirements.txt`:

- Django>=4.2
- djangorestframework
- psycopg2-binary
- python-dotenv
- django-cors-headers
- social-auth-app-django
- djangorestframework-simplejwt

---

## 4. Arquitetura do Backend

## 4.1 Organização de projeto

- `server_mih/` (projeto Django: settings/urls/wsgi/asgi)
- `mih/` (app principal de domínio e API)

### 4.2 Camadas lógicas

1. **Camada HTTP/API**: `views.py` e `auth_views.py`
2. **Camada de serialização**: `serializers.py`
3. **Camada de domínio/dados**: `models.py` e `omop_models.py`
4. **Camada de roteamento**: `mih/urls.py` + `server_mih/urls.py`
5. **Camada de persistência**: PostgreSQL + migrations

### 4.3 Decisão arquitetural central

O sistema foi consolidado em **modelo OMOP-only para entidades clínicas**.

- Entidades clínicas legadas (`Patient`, `Mih`, `TrackingRecord`) foram removidas do domínio persistente.
- Endpoints legados continuam existindo por compatibilidade, porém fazem mapeamento para tabelas OMOP.
- Modelos de suporte fora de OMOP permanecem apenas quando necessários ao framework/aplicação (`UserProfile` e `Image`).

---

## 5. Modelagem de Dados

## 5.1 Modelos de suporte (`mih/models.py`)

### `Image`
Upload e metadados de arquivos:
- `file` com upload local em `media/images/%Y/%m/%d`
- `extension` preenchida automaticamente no `save()`
- vínculo com usuário

### `UserProfile` (compatibilidade com frontend)
Modelo OneToOne com usuário Django:
- `role` (`responsible`/`specialist`)
- `is_allowed`
- telefone/endereço
- aceite de TCLE

Objetivo: suportar regras de autenticação/autorização e guardas do frontend.

## 5.2 Modelos OMOP (`mih/omop_models.py`)

Foram implementados modelos OMOP para persistência clínica:

- `Location`
- `Provider`
- `Person`
- `VisitOccurrence`
- `ConditionOccurrence`
- `Observation`
- `Measurement`
- `FactRelationship`

Esses modelos são a base principal de dados clínicos do backend.

---

## 6. API e Endpoints

## 6.1 Endpoints de autenticação e usuário

- `GET /user/me/` (compatibilidade frontend)
- `GET /api/auth/user/`
- `POST /api/auth/token/` (sessão -> JWT)
- `PUT /users/` (compatibilidade para atualizar perfil atual)

### Detalhes de compatibilidade importantes

- O frontend utiliza `PUT /users/`; foi criada `UpsertCurrentUserProfileView`.
- O frontend utiliza `/api/patients`, `/api/mih` e `/api/tracking-records`; essas rotas foram mantidas, porém agora com persistência OMOP via camada de mapeamento.

## 6.2 Endpoints DRF (router)

Via `DefaultRouter` em `/api/`:

- `/api/patients/`
- `/api/mih/`
- `/api/tracking-records/`
- `/api/images/`

---

## 7. Autenticação e Autorização

## 7.1 Mecanismos

- Sessão Django (cookie) para fluxo social/login tradicional
- JWT para consumo de API quando necessário

## 7.2 Backend de autenticação

- `social_core.backends.google.GoogleOAuth2`
- `django.contrib.auth.backends.ModelBackend`

## 7.3 Configuração DRF

`DEFAULT_AUTHENTICATION_CLASSES`:
- SessionAuthentication
- JWTAuthentication

Permissões padrão:
- `IsAuthenticatedOrReadOnly`

---

## 8. CORS, Hosts e Integração com Frontend

## 8.1 Hosts permitidos

`ALLOWED_HOSTS` configurado para ambiente local:
- localhost
- 127.0.0.1
- 0.0.0.0
- [::1]

## 8.2 CORS

`CORS_ALLOWED_ORIGINS` inclui origens locais de desenvolvimento (porta 5173 e 8000).

`CORS_ALLOW_CREDENTIALS = True` permite envio de cookies de sessão em requisições cross-origin do frontend.

---

## 9. Banco de Dados e Migrations

## 9.1 Estratégia

- Banco principal: PostgreSQL
- Configuração por variáveis de ambiente
- Migrações Django para controle de schema

## 9.2 Migrações relevantes

- `0001_initial.py`
- `0002_image_file_alter_image_extension.py`
- `0003_userprofile.py`
- `0004_remove_trackingrecord_mih_remove_patient_user_and_more.py` (remoção das classes legadas clínicas)

---

## 10. Upload de Arquivos

- Upload via endpoint de imagens (`multipart/form-data`)
- Persistência local em `MEDIA_ROOT`
- Em ambiente de produção, recomendado migrar para object storage (S3/compatível)

---

## 11. Testes Automatizados

Estrutura em `mih/tests/`:

- `test_models.py` (modelos principais + OMOP base)
- `test_auth.py` (auth user, sessão->JWT, compat `/users/`)
- `test_images.py` (upload de imagem)

Resultado validado durante desenvolvimento: suíte passando integralmente.

---

## 12. Fluxo de Execução em Desenvolvimento

## 12.1 Variáveis essenciais

- `DB_NAME`
- `DB_USER`
- `DB_PASSWORD`
- `DB_HOST`
- `DB_PORT`
- `SECRET_KEY`

## 12.2 Sequência padrão

1. subir PostgreSQL
2. ativar venv
3. instalar dependências
4. executar migrations
5. iniciar `runserver`

---

## 13. Decisões de Compatibilidade com o Frontend

Para reduzir risco e acelerar entrega:

1. **Mantido endpoint legado `/user/me/`**
2. **Criado endpoint legado `/users/`**
3. **Adicionado payload esperado pelo frontend** (`role`, `is_allowed`, campos de perfil)
4. **Mantido fluxo de sessão com suporte adicional a JWT**
5. **Mapeamento dos endpoints clínicos legados para entidades OMOP**

Com isso, o frontend consegue operar sem grande refatoração imediata.

---

## 14. Estado Atual e Próximos Passos

## 14.1 Estado atual

- Backend Django funcional
- Integração com PostgreSQL operacional
- Persistência clínica baseada em OMOP
- Rotas compatíveis com frontend legado mantidas por mapeamento
- Testes cobrindo cenários críticos

## 14.2 Próximos passos recomendados

1. Endurecer segurança para produção (DEBUG=False, SECRET_KEY externa, cookies seguros)
2. Revisar CORS para domínios oficiais de deploy
3. Evoluir ETL e vocabulário OMOP completo
4. Integrar armazenamento de arquivos em serviço externo
5. Adicionar observabilidade (logs estruturados, métricas, tracing)
6. Configurar CI para testes automáticos

---

## 15. Conclusão

A migração para Django foi estruturada para equilibrar:

- **continuidade de operação** (compatibilidade de endpoints)
- **base sólida de evolução** (modelagem OMOP + DRF)
- **manutenibilidade** (migrations, testes, separação por camadas)

O backend está pronto para uso em desenvolvimento e preparado para evolução incremental rumo a um ambiente de produção robusto.
