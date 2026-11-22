# BioRegistro API

Back-end em Python para registrar observações de campo sobre a sociobiodiversidade (espécie, uso tradicional, foto e coordenadas) e submetê-las à validação de um especialista. A API foi pensada para um aplicativo móvel que funciona offline e sincroniza quando houver conexão.

## Stack

- Python 3.12, FastAPI e Pydantic
- SQLAlchemy 2 e Alembic
- PostgreSQL em produção, SQLite em desenvolvimento
- pytest

## Como rodar

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
alembic upgrade head
uvicorn app.main:app --reload
```

No Windows, ative o ambiente com `.venv\Scripts\activate`.

A documentação interativa fica em `http://localhost:8000/docs` e `http://localhost:8000/redoc`.

Para usar PostgreSQL, copie `.env.example` para `.env` e ajuste `DATABASE_URL`, por exemplo `postgresql+psycopg://usuario:senha@localhost:5432/bioregistro`. Em produção, troque também a `SECRET_KEY`.

## Primeiro acesso

Só administradores cadastram usuários, então o primeiro admin é criado pelo terminal:

```bash
python -m app.criar_admin --nome "Coordenação" --email admin@exemplo.com
```

A senha é pedida em seguida (mínimo de 8 caracteres). Depois disso, os demais usuários são cadastrados pela API.

## Autenticação

O login devolve um token JWT válido por 60 minutos, que vai no cabeçalho `Authorization: Bearer <token>`. A rota segue o formulário OAuth2, com o e-mail no campo `username`:

```bash
curl -X POST http://localhost:8000/auth/login \
  -d "username=admin@exemplo.com&password=sua-senha"
```

```json
{"access_token": "eyJhbGciOi...", "token_type": "bearer", "expires_in": 3600}
```

No `/docs`, o botão **Authorize** faz o login direto pela página.

Cadastro de um validador:

```bash
curl -X POST http://localhost:8000/usuarios \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"nome": "Beto", "email": "beto@exemplo.com", "senha": "senha-forte-123", "papel": "validador"}'
```

Cadastro de uma espécie:

```bash
curl -X POST http://localhost:8000/especies \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"nome_popular": "Açaí", "nome_cientifico": "Euterpe oleracea", "familia": "Arecaceae"}'
```

## Endpoints

| Método | Rota | Descrição | Acesso |
| --- | --- | --- | --- |
| POST | /auth/login | Gera token JWT | Público |
| POST | /usuarios | Cadastra usuário | Admin |
| GET | /especies | Lista espécies | Público |
| POST | /especies | Cadastra espécie | Admin |
| PUT | /especies/{id} | Edita espécie | Admin |

As respostas de erro seguem o formato `{"detail": "..."}`: 401 sem token ou com token inválido, 403 quando o papel não tem permissão, 404 para recurso inexistente, 409 para e-mail ou nome científico repetido e 422 para dados inválidos.

## Testes

```bash
pytest
```

## Estrutura

```
app/
  main.py
  criar_admin.py criação do primeiro administrador
  core/          configuração, banco, senhas e JWT
  models/        tabelas
  schemas/       entrada e saída da API
  repositories/  consultas ao banco
  services/      regras de negócio
  routers/       rotas HTTP
alembic/         migrações
tests/
```

## Modelo de dados

| Tabela | Conteúdo |
| --- | --- |
| usuarios | nome, e-mail, hash da senha e papel (coletor, validador ou admin) |
| especies | nome popular, nome científico e família |
| registros | observação de campo com UUID gerado no aparelho, coordenadas WGS 84, status e exclusão lógica |
| validacoes | decisão do validador (aprovado ou rejeitado) e comentário |
