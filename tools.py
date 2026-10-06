"""External-data and analysis tools for the Formula 1 briefing agent."""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime
from functools import lru_cache
import html
import json
import math
import re
from typing import Any
import xml.etree.ElementTree as ET

import requests


JOLPICA_BASE_URL = "https://api.jolpi.ca/ergast/f1"
MOTORSPORT_RSS_URL = "https://www.motorsport.com/rss/f1/news/"
REQUEST_HEADERS = {"User-Agent": "Formula One Chatbot (Course Project)"}
REQUEST_TIMEOUT_SECONDS = 12
DRIVER_RACE_MAX_POINTS = 25
DRIVER_SPRINT_MAX_POINTS = 8
CONSTRUCTOR_RACE_MAX_POINTS = 43  # First and Second in a Grand Prix: 25 + 18.
CONSTRUCTOR_SPRINT_MAX_POINTS = 15  # First and Second in a Sprint: 8 + 7.


def _json_response(url: str, *, params: dict[str, Any] | None = None) -> dict[str, Any]:
    """Return service errors as JSON the model can reason about."""
    try:
        response = requests.get(url, params=params, headers=REQUEST_HEADERS, timeout=REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()
        payload = response.json()
    except requests.Timeout:
        return {"error": "The data service timed out. Try again in a moment."}
    except requests.RequestException as exc:
        return {"error": f"The data service could not be reached: {exc}"}
    except ValueError:
        return {"error": "The data service returned invalid JSON."}
    return payload if isinstance(payload, dict) else {"error": "The data service returned an unexpected response."}

# Get recent, source-linked F1 news related to a driver, team, or topic.
def _rss_child_text(item: ET.Element, local_name: str) -> str:
    """Read an RSS child while tolerating namespace-qualified XML tags."""
    for child in item:
        if child.tag.rsplit("}", 1)[-1] == local_name:
            return (child.text or "").strip()
    return ""


def _rss_items() -> list[ET.Element] | dict[str, str]:
    """Fetch Motorsport.com's public F1 RSS feed without an API key."""
    try:
        response = requests.get(MOTORSPORT_RSS_URL, headers=REQUEST_HEADERS, timeout=REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()
        root = ET.fromstring(response.content)
    except requests.Timeout:
        return {"error": "The Motorsport.com news feed timed out. Try again in a moment."}
    except requests.RequestException as exc:
        return {"error": f"The Motorsport.com news feed could not be reached: {exc}"}
    except ET.ParseError:
        return {"error": "The Motorsport.com news feed returned invalid RSS."}
    return [element for element in root.iter() if element.tag.rsplit("}", 1)[-1] == "item"]


def _plain_text(value: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html.unescape(value))).strip()

#get the latest Motorsport.com F1 RSS headlines for a driver, team, or topic.
def get_f1_news(subject: str = "Formula 1", max_articles: int = 5) -> str:
    """Retrieve the current Motorsport.com F1 RSS headlines for a driver, team, or topic."""
    if not subject.strip():
        return json.dumps({"error": "Provide a driver, team, or F1 topic to search for."})
    max_articles = max(1, min(int(max_articles), 10))
    feed_items = _rss_items()
    if isinstance(feed_items, dict):
        return json.dumps(feed_items)

    ignored_terms = {"f1", "formula", "one", "news", "latest", "current", "recent"}
    subject_terms = [term for term in re.findall(r"[a-z0-9]+", subject.casefold()) if term not in ignored_terms]
    articles = []
    for item in feed_items:
        title = _plain_text(_rss_child_text(item, "title"))
        description = _plain_text(_rss_child_text(item, "description"))
        searchable = f"{title} {description}".casefold()
        if subject_terms and not all(term in searchable for term in subject_terms):
            continue
        articles.append(
            {
                "title": title,
                "published_at": _rss_child_text(item, "pubDate"),
                "source": "Motorsport.com",
                "url": _rss_child_text(item, "link"),
            }
        )
        if len(articles) == max_articles:
            break

    return json.dumps(
        {
            "subject": subject,
            "articles": articles,
            "source": "Motorsport.com Formula 1 RSS",
            "note": (
                "No matching articles were found in the current Motorsport.com F1 feed. "
                "This public RSS source does not support historical day-range searches."
                if not articles
                else "Results are drawn from the current Motorsport.com F1 RSS feed."
            ),
        }
    )

@lru_cache(maxsize=256)
def _jolpica(path: str) -> dict[str, Any]:
    return _json_response(f"{JOLPICA_BASE_URL}/{path.lstrip('/')}")

#get either driver standing or championship standing from jolpica API.
def _standings(championship: str, season: str) -> dict[str, Any]:
    if championship not in {"drivers", "constructors"}:
        return {"error": "championship must be either 'drivers' or 'constructors'."}
    endpoint = "driverstandings" if championship == "drivers" else "constructorstandings"
    payload = _jolpica(f"{season}/{endpoint}.json")
    if "error" in payload:
        return payload
    try:
        table = payload["MRData"]["StandingsTable"]
        standings_list = table["StandingsLists"][0]
        key = "DriverStandings" if championship == "drivers" else "ConstructorStandings"
        return {"season": table.get("season", season), "round": table.get("round"), "standings": standings_list[key]}
    except (KeyError, IndexError, TypeError):
        return {"error": f"No {championship} standings were available for {season}."}

#get driver name if looking for driver championship or get constructor team name if looking for constructor championship.
def _subject_name(entry: dict[str, Any], championship: str) -> str:
    if championship == "drivers":
        driver = entry["Driver"]
        return f"{driver.get('givenName', '')} {driver.get('familyName', '')}".strip()
    return entry["Constructor"].get("name", "Unknown team")

#get driver id if looking for driver championship or get constructor team id if looking for constructor championship.
def _subject_id(entry: dict[str, Any], championship: str) -> str:
    object_key = "Driver" if championship == "drivers" else "Constructor"
    id_key = "driverId" if championship == "drivers" else "constructorId"
    return entry[object_key].get(id_key, "")

def _find_subject(standings: list[dict[str, Any]], subject: str, championship: str) -> dict[str, Any] | None:
    needle = subject.casefold().strip()
    exact = [item for item in standings if needle in {_subject_name(item, championship).casefold(), _subject_id(item, championship).casefold()}]
    if exact:
        return exact[0]
    partial = [item for item in standings if needle in _subject_name(item, championship).casefold()]
    return partial[0] if len(partial) == 1 else None

#get championship standings for drivers or constructors.
def get_championship_standings(championship: str = "drivers", season: str = "current") -> str:
    """Get the current or selected-season Drivers' or Constructors' table."""
    data = _standings(championship, str(season))
    if "error" in data:
        return json.dumps(data)
    standings = [
        {
            "position": int(item.get("position", 0)),
            "subject": _subject_name(item, championship),
            "id": _subject_id(item, championship),
            "points": float(item.get("points", 0)),
            "wins": int(item.get("wins", 0)),
        }
        for item in data["standings"]
    ]
    return json.dumps({"championship": championship, "season": data["season"], "completed_round": data["round"], "standings": standings, "source": "Jolpica-F1"})

#used to analyze whether a driver or constructor remains eligible for a championship.
def _remaining_rounds(
    season: str, completed_round: int, championship: str
) -> tuple[list[dict[str, Any]], int]:
    """Use the standings' completed round, not the current date, to find events left."""
    payload = _jolpica(f"{season}/races.json?limit=100")
    if "error" in payload:
        return [], 0
    remaining = []
    for race in payload.get("MRData", {}).get("RaceTable", {}).get("Races", []):
        try:
            if int(race["round"]) > completed_round:
                remaining.append(race)
        except (KeyError, TypeError, ValueError):
            continue
    if championship == "drivers":
        race_maximum, sprint_maximum = DRIVER_RACE_MAX_POINTS, DRIVER_SPRINT_MAX_POINTS
    else:
        race_maximum, sprint_maximum = CONSTRUCTOR_RACE_MAX_POINTS, CONSTRUCTOR_SPRINT_MAX_POINTS
    maximum = sum(race_maximum + (sprint_maximum if race.get("Sprint") else 0) for race in remaining)
    return remaining, maximum

#calculate recent pace for a driver or constructor based on season and last five rounds.
def _recent_pace(
    championship: str,
    season: str,
    completed_round: int,
    subjects: list[dict[str, Any]],
) -> dict[str, dict[str, float | int | None]]:
    """Calculate season and latest-five-round average points from cumulative tables."""
    subject_ids = {_subject_id(item, championship) for item in subjects}
    current_points = {_subject_id(item, championship): float(item.get("points", 0)) for item in subjects}
    recent_rounds = min(5, completed_round)
    baseline_round = completed_round - recent_rounds
    baseline_points = {subject_id: 0.0 for subject_id in subject_ids}

    if baseline_round > 0:
        baseline = _standings(championship, f"{season}/{baseline_round}")
        if "error" not in baseline:
            for item in baseline["standings"]:
                subject_id = _subject_id(item, championship)
                if subject_id in baseline_points:
                    baseline_points[subject_id] = float(item.get("points", 0))

    return {
        subject_id: {
            "season_average_points_per_weekend": round(points / completed_round, 2) if completed_round else None,
            "recent_rounds_sample": recent_rounds,
            "recent_five_round_average_points_per_weekend": (
                round((points - baseline_points[subject_id]) / recent_rounds, 2) if recent_rounds else None
            ),
        }
        for subject_id, points in current_points.items()
    }


#analyze mathematical eligibility plus season-pace and recent-pace title scenarios.
def analyze_title_potential(subject: str, championship: str = "drivers", season: str = "current") -> str:
    """Show exact title eligibility plus season-pace and recent-pace scenarios."""
    data = _standings(championship, str(season))
    if "error" in data:
        return json.dumps(data)
    target = _find_subject(data["standings"], subject, championship)
    if target is None:
        choices = [_subject_name(item, championship) for item in data["standings"]]
        return json.dumps({"error": f"Could not identify '{subject}'. Try: {', '.join(choices)}."})
    completed_round = int(data.get("round") or 0)
    leader = data["standings"][0]
    target_points, leader_points = float(target.get("points", 0)), float(leader.get("points", 0))
    gap = max(0, leader_points - target_points)
    remaining, maximum_points = _remaining_rounds(str(data["season"]), completed_round, championship)
    rounds_left = len(remaining)
    target_id = _subject_id(target, championship)
    leader_id = _subject_id(leader, championship)
    pace = _recent_pace(championship, str(data["season"]), completed_round, [target, leader])
    target_maximum_final_points = target_points + maximum_points
    rivals_already_unreachable = [
        _subject_name(rival, championship)
        for rival in data["standings"]
        if _subject_id(rival, championship) != target_id
        and float(rival.get("points", 0)) > target_maximum_final_points
    ]
    tiebreak_dependent_rivals = [
        _subject_name(rival, championship)
        for rival in data["standings"]
        if _subject_id(rival, championship) != target_id
        and float(rival.get("points", 0)) == target_maximum_final_points
    ]
    points_gain_needed = math.floor(gap) + 1 if target_id != leader_id else 0
    gain_per_weekend = round(points_gain_needed / rounds_left, 2) if rounds_left else None
    maximum_average_points = round(maximum_points / rounds_left, 2) if rounds_left else None

    leader_season_average = pace[leader_id]["season_average_points_per_weekend"]
    leader_recent_average = pace[leader_id]["recent_five_round_average_points_per_weekend"]

    def pace_scenario(leader_average: float | int | None) -> dict[str, float | bool | None]:
        if rounds_left == 0 or target_id == leader_id or leader_average is None:
            return {"leader_average_points_per_weekend": leader_average, "target_required_average_points_per_weekend": None, "within_maximum_possible_pace": None}
        target_required = round((leader_points + float(leader_average) * rounds_left + 1 - target_points) / rounds_left, 2)
        return {
            "leader_average_points_per_weekend": leader_average,
            "target_required_average_points_per_weekend": target_required,
            "within_maximum_possible_pace": target_required <= maximum_average_points,
        }

    scenario_target_needed = {
        "if_leader_continues_season_average": pace_scenario(leader_season_average),
        "if_leader_continues_recent_five_round_average": pace_scenario(leader_recent_average),
    }
    return json.dumps(
        {
            "championship": championship,
            "season": data["season"],
            "subject": _subject_name(target, championship),
            "current_position": int(target.get("position", 0)),
            "current_points": target_points,
            "leader": _subject_name(leader, championship),
            "leader_points": leader_points,
            "points_gap_to_leader": gap,
            "completed_round": completed_round,
            "remaining_rounds": rounds_left,
            "remaining_events": [race.get("raceName") for race in remaining],
            "maximum_points_available": maximum_points,
            "maximum_average_points_per_remaining_weekend": maximum_average_points,
            "target_maximum_final_points": target_maximum_final_points,
            "mathematically_eligible": not rivals_already_unreachable,
            "rivals_already_unreachable": rivals_already_unreachable,
            "tiebreak_dependent_rivals": tiebreak_dependent_rivals,
            "points_gain_needed_over_leader": points_gain_needed,
            "required_average_gain_over_leader_per_remaining_weekend": gain_per_weekend,
            "target_current_pace": pace[target_id],
            "leader_current_pace": pace[leader_id],
            "target_points_needed_per_remaining_weekend": scenario_target_needed,
            "assumptions": [
                "This is a scenario analysis, not a win-probability forecast.",
                "Remaining events are determined from the completed round in the standings, not the calendar date.",
                "Driver maximums are 25 points per race and 8 per Sprint; Constructor maximums are 43 and 15 because both cars can score.",
                "A tie for maximum final points is marked as tie-break dependent rather than automatically eliminated.",
                "Season and recent-five averages include all championship points accumulated in those weekends, including Sprints.",
            ],
            "source": "Jolpica-F1 standings and schedule",
        }
    )

#analyze a driver's historically strongest circuits from results data, using wins, podiums, points, and average finishes.
def analyze_driver_track_history(driver: str, seasons_back: int = 8, limit: int = 5) -> str:
    """Rank a driver's historically strongest circuits from results data."""
    seasons_back = max(1, min(int(seasons_back), 12))
    limit = max(1, min(int(limit), 10))
    current_year = datetime.now(UTC).year
    by_circuit: dict[str, dict[str, Any]] = defaultdict(lambda: {"starts": 0, "wins": 0, "podiums": 0, "points": 0.0, "finishes": [], "countries": set()})
    resolved_name: str | None = None

    for year in range(current_year - seasons_back + 1, current_year + 1):
        payload = _jolpica(f"{year}/drivers/{driver.strip().lower()}/results.json?limit=100")
        if "error" in payload:
            continue
        for race in payload.get("MRData", {}).get("RaceTable", {}).get("Races", []):
            if not race.get("Results"):
                continue
            result, circuit = race["Results"][0], race.get("Circuit", {})
            resolved_name = resolved_name or f"{result.get('Driver', {}).get('givenName', '')} {result.get('Driver', {}).get('familyName', '')}".strip()
            stats = by_circuit[circuit.get("circuitName", "Unknown circuit")]
            stats["starts"] += 1
            stats["wins"] += int(result.get("position", "") == "1")
            position = result.get("position", "")
            if position.isdigit():
                numeric_position = int(position)
                stats["finishes"].append(numeric_position)
                stats["podiums"] += int(numeric_position <= 3)
            stats["points"] += float(result.get("points", 0))
            country = circuit.get("Location", {}).get("country")
            if country:
                stats["countries"].add(country)

    if not by_circuit:
        return json.dumps({"error": f"No results were found for '{driver}'. Use a Jolpica driver id such as 'hamilton', 'verstappen', or 'norris'."})
    ranking = []
    for circuit, stats in by_circuit.items():
        starts = stats["starts"]
        # A small-sample adjustment keeps one isolated win from looking like a sustained strength.
        score = round((stats["points"] / starts) + 6 * (stats["wins"] / starts) + 3 * (stats["podiums"] / starts), 2)
        ranking.append(
            {
                "circuit": circuit,
                "countries": sorted(stats["countries"]),
                "starts": starts,
                "wins": stats["wins"],
                "podiums": stats["podiums"],
                "points_per_start": round(stats["points"] / starts, 2),
                "average_classified_finish": round(sum(stats["finishes"]) / len(stats["finishes"]), 2) if stats["finishes"] else None,
                "strength_score": score,
            }
        )
    ranking.sort(key=lambda item: (item["strength_score"], item["wins"], item["podiums"]), reverse=True)
    return json.dumps(
        {
            "driver": resolved_name or driver,
            "seasons_included": list(range(current_year - seasons_back + 1, current_year + 1)),
            "ranking_method": "Points per start plus weighted win and podium rates.",
            "top_circuits": ranking[:limit],
            "source": "Jolpica-F1 historical race results",
        }
    )


TOOLS = [
    {"type": "function", "function": {"name": "get_f1_news", "description": "Get current, source-linked Formula 1 headlines from Motorsport.com's public RSS feed. Use for current news; the feed does not support historical date-range searches.", "parameters": {"type": "object", "properties": {"subject": {"type": "string", "description": "A driver, team, or topic, for example 'McLaren'."}, "max_articles": {"type": "integer", "description": "Articles to return, 1 to 10. Defaults to 5."}}, "required": ["subject"]}}},
    {"type": "function", "function": {"name": "get_championship_standings", "description": "Get current or selected-season Drivers' or Constructors' Championship standings. Use for current points or rank.", "parameters": {"type": "object", "properties": {"championship": {"type": "string", "enum": ["drivers", "constructors"], "description": "The championship table."}, "season": {"type": "string", "description": "A season year such as '2026', or 'current'. Defaults to current."}}, "required": ["championship"]}}},
    {"type": "function", "function": {"name": "analyze_title_potential", "description": "Analyze whether a driver or constructor remains in the running for the championship and show a transparent catch-up scenario. Not a betting or probability forecast.", "parameters": {"type": "object", "properties": {"subject": {"type": "string", "description": "Driver/team name or id, such as 'norris' or 'McLaren'."}, "championship": {"type": "string", "enum": ["drivers", "constructors"], "description": "The title to analyze."}, "season": {"type": "string", "description": "A season year such as '2026', or 'current'. Defaults to current."}}, "required": ["subject", "championship"]}}},
    {"type": "function", "function": {"name": "analyze_driver_track_history", "description": "Rank a driver's strongest historic F1 circuits using wins, podiums, points, and average finishes. Use for questions about track history or location strength.", "parameters": {"type": "object", "properties": {"driver": {"type": "string", "description": "Jolpica driver id, such as 'hamilton', 'verstappen', or 'norris'."}, "seasons_back": {"type": "integer", "description": "Recent seasons to analyze, 1 to 12. Defaults to 8."}, "limit": {"type": "integer", "description": "Circuits to return, 1 to 10. Defaults to 5."}}, "required": ["driver"]}}},
]

TOOL_MAP = {
    "get_f1_news": get_f1_news,
    "get_championship_standings": get_championship_standings,
    "analyze_title_potential": analyze_title_potential,
    "analyze_driver_track_history": analyze_driver_track_history,
}


def run_tool(name: str, args: dict[str, Any]) -> str:
    """Run a known tool without allowing malformed model calls to terminate the loop."""
    if name not in TOOL_MAP:
        return json.dumps({"error": f"Unknown tool '{name}'. Available tools: {sorted(TOOL_MAP)}"})
    try:
        return TOOL_MAP[name](**args)
    except (TypeError, ValueError) as exc:
        return json.dumps({"error": f"Invalid arguments for {name}: {exc}"})
    except Exception as exc:
        return json.dumps({"error": f"{name} failed unexpectedly: {type(exc).__name__}: {exc}"})
