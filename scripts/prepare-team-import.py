#!/usr/bin/env python3
import argparse
import hashlib
import json
import os
import re
import secrets
import string
import uuid
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "public" / "data.json"
NS = {
    "main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "rel": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "pkgrel": "http://schemas.openxmlformats.org/package/2006/relationships",
}

SKILL_ALIASES = {
    "mighty blow (+1)": "Mighty Blow",
    "mighty blow (+2)": "Mighty Blow",
    "mighty blow": "Mighty Blow",
    "thick skull": "Thick Skull",
    "on the ball": "On the Ball",
    "strip ball": "Strip Ball",
    "side step": "Sidestep",
    "sure feet": "Sure Feet",
    "sure hands": "Sure Hands",
    "diving tackle": "Diving Tackle",
    "unchannelled fury": "Unchanneled Fury",
    "throw team-mate": "Throw Team-Mate",
    "throw teammate": "Throw Team-Mate",
    "no hands": "No Ball",
    "bone-head": "Bonehead",
}

CODE_BY_CATEGORY = {
    "Agility": "A",
    "Devious": "D",
    "General": "G",
    "Mutation": "M",
    "Passing": "P",
    "Strength": "S",
}

LEAGUES = [
    "Badlands Brawl",
    "Chaos Clash",
    "Elven Kingdoms League",
    "Halfling Thimble Cup",
    "Lustrian Superleague",
    "Old World Classic",
    "Sylvanian Spotlight",
    "Underworld Challenge",
    "Woodland League",
    "Worlds Edge Superleague",
]


def normalize(value):
    return re.sub(r"\s+", " ", str(value or "").replace("’", "'")).strip().lower()


def login_key(value):
    return normalize(value)


def sql_literal(value):
    if value is None:
        return "NULL"
    return "'" + str(value).replace("'", "''") + "'"


def sql_json(value):
    return sql_literal(json.dumps(value, ensure_ascii=False, separators=(",", ":"))) + "::jsonb"


def hash_password(password):
    salt = secrets.token_hex(16)
    derived = hashlib.scrypt(password.encode("utf-8"), salt=salt.encode("utf-8"), n=16384, r=8, p=1, dklen=64)
    return f"scrypt:{salt}:{derived.hex()}"


def temporary_password():
    alphabet = string.ascii_lowercase + string.digits
    left = "".join(secrets.choice(alphabet) for _ in range(6))
    right = "".join(secrets.choice(alphabet) for _ in range(6))
    return f"gata-{left}-{right}"


def column_index(cell_ref):
    match = re.match(r"([A-Z]+)", cell_ref)
    if not match:
        return 0
    value = 0
    for char in match.group(1):
        value = value * 26 + (ord(char) - ord("A") + 1)
    return value - 1


def cell_text(cell, shared_strings):
    cell_type = cell.attrib.get("t", "")
    if cell_type == "inlineStr":
        return "".join(t.text or "" for t in cell.findall(".//main:t", NS))
    value_node = cell.find("main:v", NS)
    if value_node is None:
        return None
    raw = value_node.text or ""
    if cell_type == "s":
        return shared_strings[int(raw)] if raw else ""
    if cell_type == "b":
        return raw == "1"
    if cell_type in {"str", "e"}:
        return raw
    try:
        number = float(raw)
        return int(number) if number.is_integer() else number
    except ValueError:
        return raw


def read_shared_strings(archive):
    if "xl/sharedStrings.xml" not in archive.namelist():
        return []
    root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
    strings = []
    for item in root.findall("main:si", NS):
        strings.append("".join(t.text or "" for t in item.findall(".//main:t", NS)))
    return strings


