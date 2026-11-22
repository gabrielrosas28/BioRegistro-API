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

Para usar PostgreSQL, copie `.env.example` para `.env` e ajuste `DATABASE_URL`, por exemplo `postgresql+psycopg://usuario:senha@localhost:5432/bioregistro`.

## Testes

```bash
pytest
```

## Estrutura

```
app/
  main.py
  core/          configuração e banco
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
