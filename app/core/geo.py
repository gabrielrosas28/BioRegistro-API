import math
from dataclasses import dataclass

RAIO_TERRA_KM = 6371.0088
MARGEM_GRAUS = 1e-6


def distancia_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    fi1, fi2 = math.radians(lat1), math.radians(lat2)
    delta_fi = fi2 - fi1
    delta_lambda = math.radians(lon2 - lon1)
    a = (
        math.sin(delta_fi / 2) ** 2
        + math.cos(fi1) * math.cos(fi2) * math.sin(delta_lambda / 2) ** 2
    )
    return 2 * RAIO_TERRA_KM * math.asin(min(1.0, math.sqrt(a)))


@dataclass(frozen=True)
class Caixa:
    lat_min: float
    lat_max: float
    lon_min: float
    lon_max: float

    @property
    def cruza_antimeridiano(self) -> bool:
        return self.lon_min > self.lon_max


def caixa_envolvente(lat: float, lon: float, raio_km: float) -> Caixa:
    angulo = math.degrees(raio_km / RAIO_TERRA_KM) + MARGEM_GRAUS
    lat_min, lat_max = lat - angulo, lat + angulo
    if lat_min <= -90 or lat_max >= 90:
        return Caixa(max(lat_min, -90.0), min(lat_max, 90.0), -180.0, 180.0)
    delta = math.degrees(math.asin(math.sin(math.radians(angulo)) / math.cos(math.radians(lat))))
    lon_min, lon_max = lon - delta, lon + delta
    if lon_min < -180:
        lon_min += 360
    if lon_max > 180:
        lon_max -= 360
    return Caixa(lat_min, lat_max, lon_min, lon_max)