def workbook_sheets(archive):
    workbook = ET.fromstring(archive.read("xl/workbook.xml"))
    rels = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
    targets = {
        rel.attrib["Id"]: rel.attrib["Target"]
        for rel in rels.findall("pkgrel:Relationship", NS)
    }
    sheets = {}
    for sheet in workbook.findall("main:sheets/main:sheet", NS):
        rel_id = sheet.attrib[f"{{{NS['rel']}}}id"]
        target = targets[rel_id].replace("\\", "/")
        if not target.startswith("xl/"):
            target = "xl/" + target.lstrip("/")
        sheets[sheet.attrib["name"]] = target
    return sheets


def read_sheet_matrix(xlsx_path, sheet_name):
    with zipfile.ZipFile(xlsx_path) as archive:
        shared_strings = read_shared_strings(archive)
        sheets = workbook_sheets(archive)
        if sheet_name not in sheets:
            available = ", ".join(sheets)
            raise SystemExit(f"Sheet not found: {sheet_name}. Available sheets: {available}")
        root = ET.fromstring(archive.read(sheets[sheet_name]))
        rows = []
        for row in root.findall("main:sheetData/main:row", NS):
            row_values = []
            for cell in row.findall("main:c", NS):
                index = column_index(cell.attrib.get("r", "A1"))
                while len(row_values) < index:
                    row_values.append(None)
                row_values.append(cell_text(cell, shared_strings))
            rows.append(row_values)
        return rows


def cell(row, index):
    return row[index] if index < len(row) else None


def to_number(value, default=0):
    if value in (None, ""):
        return default
    if isinstance(value, bool):
        return int(value)
    try:
        number = float(str(value).replace(",", "."))
        return int(number) if number.is_integer() else number
    except ValueError:
        return default


def to_bool(value):
    if isinstance(value, bool):
        return value
    return normalize(value) in {"1", "true", "yes", "y"}


def parse_cost(value):
    match = re.search(r"\d+", str(value or ""))
    return int(match.group(0)) if match else 0


def split_skills(value):
    return [
        re.sub(r",+$", "", part.strip())
        for part in re.sub(r"\s+", " ", str(value or "")).split(",")
        if part.strip()
    ]


def parse_advancements(value):
    result = []
    for part in normalize(value).split(","):
        if "random" in part:
            result.append({"type": "random"})
        elif "secondary" in part:
            result.append({"type": "secondary"})
        elif "primary" in part:
            result.append({"type": "primary"})
        elif "stat" in part or "characteristic" in part:
            result.append({"type": "stat"})
    return result[:6]


def parse_stat_mod(stat, base, current):
    if current in (None, ""):
        return 0
    base_match = re.match(r"^(\d+)", str(base or ""))
    current_match = re.match(r"^(\d+)", str(current or ""))
    if not base_match or not current_match:
        return 0
    base_number = int(base_match.group(1))
    current_number = int(current_match.group(1))
    if stat in {"ag", "pa"}:
        return base_number - current_number
    return current_number - base_number


def load_site_data():
    return json.loads(DATA_PATH.read_text(encoding="utf-8"))


def find_team(data, team_name):
    wanted = normalize(team_name)
    for team in data.get("teams", []):
        if normalize(team.get("title")) == wanted:
            return team
    for team in data.get("teams", []):
        slug_tail = str(team.get("slug", "")).split("/")[-1].replace("-", " ")
        if normalize(slug_tail) == wanted:
            return team
    raise SystemExit(f"Base team was not found in public/data.json: {team_name}")


def skill_canonical_map(data):
    mapping = {}
    for group in data.get("skillGroups", []):
        for name in group.get("skills", []):
            mapping[normalize(name)] = name
    for item in data.get("items", []):
        if item.get("kind") in {"skill", "trait"}:
            mapping[normalize(item.get("title"))] = item.get("title")
    mapping.update(SKILL_ALIASES)
    return mapping


def canonical_skill(name, mapping):
    clean = normalize(name)
    if clean in mapping:
        return mapping[clean]
    return " ".join(part[:1].upper() + part[1:] for part in str(name).strip().split())


