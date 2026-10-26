"""Fetch and parse the Big Sky mountain report feed.

xmltodict returns a dict for a single child element and a list for several,
and missing elements come back as None. Everything below goes through
as_list() and the to_* helpers so a sparse or off-season feed parses
without KeyError or ValueError.
"""
from __future__ import annotations

import asyncio
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
import re
from typing import Any
from xml.parsers.expat import ExpatError

import aiohttp
import xmltodict

from homeassistant.util import dt as dt_util

from .const import FETCH_TIMEOUT, MAX_FEED_BYTES, RESORT_TIME_ZONE


class FeedError(Exception):
    """The feed could not be fetched or parsed."""


class FeedTooLarge(FeedError):
    """The response was larger than MAX_FEED_BYTES."""


@dataclass
class Lift:
    key: str
    name: str
    area: str | None
    type: str | None
    status: str | None
    capacity: str | None
    open_time: str | None
    close_time: str | None
    status_detail: str | None
    skier_wait_time: str | None
    scenic_wait_time: str | None


@dataclass
class Trail:
    key: str
    name: str
    area: str | None
    difficulty: str | None
    status: str | None
    groomed: str | None


@dataclass
class Park:
    name: str
    area: str | None
    status: str | None
    difficulty: str | None
    groomed: str | None


@dataclass
class ParkingLot:
    name: str
    status: str | None
    percent_full: str | None
    open_time: str | None
    closed_time: str | None
    alert: str | None


@dataclass
class ForecastDay:
    name: str | None
    high: float | None
    low: float | None
    weather: str | None
    text: str | None


@dataclass
class ResortData:
    updated: datetime | None = None
    resort_status: str | None = None
    open_time: str | None = None
    close_time: str | None = None
    trails_open: int | None = None
    lifts_open: int | None = None
    parks_open: int | None = None
    trails_snowmaking: int | None = None
    snow_base: float | None = None
    snow_overnight: float | None = None
    snow_24h: float | None = None
    snow_48h: float | None = None
    snow_72h: float | None = None
    snow_7d: float | None = None
    forecast: list[ForecastDay] = field(default_factory=list)
    lifts: dict[str, Lift] = field(default_factory=dict)
    trails: dict[str, Trail] = field(default_factory=dict)
    parks: list[Park] = field(default_factory=list)
    parking: list[ParkingLot] = field(default_factory=list)
    shuttle: dict[str, str | None] | None = None


def as_list(value: Any) -> list[dict[str, Any]]:
    """Return value as a list of dicts, whatever shape xmltodict produced."""
    if value is None:
        return []
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    if isinstance(value, dict):
        return [value]
    return []


def child(node: Any, *path: str) -> Any:
    """Walk nested dict keys, returning None at the first missing step."""
    for key in path:
        if not isinstance(node, dict):
            return None
        node = node.get(key)
    return node


def to_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def to_int(value: Any) -> int | None:
    number = to_float(value)
    return None if number is None else int(number)


def slugify_name(name: str) -> str:
    """Match the pre-1.1 unique_id slug: lower case, spaces to underscores."""
    return name.lower().replace(" ", "_")


def _clean_key(value: str) -> str:
    return re.sub(r"[^a-z0-9_]+", "_", value.lower()).strip("_")


def _assign_keys(items: list[dict[str, Any]]) -> list[str]:
    """Pick a stable key per item: the feed id, else the name.

    The feed reuses some ids (two trails share 11711 in October 2026),
    so a colliding id gets the name appended.
    """
    ids = Counter(item.get("@id") for item in items if item.get("@id"))
    keys = []
    for item in items:
        feed_id = item.get("@id")
        name = item.get("@name") or ""
        if feed_id and ids[feed_id] == 1:
            keys.append(_clean_key(str(feed_id)))
        elif feed_id:
            keys.append(_clean_key(f"{feed_id}_{name}"))
        else:
            keys.append(_clean_key(name))
    return keys


