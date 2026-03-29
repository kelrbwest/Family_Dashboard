"""
Family data loading and all calculation logic.
"""

import json
from datetime import date, datetime
from pathlib import Path

MILESTONE_AGES = [16, 18, 21, 25, 30, 40, 50, 60, 65, 70, 75, 80, 85, 90, 95, 100]

MILESTONE_LABELS = {
    16: "Sweet 16",
    18: "Legal adult",
    21: "Coming of age",
    25: "Quarter century",
    30: "Thirty!",
    40: "Forty!",
    50: "Half century",
    60: "Sixty!",
    65: "Retirement age",
    70: "Seventy!",
    75: "Diamond jubilee",
    80: "Eighty!",
    85: "Eighty-five!",
    90: "Ninety!",
    95: "Ninety-five!",
    100: "Centenarian",
}

GENERATION_LABELS = {
    1: "Grandparent Generation",
    2: "Parent Generation",
    3: "Young Generation",
}


def load_family_data() -> dict:
    path = Path(__file__).parent / "family.json"
    with open(path) as f:
        return json.load(f)


def get_all_members() -> list[dict]:
    data = load_family_data()
    members = []
    for family in data["families"]:
        for member in family["members"]:
            member = dict(member)
            member["family_line"] = family["family_line"]
            member["accent_color"] = family["accent_color"]
            members.append(member)
    return members


def get_members_by_family() -> list[dict]:
    """Return families with enriched member dicts."""
    data = load_family_data()
    result = []
    for family in data["families"]:
        enriched_members = []
        for member in family["members"]:
            m = dict(member)
            m["family_line"] = family["family_line"]
            m["accent_color"] = family["accent_color"]
            enriched_members.append(m)
        result.append({
            "family_line": family["family_line"],
            "accent_color": family["accent_color"],
            "members": enriched_members,
        })
    return result


def member_map() -> dict[str, dict]:
    """ID → member dict for fast lookup."""
    return {m["id"]: m for m in get_all_members()}


def age_in_year(birth_year: int, target_year: int) -> int:
    return target_year - birth_year


def current_age(member: dict) -> dict:
    """
    Returns {'age': int, 'exact': bool}.
    exact=True only when birth_month + birth_day are both set.
    """
    today = date.today()
    by = member["birth_year"]
    bm = member.get("birth_month")
    bd = member.get("birth_day")

    if bm and bd:
        had_birthday = (today.month, today.day) >= (bm, bd)
        age = today.year - by - (0 if had_birthday else 1)
        return {"age": age, "exact": True}
    else:
        return {"age": today.year - by, "exact": False}


def format_age(age_dict: dict) -> str:
    prefix = "" if age_dict["exact"] else "~"
    return f"{prefix}{age_dict['age']}"


def initials(name: str) -> str:
    parts = name.split()
    return "".join(p[0].upper() for p in parts if p)[:2]


# ── Birthday Reminders ────────────────────────────────────────────────────────

def upcoming_birthdays(members: list, days_ahead: int = 90) -> list[dict]:
    """Members with birth_month+birth_day whose birthday falls within days_ahead."""
    today = date.today()
    results = []
    for m in members:
        bm = m.get("birth_month")
        bd = m.get("birth_day")
        if not (bm and bd):
            continue
        # Find next birthday
        try:
            birthday_this_year = date(today.year, bm, bd)
        except ValueError:
            continue
        if birthday_this_year < today:
            try:
                next_bday = date(today.year + 1, bm, bd)
            except ValueError:
                continue
        else:
            next_bday = birthday_this_year

        delta = (next_bday - today).days
        if delta <= days_ahead:
            age_info = current_age(m)
            turning_age = age_info["age"] if birthday_this_year >= today else age_info["age"] + 1
            results.append({
                "member": m,
                "date": next_bday,
                "days_until": delta,
                "turning_age": turning_age,
                "is_milestone": turning_age in MILESTONE_AGES,
                "milestone_label": MILESTONE_LABELS.get(turning_age, ""),
            })
    results.sort(key=lambda x: x["days_until"])
    return results


def birthday_year_summary(members: list) -> list[dict]:
    """Members turning a milestone age THIS calendar year."""
    this_year = date.today().year
    results = []
    for m in members:
        age = this_year - m["birth_year"]
        if age in MILESTONE_AGES:
            results.append({
                "member": m,
                "turning_age": age,
                "milestone_label": MILESTONE_LABELS.get(age, ""),
            })
    results.sort(key=lambda x: x["turning_age"])
    return results