def skill_access(row, skill_name, data):
    category = ""
    for group in data.get("skillGroups", []):
        if any(normalize(name) == normalize(skill_name) for name in group.get("skills", [])):
            category = group.get("category", "")
            break
    code = CODE_BY_CATEGORY.get(category)
    primary = " ".join(row.get("primary", [])).split()
    secondary = " ".join(row.get("secondary", [])).split()
    if code and code in secondary and code not in primary:
        return "secondary"
    return "primary"


def match_roster_row(rows, position, value):
    if position:
        wanted = normalize(position)
        for index, row in enumerate(rows):
            if normalize(row.get("position")) == wanted:
                return index
    cost = to_number(value, None)
    if cost:
        matches = [index for index, row in enumerate(rows) if parse_cost(row.get("price")) == cost]
        if len(matches) == 1:
            return matches[0]
    linemen = [index for index, row in enumerate(rows) if "lineman" in normalize(",".join(row.get("tags", [])))]
    if linemen:
        return linemen[0]
    raise SystemExit(f"Could not match player position: {position or '(blank)'}")


def first_league_option(team):
    source = str(team.get("team", {}).get("meta", {}).get("specialRules", ""))
    source_key = normalize(source)
    for league in LEAGUES:
        if normalize(league) in source_key:
            return league
    return ""


def player_rows(matrix):
    header_index = None
    for index, row in enumerate(matrix):
        if normalize(cell(row, 0)) == "#" and normalize(cell(row, 1)) == "player":
            header_index = index
            break
    if header_index is None:
        raise SystemExit("Could not find player table header.")
    headers = [normalize(value) for value in matrix[header_index]]
    rows = []
    for row in matrix[header_index + 1:]:
        first_cells = " ".join(normalize(value) for value in row[:4] if value not in (None, ""))
        if "book of the dead" in first_cells:
            break
        if normalize(cell(row, 0)) == "#" and normalize(cell(row, 1)) == "player":
            break
        if not any(value not in (None, "") for value in row[:9]):
            continue
        rows.append((headers, row))
    return rows


def header_index(headers, *needles):
    for needle in needles:
        for index, header in enumerate(headers):
            if needle in header:
                return index
    return -1


def sheet_value_by_header(matrix, header_name, value_row=2, header_row=1, default_index=-1):
    headers = [normalize(value) for value in matrix[header_row]] if header_row < len(matrix) else []
    index = header_index(headers, normalize(header_name))
    if index < 0:
        index = default_index
    return cell(matrix[value_row], index) if index >= 0 and value_row < len(matrix) else None


