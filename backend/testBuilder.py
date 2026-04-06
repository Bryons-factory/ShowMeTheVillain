from dataclasses import dataclass
from typing import TypedDict


def getThreatLevel(score: float) -> str:
    match score:
        case s if s <= 0:
            return "none"
        case s if s <= 2:
            return "low"
        case s if s <= 4:
            return "moderate"
        case s if s <= 6:
            return "elevated"
        case s if s <= 8:
            return "high"
        case s if s <= 10:
            return "critical"
        case _:
            return "unknown"


@dataclass
class location:
    def __init__(self):
        self.id: int
        self.url: str | None
        self.redirect_url: str
        self.ip: str
        self.countrycode: str
        self.countryname: str
        self.regioncode: str
        self.regionname: str
        self.city: str
        self.zipcode: str
        self.latitude: float
        self.longitude: float
        self.asn: str
        self.bgp: str
        self.isp: str
        self.title: str
        self.date: str
        self.date_update: str
        self.hash: str
        self.score: float
        self.host: str
        self.domain: str
        self.tld: str
        self.domain_registered_n_days_ago: int
        self.screenshot: str
        self.abuse_contact: str
        self.ssl_issuer: str
        self.ssl_subject: str
        self.rank_host: int
        self.rank_domain: int
        self.n_times_seen_ip: int
        self.n_times_seen_host: int
        self.n_times_seen_domain: int
        self.http_code: int
        self.http_server: str
        self.google_safebrowsing: str
        self.virus_total: str
        self.abuse_ch_malware: str
        self.vulns: str
        self.ports: str
        self.os: str
        self.tags: str
        self.technology: str
        self.page_text: str
        self.ssl_fingerprint: str
        self.inserted_at: str


class JsonItem(TypedDict):
    lat: float
    lon: float
    intensity: float
    name: str
    threat_level: str
    company: str
    country: str
    isp: str


def isNone(item: JsonItem) -> bool:
    return item["threat_level"] == "none"


def isLow(item: JsonItem) -> bool:
    return item["threat_level"] == "low"


def isModerate(item: JsonItem) -> bool:
    return item["threat_level"] == "moderate"


def isElevated(item: JsonItem) -> bool:
    return item["threat_level"] == "elevated"


def isHigh(item: JsonItem) -> bool:
    return item["threat_level"] == "high"


def isCritical(item: JsonItem) -> bool:
    return item["threat_level"] == "critical"


def isCountry(item: JsonItem, country: str) -> bool:
    return item["country"].lower() == country.lower()


def isIsp(item: JsonItem, isp: str) -> bool:
    return item["isp"].lower() == isp.lower()


def intensityAbove(item: JsonItem, threshold: float) -> bool:
    return item["intensity"] > threshold


def intensityBelow(item: JsonItem, threshold: float) -> bool:
    return item["intensity"] < threshold


class JsonBuilder:
    def __init__(self):
        self.objects: list[location]
        self.listSize: int
        self.items: list[JsonItem]

    def setObjects(self, objects: list[location]) -> None:
        self.objects = objects

    def addObjects(self, objects: list[location]) -> None:
        for object in objects:
            self.objects.append(object)

    def getList(self) -> list[JsonItem]:
        if self.objects is not None:
            if self.listSize == len(self.objects):
                return self.items
            else:
                for object in self.objects:
                    self.items.append(self.createDataPoint(object))

        return self.items

    def createDataPoint(self, location: location) -> JsonItem:
        return {
            "lat": location.latitude,
            "lon": location.longitude,
            "intensity": location.score,
            "name": location.host,
            "threat_level": getThreatLevel(location.score),
            "company": location.host,
            "country": location.countryname,
            "isp": location.isp,
        }

    def filterByThreatLevel(self, level: str) -> list[JsonItem]:
        match level.lower():
            case "none":
                return list(filter(isNone, self.items))
            case "low":
                return list(filter(isLow, self.items))
            case "moderate":
                return list(filter(isModerate, self.items))
            case "elevated":
                return list(filter(isElevated, self.items))
            case "high":
                return list(filter(isHigh, self.items))
            case "critical":
                return list(filter(isCritical, self.items))
            case _:
                return []

    def filterByCountry(self, country: str) -> list[JsonItem]:
        return list(filter(lambda item: isCountry(item, country), self.items))

    def filterByIsp(self, isp: str) -> list[JsonItem]:
        return list(filter(lambda item: isIsp(item, isp), self.items))

    def filterIntensityAbove(self, threshold: float) -> list[JsonItem]:
        return list(filter(lambda item: intensityAbove(item, threshold), self.items))

    def filterIntensityBelow(self, threshold: float) -> list[JsonItem]:
        return list(filter(lambda item: intensityBelow(item, threshold), self.items))
