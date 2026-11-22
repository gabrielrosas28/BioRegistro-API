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

## Registros e validação

Todo registro novo entra como `pendente`. O `id` pode ser o UUID gerado no aparelho; se for omitido, o servidor gera um.

```bash
curl -X POST http://localhost:8000/registros \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"especie_id": 1, "descricao": "Touceira com cachos maduros", "uso_tradicional": "Fruto batido para o vinho", "latitude": -1.455833, "longitude": -48.503889, "data_coleta": "2026-11-20"}'
```

Um validador aprova ou rejeita. A rejeição exige comentário com no mínimo 10 caracteres:

```bash
curl -X POST http://localhost:8000/registros/$ID/validacao \
  -H "Authorization: Bearer $TOKEN_VALIDADOR" -H "Content-Type: application/json" \
  -d '{"decisao": "rejeitado", "comentario": "A foto não permite confirmar a espécie"}'
```

Listagem com filtros e paginação:

```bash
curl "http://localhost:8000/registros?status=validado&especie_id=1&data_inicio=2026-11-01&pagina=1&tamanho=20"
```

Regras aplicadas:

- latitude entre -90 e 90, longitude entre -180 e 180 e data da coleta que não seja futura;
- só o coletor que criou o registro edita ou exclui, e apenas enquanto estiver pendente;
- só validadores aprovam ou rejeitam, e ninguém valida o próprio registro;
- um registro rejeitado é reenviado como um novo registro;
- a exclusão é lógica (`deleted_at`), para a sincronização avisar o aplicativo;
- sem login só aparecem registros validados; o coletor vê os validados e os próprios; validadores e administradores veem todos.

## Busca por proximidade

`GET /registros/proximos` devolve os registros dentro de um raio em km, do mais próximo ao mais distante, com a distância calculada pela fórmula de Haversine:

```bash
curl "http://localhost:8000/registros/proximos?lat=-1.45&lon=-48.5&raio_km=20&limite=50"
```

Cada item traz os dados do registro e o campo `distancia_km`. Para não calcular a distância de todos os registros do banco, a consulta primeiro filtra por um retângulo de latitude e longitude em volta do ponto, com índice, e só aplica o Haversine aos candidatos. A busca considera os casos de borda, como raios que cruzam a linha de data (longitude ±180) ou chegam perto dos polos. A visibilidade é a mesma da listagem.

## Sincronização offline

O aplicativo guarda os registros no aparelho, cada um com um UUID gerado lá, e envia tudo em lote quando houver conexão:

```bash
curl -X POST http://localhost:8000/sync/registros   -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json"   -d '{"registros": [{"id": "6f1c2b9e-3d4a-4f5b-8c7d-9e0a1b2c3d4e", "especie_id": 1, "descricao": "Touceira com cachos maduros", "uso_tradicional": "Fruto batido para o vinho", "latitude": -1.455833, "longitude": -48.503889, "data_coleta": "2026-11-20"}]}'
```

```json
{"criados": ["6f1c2b9e-..."], "ignorados": [], "erros": []}
```

UUIDs que já existem no servidor vão para `ignorados`. Por isso, reenviar o mesmo lote, por exemplo depois de uma queda de conexão no meio do envio, não duplica nada. Um item com espécie inexistente volta em `erros` sem impedir o resto do lote. Cada envio aceita até 500 registros.

Depois, o aplicativo pede o que mudou desde a última sincronização:

```bash
curl -H "Authorization: Bearer $TOKEN"   "http://localhost:8000/sync/registros?desde=2026-11-22T18:00:00Z"
```

```json
{"alterados": [...], "excluidos": [{"id": "...", "excluido_em": "..."}], "sincronizado_em": "2026-11-22T19:00:58Z"}
```

`alterados` traz os registros criados, editados ou validados no período, com o histórico de validação. `excluidos` traz o que foi apagado, graças à exclusão lógica. O valor de `sincronizado_em` é a hora do servidor e deve ser enviado como `desde` na próxima chamada. Sem `desde`, a resposta traz tudo o que o usuário pode ver.

## Endpoints

| Método | Rota | Descrição | Acesso |
| --- | --- | --- | --- |
| POST | /auth/login | Gera token JWT | Público |
| POST | /usuarios | Cadastra usuário | Admin |
| GET | /especies | Lista espécies | Público |
| POST | /especies | Cadastra espécie | Admin |
| PUT | /especies/{id} | Edita espécie | Admin |
| POST | /registros | Cria registro | Autenticado |
| GET | /registros | Lista com filtros e paginação | Público |
| GET | /registros/{id} | Detalha registro com histórico de validação | Público |
| PUT | /registros/{id} | Edita registro pendente | Dono do registro |
| DELETE | /registros/{id} | Exclui registro pendente | Dono do registro |
| POST | /registros/{id}/validacao | Aprova ou rejeita | Validador |
| GET | /registros/proximos | Busca por raio | Público |
| POST | /sync/registros | Recebe lote offline | Autenticado |
| GET | /sync/registros?desde= | Devolve alterações e exclusões | Autenticado |

As respostas de erro seguem o formato `{"detail": "..."}`: 401 sem token ou com token inválido, 403 quando o papel não tem permissão, 404 para recurso inexistente ou fora da visibilidade do usuário, 409 para dado repetido ou registro que não está mais pendente e 422 para dados inválidos.

## Telas do Swagger

Visão geral das rotas:

![Visão geral do Swagger](docs/img/swagger-visao-geral.png)

Busca por raio a partir de Belém:

![Busca por raio](docs/img/swagger-busca-por-raio.png)

Mesmo lote enviado pela segunda vez: o registro é ignorado e nada é duplicado.

![Lote reenviado](docs/img/swagger-sync-lote-reenviado.png)

Sincronização incremental:

![Alterações desde a última sincronização](docs/img/swagger-sync-alteracoes.png)

## Desempenho

Medido com 10 mil registros num SQLite local, em mediana:

| Consulta | Tempo |
| --- | --- |
| Busca por raio de 50 km | 7 ms |
| Busca por raio de 5.000 km, com os 10 mil registros como candidatos | 17 ms |
| Mesma busca devolvendo 500 registros | 32 ms |
| Listagem com filtros e paginação | 7 ms |

## Testes

```bash
pytest
```

## Estrutura

```
app/
  main.py
  criar_admin.py criação do primeiro administrador
  core/          configuração, banco, senhas, JWT e cálculo de distância
  models/        tabelas
  schemas/       entrada e saída da API
  repositories/  consultas ao banco
  services/      regras de negócio
  routers/       rotas HTTP
alembic/         migrações
docs/img/        prints do Swagger
tests/
```

## Modelo de dados

| Tabela | Conteúdo |
| --- | --- |
| usuarios | nome, e-mail, hash da senha e papel (coletor, validador ou admin) |
| especies | nome popular, nome científico e família |
| registros | observação de campo com UUID gerado no aparelho, coordenadas WGS 84, status e exclusão lógica |
| validacoes | decisão do validador (aprovado ou rejeitado) e comentário |