def build_roster(matrix, data, base_team_override=None, team_name_override=None):
    team_name = str(team_name_override or cell(matrix[0], 0) or "").strip()
    base_team_name = str(base_team_override or cell(matrix[1], 2) or "").strip()
    telegram = str(cell(matrix[2], 2) or "").strip()
    team = find_team(data, base_team_name)
    roster_rows = team["team"]["roster"]
    skill_names = skill_canonical_map(data)
    players = []

    for headers, row in player_rows(matrix):
        name = str(cell(row, 1) or "").strip()
        position = str(cell(row, 2) or "").strip()
        if not name and not position:
            continue
        row_index = match_roster_row(roster_rows, position, cell(row, header_index(headers, "value")))
        base = roster_rows[row_index]
        base_skills = {normalize(skill) for skill in base.get("skills", [])}
        raw_skills = split_skills(cell(row, 8))
        is_captain = any(normalize(skill) == "captain" for skill in raw_skills)
        extra_skills = []
        for raw_skill in raw_skills:
            if normalize(raw_skill) == "captain":
                continue
            skill_name = canonical_skill(raw_skill, skill_names)
            if normalize(skill_name) in base_skills:
                continue
            if is_captain and normalize(skill_name) == "pro":
                continue
            extra_skills.append({
                "name": skill_name,
                "access": skill_access(base, skill_name, data),
            })

        stat_mods = {}
        for stat, header_name, prop in [
            ("ma", "ma", "ma"),
            ("st", "st", "st"),
            ("ag", "ag", "ag"),
            ("pa", "pa", "pa"),
            ("ar", "av", "ar"),
        ]:
            index = header_index(headers, header_name)
            mod = parse_stat_mod(stat, base.get(prop), cell(row, index))
            if mod:
                stat_mods[stat] = mod

        def stat_value(*names):
            index = header_index(headers, *names)
            return to_number(cell(row, index)) if index >= 0 else 0

        players.append({
            "id": str(uuid.uuid4()),
            "rowIndex": row_index,
            "number": str(cell(row, 0) or len(players) + 1),
            "name": name or f"{base['position']} {len(players) + 1}",
            "statMods": stat_mods,
            "extraSkills": extra_skills,
            "favouredSkills": [],
            "skipNextGame": to_bool(cell(row, header_index(headers, "skip next"))),
            "niglingInjury": to_bool(cell(row, header_index(headers, "niggling"))),
            "isCaptain": is_captain,
            "extendedContracts": 0,
            "spp": {
                "touchdowns": stat_value("touchdown"),
                "casualties": stat_value("casualties"),
                "knockouts": stat_value("knock outs"),
                "completions": stat_value("completion"),
                "catches": 0,
                "interceptions": stat_value("interceptions"),
                "mvps": stat_value("mvp"),
            },
            "advancements": parse_advancements(cell(row, header_index(headers, "advanc"))),
            "purchased": False,
        })

    counts = {}
    for player in players:
        key = str(player["rowIndex"])
        counts[key] = counts.get(key, 0) + 1

    purchased_staff = {
        "teamRerolls": to_number(sheet_value_by_header(matrix, "Team Rerolls", default_index=6)),
        "startingRerolls": 0,
        "bribes": 0,
        "assistantCoaches": to_number(sheet_value_by_header(matrix, "Assistants", default_index=3)),
        "cheerleaders": to_number(sheet_value_by_header(matrix, "Cheerleaders", default_index=4)),
        "apothecary": to_number(sheet_value_by_header(matrix, "Apothecary", default_index=5)),
        "mortuaryAssistant": 0,
        "plagueDoctor": 0,
    }
    return {
        "team": team,
        "telegram": telegram,
        "teamName": team_name,
        "roster": {
            "editingTeamId": "",
            "teamSlug": team["slug"],
            "teamName": team_name,
            "selectedLeague": first_league_option(team),
            "favouredChoice": "",
            "logoData": "",
            "players": players,
            "roster": counts,
            "playerEdits": {},
            "teamRerolls": purchased_staff["teamRerolls"],
            "startingRerolls": 0,
            "bribes": 0,
            "dedicatedFans": to_number(sheet_value_by_header(matrix, "Fan Factor", default_index=10)),
            "assistantCoaches": purchased_staff["assistantCoaches"],
            "cheerleaders": purchased_staff["cheerleaders"],
            "apothecary": purchased_staff["apothecary"],
            "mortuaryAssistant": 0,
            "plagueDoctor": 0,
            "purchasedStaff": purchased_staff,
            "treasury": to_number(sheet_value_by_header(matrix, "Treasury", default_index=9)),
            "coachesSafe": 0,
        },
    }