def _parse_updated(report: dict[str, Any]) -> datetime | None:
    if (epoch := to_float(report.get("@updated"))) is not None:
        return dt_util.utc_from_timestamp(epoch)
    if raw := report.get("@timestamp"):
        try:
            naive = datetime.strptime(raw, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return None
        return naive.replace(tzinfo=dt_util.get_time_zone(RESORT_TIME_ZONE))
    return None


def parse_feed(raw: dict[str, Any]) -> ResortData:
    """Turn the xmltodict output into ResortData."""
    report = child(raw, "report")
    if not isinstance(report, dict):
        raise FeedError("Feed has no <report> element")

    data = ResortData(updated=_parse_updated(report))

    operations = child(report, "operations") or {}
    data.resort_status = operations.get("@resortStatus")
    data.open_time = operations.get("@openTime")
    data.close_time = operations.get("@closeTime")

    resortwide = child(report, "currentConditions", "resortwide") or {}
    data.trails_open = to_int(resortwide.get("@numTrailsOpen"))
    data.lifts_open = to_int(resortwide.get("@numLiftsOpen"))
    data.parks_open = to_int(resortwide.get("@numParksOpen"))
    data.trails_snowmaking = to_int(resortwide.get("@numTrailsSnowMaking"))

    locations = as_list(child(report, "currentConditions", "resortLocations", "location"))
    if locations:
        location = locations[0]
        data.snow_base = to_float(location.get("@base"))
        data.snow_overnight = to_float(location.get("@snowOverNight"))
        data.snow_24h = to_float(location.get("@snow24Hours"))
        data.snow_48h = to_float(location.get("@snow48Hours"))
        data.snow_72h = to_float(location.get("@snow72Hours"))
        data.snow_7d = to_float(location.get("@snow7Days"))

    for day in as_list(child(report, "forecast", "day")):
        data.forecast.append(
            ForecastDay(
                name=day.get("@name"),
                high=to_float(day.get("@high")),
                low=to_float(day.get("@low")),
                weather=day.get("@weather"),
                text=day.get("#text"),
            )
        )

    lifts: list[tuple[str | None, dict[str, Any]]] = []
    trails: list[tuple[str | None, dict[str, Any]]] = []
    for area in as_list(child(report, "facilities", "areas", "area")):
        area_name = area.get("@name")
        lifts.extend((area_name, lift) for lift in as_list(child(area, "lifts", "lift")))
        trails.extend(
            (area_name, trail) for trail in as_list(child(area, "trails", "trail"))
        )
        for park in as_list(child(area, "freestyleTerrain", "parks", "park")):
            if not park.get("@name"):
                continue
            data.parks.append(
                Park(
                    name=park["@name"],
                    area=area_name,
                    status=park.get("@status"),
                    difficulty=park.get("@difficulty"),
                    groomed=park.get("@groomedOrCut"),
                )
            )

    lifts = [(area, lift) for area, lift in lifts if lift.get("@name")]
    for key, (area_name, lift) in zip(_assign_keys([l for _, l in lifts]), lifts):
        data.lifts[key] = Lift(
            key=key,
            name=lift["@name"],
            area=area_name,
            type=lift.get("@type"),
            status=lift.get("@status"),
            capacity=lift.get("@capacity"),
            open_time=lift.get("@openTime"),
            close_time=lift.get("@closeTime"),
            status_detail=lift.get("@statusDetail"),
            skier_wait_time=lift.get("@skierWaitTime"),
            scenic_wait_time=lift.get("@scenicWaitTime"),
        )

    trails = [(area, trail) for area, trail in trails if trail.get("@name")]
    for key, (area_name, trail) in zip(_assign_keys([t for _, t in trails]), trails):
        data.trails[key] = Trail(
            key=key,
            name=trail["@name"],
            area=area_name,
            difficulty=trail.get("@difficulty"),
            status=trail.get("@status"),
            groomed=trail.get("@groomed"),
        )

    for lot in as_list(child(report, "facilities", "parking", "lot")):
        if not lot.get("@name"):
            continue
        data.parking.append(
            ParkingLot(
                name=lot["@name"],
                status=lot.get("@status"),
                percent_full=lot.get("@percentFull"),
                open_time=lot.get("@openTime"),
                closed_time=lot.get("@closedTime"),
                alert=lot.get("@alert"),
            )
        )

    shuttles = as_list(child(report, "facilities", "shuttles", "line"))
    if shuttles:
        line = shuttles[0]
        data.shuttle = {
            "name": line.get("@name"),
            "status": line.get("@status"),
            "number_running": line.get("@numberRunning"),
            "open_time": line.get("@openTime"),
            "closed_time": line.get("@closedTime"),
            "comment": (line.get("@comment") or "").strip() or None,
            "alert": line.get("@alert"),
        }

    return data


def is_open(status: str | None) -> bool:
    return (status or "").strip().lower() == "open"


async def fetch_feed(session: aiohttp.ClientSession, url: str) -> ResortData:
    """Download and parse the feed. Raises FeedError on any failure."""
    try:
        async with asyncio.timeout(FETCH_TIMEOUT):
            async with session.get(url) as response:
                if response.status != 200:
                    raise FeedError(f"Feed returned HTTP {response.status}")
                declared = to_int(response.headers.get(aiohttp.hdrs.CONTENT_LENGTH))
                if declared is not None and declared > MAX_FEED_BYTES:
                    raise FeedTooLarge(f"Feed is {declared} bytes, limit {MAX_FEED_BYTES}")
                body = bytearray()
                async for chunk in response.content.iter_chunked(65536):
                    body.extend(chunk)
                    if len(body) > MAX_FEED_BYTES:
                        raise FeedTooLarge(f"Feed exceeds {MAX_FEED_BYTES} bytes")
    except TimeoutError as err:
        raise FeedError(f"Timed out after {FETCH_TIMEOUT}s fetching feed") from err
    except aiohttp.ClientError as err:
        raise FeedError(f"Error fetching feed: {err}") from err

    try:
        raw = xmltodict.parse(bytes(body))
    except ExpatError as err:
        raise FeedError(f"Feed is not valid XML: {err}") from err
    return parse_feed(raw)
