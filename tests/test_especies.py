import pytest

from tests.conftest import cabecalho

ACAI = {"nome_popular": "Açaí", "nome_cientifico": "Euterpe oleracea", "familia": "Arecaceae"}
ANDIROBA = {
    "nome_popular": "Andiroba",
    "nome_cientifico": "Carapa guianensis",
    "familia": "Meliaceae",
}


def cadastrar(cliente, admin, dados):
    return cliente.post("/especies", json=dados, headers=cabecalho(admin))


def test_admin_cadastra_especie(cliente, admin):
    resposta = cadastrar(cliente, admin, ACAI)
    assert resposta.status_code == 201
    corpo = resposta.json()
    assert isinstance(corpo["id"], int)
    assert {k: corpo[k] for k in ACAI} == ACAI


def test_familia_e_opcional(cliente, admin):
    resposta = cadastrar(
        cliente, admin, {"nome_popular": "Jambu", "nome_cientifico": "Acmella oleracea"}
    )
    assert resposta.status_code == 201
    assert resposta.json()["familia"] is None


def test_familia_em_branco_vira_nula(cliente, admin):
    resposta = cadastrar(cliente, admin, {**ACAI, "familia": "  "})
    assert resposta.json()["familia"] is None


def test_espacos_sao_removidos(cliente, admin):
    resposta = cadastrar(cliente, admin, {**ACAI, "nome_popular": "  Açaí  "})
    assert resposta.json()["nome_popular"] == "Açaí"


def test_listagem_e_publica_e_ordenada(cliente, admin):
    cadastrar(
        cliente, admin, {"nome_popular": "Copaíba", "nome_cientifico": "Copaifera reticulata"}
    )
    cadastrar(cliente, admin, ANDIROBA)
    resposta = cliente.get("/especies")
    assert resposta.status_code == 200
    assert [e["nome_popular"] for e in resposta.json()] == ["Andiroba", "Copaíba"]


def test_listagem_vazia(cliente):
    assert cliente.get("/especies").json() == []


def test_nome_cientifico_duplicado(cliente, admin):
    cadastrar(cliente, admin, ACAI)
    resposta = cadastrar(cliente, admin, {**ACAI, "nome_cientifico": "euterpe OLERACEA"})
    assert resposta.status_code == 409
    assert resposta.json() == {"detail": "Já existe uma espécie com este nome científico"}


@pytest.mark.parametrize(
    "campo,valor",
    [
        ("nome_popular", ""),
        ("nome_popular", None),
        ("nome_cientifico", "   "),
        ("nome_cientifico", "x" * 161),
        ("familia", "x" * 121),
    ],
)
def test_dados_invalidos(cliente, admin, campo, valor):
    resposta = cadastrar(cliente, admin, {**ACAI, campo: valor})
    assert resposta.status_code == 422
    assert resposta.json()["detail"][0]["loc"][:2] == ["body", campo]


def test_coletor_nao_cadastra_especie(cliente, coletor):
    assert cadastrar(cliente, coletor, ACAI).status_code == 403


def test_validador_nao_cadastra_especie(cliente, validador):
    assert cadastrar(cliente, validador, ACAI).status_code == 403


def test_admin_edita_especie(cliente, admin):
    especie_id = cadastrar(cliente, admin, ACAI).json()["id"]
    novos = {**ACAI, "nome_popular": "Açaí-do-pará", "familia": None}
    resposta = cliente.put(f"/especies/{especie_id}", json=novos, headers=cabecalho(admin))
    assert resposta.status_code == 200
    assert resposta.json() == {"id": especie_id, **novos}
    assert cliente.get("/especies").json() == [{"id": especie_id, **novos}]


def test_editar_mantendo_o_mesmo_nome_cientifico(cliente, admin):
    especie_id = cadastrar(cliente, admin, ACAI).json()["id"]
    resposta = cliente.put(
        f"/especies/{especie_id}",
        json={**ACAI, "nome_cientifico": "Euterpe Oleracea"},
        headers=cabecalho(admin),
    )
    assert resposta.status_code == 200


def test_editar_para_nome_cientifico_de_outra_especie(cliente, admin):
    cadastrar(cliente, admin, ACAI)
    andiroba_id = cadastrar(cliente, admin, ANDIROBA).json()["id"]
    resposta = cliente.put(f"/especies/{andiroba_id}", json=ACAI, headers=cabecalho(admin))
    assert resposta.status_code == 409


def test_editar_especie_inexistente(cliente, admin):
    resposta = cliente.put("/especies/999", json=ACAI, headers=cabecalho(admin))
    assert resposta.status_code == 404
    assert resposta.json() == {"detail": "Espécie não encontrada"}


def test_coletor_nao_edita_especie(cliente, admin, coletor):
    especie_id = cadastrar(cliente, admin, ACAI).json()["id"]
    resposta = cliente.put(f"/especies/{especie_id}", json=ANDIROBA, headers=cabecalho(coletor))
    assert resposta.status_code == 403