# ── Timeline Explorer ─────────────────────────────────────────────────────────

def timeline_for_year(year: int) -> list[dict]:
    """Returns families list with each member's age in the given year."""
    families = get_members_by_family()
    for family in families:
        for m in family["members"]:
            a = age_in_year(m["birth_year"], year)
            m["timeline_age"] = a
            m["not_born"] = a < 0
            m["born_this_year"] = a == 0
    return families


def relational_facts_for_year(members: list, year: int) -> list[str]:
    facts = []
    living = [m for m in members if age_in_year(m["birth_year"], year) >= 0]
    unborn = [m for m in members if age_in_year(m["birth_year"], year) < 0]
    born_this_year = [m for m in members if age_in_year(m["birth_year"], year) == 0]

    if not living:
        return [f"No family members had been born yet in {year}."]

    # Oldest living
    oldest = max(living, key=lambda m: age_in_year(m["birth_year"], year))
    oldest_age = age_in_year(oldest["birth_year"], year)
    facts.append(f"The oldest family member in {year} was {oldest['first_name']} at {oldest_age} years old.")

    # Youngest living
    if len(living) > 1:
        youngest = min(living, key=lambda m: age_in_year(m["birth_year"], year))
        youngest_age = age_in_year(youngest["birth_year"], year)
        if youngest != oldest:
            facts.append(f"The youngest was {youngest['first_name']}, who was {youngest_age} years old.")

    # Born this year
    for m in born_this_year:
        # Find parents
        mmap = member_map()
        parent_names = [mmap[pid]["first_name"] for pid in m.get("parent_ids", []) if pid in mmap]
        if parent_names:
            parents_str = " and ".join(parent_names)
            parent_ages = [age_in_year(mmap[pid]["birth_year"], year) for pid in m.get("parent_ids", []) if pid in mmap]
            if len(parent_ages) == 2:
                facts.append(
                    f"{m['first_name']} was born in {year} — {parents_str} were {parent_ages[0]} and {parent_ages[1]} years old."
                )
            elif len(parent_ages) == 1:
                facts.append(
                    f"{m['first_name']} was born in {year} — {parents_str} was {parent_ages[0]} years old."
                )
        else:
            facts.append(f"{m['first_name']} was born in {year}.")

    # Not yet born
    if unborn:
        if len(unborn) == 1:
            facts.append(f"{unborn[0]['first_name']} had not been born yet in {year}.")
        elif len(unborn) <= 4:
            names = ", ".join(m["first_name"] for m in unborn)
            facts.append(f"{names} had not been born yet in {year}.")
        else:
            facts.append(f"{len(unborn)} family members had not been born yet in {year}.")

    # Span
    if len(living) > 1:
        max_age = age_in_year(oldest["birth_year"], year)
        min_m = min(living, key=lambda m: age_in_year(m["birth_year"], year))
        min_age = age_in_year(min_m["birth_year"], year)
        span = max_age - min_age
        if span > 0:
            facts.append(f"The age span among living family members in {year} was {span} years.")

    return facts


# ── Future Milestones ─────────────────────────────────────────────────────────

def milestones_in_range(members: list, year_start: int, year_end: int, family_filter: str = None) -> list[dict]:
    results = []
    for m in members:
        if family_filter and m["family_line"] != family_filter:
            continue
        for year in range(year_start, year_end + 1):
            age = age_in_year(m["birth_year"], year)
            if age in MILESTONE_AGES:
                results.append({
                    "member": m,
                    "year": year,
                    "age": age,
                    "label": MILESTONE_LABELS.get(age, ""),
                })
    results.sort(key=lambda x: (x["year"], x["age"]))
    return results


# ── Relational Facts ──────────────────────────────────────────────────────────

def generate_all_facts(members: list) -> dict:
    mmap = {m["id"]: m for m in members}
    facts = {
        "superlatives": _facts_superlatives(members),
        "same_birth_year": _facts_same_birth_year(members),
        "age_gaps": _facts_age_gaps(members),
        "parent_child": _facts_parent_child(members, mmap),
        "generation_spans": _facts_generation_spans(members),
    }
    return facts