def build_sql(login, telegram, password_hash, team_name, base_team_slug, roster):
    return f"""-- Generated by scripts/prepare-team-import.py.
-- Login: {login}
-- Temporary password is written to the credentials JSON next to this SQL file.

WITH upsert_user AS (
  INSERT INTO users (login, login_key, telegram, password_hash, is_admin)
  VALUES ({sql_literal(login)}, {sql_literal(login_key(login))}, {sql_literal(telegram)}, {sql_literal(password_hash)}, FALSE)
  ON CONFLICT (login_key) DO UPDATE
    SET telegram = EXCLUDED.telegram,
        password_hash = EXCLUDED.password_hash,
        updated_at = now()
  RETURNING id
),
existing_team AS (
  SELECT saved_teams.id
  FROM saved_teams
  JOIN upsert_user ON upsert_user.id = saved_teams.user_id
  WHERE saved_teams.name = {sql_literal(team_name)}
  ORDER BY saved_teams.updated_at DESC
  LIMIT 1
),
updated_team AS (
  UPDATE saved_teams
  SET base_team_slug = {sql_literal(base_team_slug)},
      logo_data = NULL,
      roster = {sql_json(roster)},
      updated_at = now()
  WHERE id IN (SELECT id FROM existing_team)
  RETURNING id
),
inserted_team AS (
  INSERT INTO saved_teams (user_id, name, base_team_slug, logo_data, roster)
  SELECT upsert_user.id, {sql_literal(team_name)}, {sql_literal(base_team_slug)}, NULL, {sql_json(roster)}
  FROM upsert_user
  WHERE NOT EXISTS (SELECT 1 FROM updated_team)
  RETURNING id
)
SELECT id AS saved_team_id FROM updated_team
UNION ALL
SELECT id AS saved_team_id FROM inserted_team;
"""


def main():
    parser = argparse.ArgumentParser(description="Prepare a cloud-importable SQL file from a Gata team XLSX sheet.")
    parser.add_argument("--xlsx", required=True, help="Path to the source .xlsx workbook.")
    parser.add_argument("--sheet", required=True, help="Sheet name with one team roster.")
    parser.add_argument("--login", help="Site login to create/update. Defaults to the Telegram handle without @.")
    parser.add_argument("--telegram", help="Telegram contact. Defaults to the sheet coach cell.")
    parser.add_argument("--password", help="Temporary password. Defaults to a generated password.")
    parser.add_argument("--base-team", help="Override the rules team name from the sheet.")
    parser.add_argument("--team-name", help="Override the saved team name from the sheet.")
    parser.add_argument("--sql-out", required=True, help="Where to write the generated SQL file.")
    parser.add_argument("--credentials-out", help="Where to write login/password JSON. Defaults next to SQL.")
    parser.add_argument("--import-out", help="Where to write the admin UI import JSON. Defaults next to SQL.")
    args = parser.parse_args()

    data = load_site_data()
    matrix = read_sheet_matrix(args.xlsx, args.sheet)
    parsed = build_roster(matrix, data, args.base_team, args.team_name)
    telegram = args.telegram or parsed["telegram"] or "@unknown"
    login = args.login or telegram.removeprefix("@") or parsed["teamName"].replace(" ", "-").lower()
    password = args.password or temporary_password()
    password_hash = hash_password(password)
    sql = build_sql(login, telegram, password_hash, parsed["teamName"], parsed["team"]["slug"], parsed["roster"])

    sql_path = Path(args.sql_out)
    sql_path.parent.mkdir(parents=True, exist_ok=True)
    sql_path.write_text(sql, encoding="utf-8")

    credentials_path = Path(args.credentials_out) if args.credentials_out else sql_path.with_suffix(".credentials.json")
    credentials_path.write_text(json.dumps({
        "login": login,
        "temporaryPassword": password,
        "telegram": telegram,
        "teamName": parsed["teamName"],
        "baseTeam": parsed["team"]["title"],
        "playersImported": len(parsed["roster"]["players"]),
        "sqlFile": str(sql_path),
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    import_path = Path(args.import_out) if args.import_out else sql_path.with_suffix(".team-import.json")
    import_path.write_text(json.dumps({
        "version": 1,
        "imports": [{
            "login": login,
            "telegram": telegram,
            "temporaryPassword": password,
            "teamName": parsed["teamName"],
            "baseTeamSlug": parsed["team"]["slug"],
            "roster": parsed["roster"],
        }],
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps({
        "sqlFile": str(sql_path),
        "credentialsFile": str(credentials_path),
        "importFile": str(import_path),
        "login": login,
        "temporaryPassword": password,
        "teamName": parsed["teamName"],
        "playersImported": len(parsed["roster"]["players"]),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
