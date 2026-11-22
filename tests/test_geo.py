import math

import pytest

from app.core.geo import RAIO_TERRA_KM, caixa_envolvente, distancia_km

KM_POR_GRAU = math.pi * RAIO_TERRA_KM / 180


def test_mesmo_ponto_tem_distancia_zero():
    assert distancia_km(-1.45, -48.5, -1.45, -48.5) == 0


def test_um_grau_de_latitude():
    assert distancia_km(0, 0, 1, 0) == pytest.approx(KM_POR_GRAU)


def test_um_grau_de_longitude_no_equador():
    assert distancia_km(0, 0, 0, 1) == pytest.approx(KM_POR_GRAU)


def test_distancia_e_simetrica():
    assert distancia_km(-1.455833, -48.503889, -3.119028, -60.021731) == pytest.approx(
        distancia_km(-3.119028, -60.021731, -1.455833, -48.503889)
    )


def test_belem_manaus():
    assert distancia_km(-1.455833, -48.503889, -3.119028, -60.021731) == pytest.approx(1294, abs=5)


def test_distancia_atravessando_o_antimeridiano():
    assert distancia_km(0, 179.9, 0, -179.9) == pytest.approx(0.2 * KM_POR_GRAU)


def test_pontos_antipodas():
    assert distancia_km(0, 0, 0, 180) == pytest.approx(math.pi * RAIO_TERRA_KM)


def test_caixa_comum():
    caixa = caixa_envolvente(-1.45, -48.5, 10)
    assert caixa.lat_min < -1.45 < caixa.lat_max
    assert caixa.lon_min < -48.5 < caixa.lon_max
    assert not caixa.cruza_antimeridiano
    assert caixa.lat_max - caixa.lat_min == pytest.approx(2 * 10 / KM_POR_GRAU, rel=1e-3)


def test_caixa_alarga_a_longitude_longe_do_equador():
    no_equador = caixa_envolvente(0, 0, 100)
    ao_sul = caixa_envolvente(-60, 0, 100)
    assert ao_sul.lon_max - ao_sul.lon_min > no_equador.lon_max - no_equador.lon_min


def test_caixa_que_cruza_o_antimeridiano():
    caixa = caixa_envolvente(0, 179.95, 20)
    assert caixa.cruza_antimeridiano
    assert caixa.lon_min > 179
    assert caixa.lon_max < -179


def test_caixa_que_alcanca_o_polo_cobre_todas_as_longitudes():
    caixa = caixa_envolvente(89.9, 0, 50)
    assert caixa.lat_max == 90
    assert (caixa.lon_min, caixa.lon_max) == (-180, 180)


@pytest.mark.parametrize(
    "lat,lon,raio",
    [(-1.45, -48.5, 25), (45, 170, 800), (-70, -179, 300), (10, 0, 2000)],
)
def test_pontos_dentro_do_raio_ficam_dentro_da_caixa(lat, lon, raio):
    caixa = caixa_envolvente(lat, lon, raio)
    for rumo in range(0, 360, 5):
        angulo = raio / RAIO_TERRA_KM
        fi1, lambda1, theta = math.radians(lat), math.radians(lon), math.radians(rumo)
        fi2 = math.asin(
            math.sin(fi1) * math.cos(angulo) + math.cos(fi1) * math.sin(angulo) * math.cos(theta)
        )
        lambda2 = lambda1 + math.atan2(
            math.sin(theta) * math.sin(angulo) * math.cos(fi1),
            math.cos(angulo) - math.sin(fi1) * math.sin(fi2),
        )
        lat2 = math.degrees(fi2)
        lon2 = (math.degrees(lambda2) + 540) % 360 - 180
        assert distancia_km(lat, lon, lat2, lon2) == pytest.approx(raio)
        assert caixa.lat_min <= lat2 <= caixa.lat_max
        if caixa.cruza_antimeridiano:
            assert lon2 >= caixa.lon_min or lon2 <= caixa.lon_max
        else:
            assert caixa.lon_min <= lon2 <= caixa.lon_max