def _facts_superlatives(members: list) -> list[str]:
    today = date.today()
    sorted_by_birth = sorted(members, key=lambda m: m["birth_year"])
    oldest = sorted_by_birth[0]
    youngest = sorted_by_birth[-1]
    oldest_age = today.year - oldest["birth_year"]
    youngest_age = today.year - youngest["birth_year"]
    span = oldest_age - youngest_age

    return [
        f"The oldest family member is {oldest['name']} (born {oldest['birth_year']}, ~{oldest_age} years old).",
        f"The youngest family member is {youngest['name']} (born {youngest['birth_year']}, ~{youngest_age} years old).",
        f"There is a {span}-year span between the oldest and youngest family member.",
    ]


def _facts_same_birth_year(members: list) -> list[str]:
    by_year: dict[int, list] = {}
    for m in members:
        by_year.setdefault(m["birth_year"], []).append(m)
    facts = []
    for year, group in sorted(by_year.items()):
        if len(group) >= 2:
            names = " and ".join(m["first_name"] for m in group)
            facts.append(f"{names} were both born in {year}.")
    return facts


def _facts_age_gaps(members: list) -> list[str]:
    """Notable age gaps: cross-generation and within same family."""
    facts = []
    today = date.today()
    sorted_members = sorted(members, key=lambda m: m["birth_year"])

    # Overall largest gap pairs (top 5)
    pairs = []
    for i, a in enumerate(sorted_members):
        for b in sorted_members[i+1:]:
            gap = b["birth_year"] - a["birth_year"]
            if gap > 0 and a["family_line"] != b["family_line"]:
                pairs.append((gap, a, b))
    pairs.sort(reverse=True, key=lambda x: x[0])
    for gap, a, b in pairs[:4]:
        facts.append(f"{a['first_name']} is {gap} years older than {b['first_name']}.")

    # Same-family gaps (Gen 2 to Gen 3)
    from itertools import groupby
    by_family = {}
    for m in members:
        by_family.setdefault(m["family_line"], []).append(m)

    for family, fmembers in by_family.items():
        gen2 = [m for m in fmembers if m["generation"] == 2]
        gen3 = [m for m in fmembers if m["generation"] == 3]
        if gen2 and gen3:
            oldest_parent = min(gen2, key=lambda m: m["birth_year"])
            youngest_child = max(gen3, key=lambda m: m["birth_year"])
            gap = youngest_child["birth_year"] - oldest_parent["birth_year"]
            facts.append(
                f"In the {family} family, {oldest_parent['first_name']} and {youngest_child['first_name']} are {gap} years apart."
            )

    return facts


def _facts_parent_child(members: list, mmap: dict) -> list[str]:
    facts = []
    for m in members:
        for pid in m.get("parent_ids", []):
            parent = mmap.get(pid)
            if parent:
                parent_age = m["birth_year"] - parent["birth_year"]
                facts.append(
                    f"{parent['first_name']} was {parent_age} years old when {m['first_name']} was born."
                )
    # Deduplicate similar facts (e.g., both parents produce similar lines)
    seen = set()
    deduped = []
    for f in facts:
        if f not in seen:
            seen.add(f)
            deduped.append(f)
    return deduped


def _facts_generation_spans(members: list) -> list[str]:
    facts = []
    by_family = {}
    for m in members:
        by_family.setdefault(m["family_line"], []).append(m)

    for family, fmembers in by_family.items():
        if len(fmembers) < 2:
            continue
        oldest = min(fmembers, key=lambda m: m["birth_year"])
        youngest = max(fmembers, key=lambda m: m["birth_year"])
        span = youngest["birth_year"] - oldest["birth_year"]
        if span > 0:
            facts.append(
                f"The {family} family spans {span} years, from {oldest['first_name']} ({oldest['birth_year']}) to {youngest['first_name']} ({youngest['birth_year']})."
            )

    # Overall cross-family
    all_sorted = sorted(members, key=lambda m: m["birth_year"])
    overall_span = all_sorted[-1]["birth_year"] - all_sorted[0]["birth_year"]
    facts.append(
        f"Across all families, {all_sorted[0]['first_name']} ({all_sorted[0]['birth_year']}) and {all_sorted[-1]['first_name']} ({all_sorted[-1]['birth_year']}) are {overall_span} years apart."
    )

    return facts
