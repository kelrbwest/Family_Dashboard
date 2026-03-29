"""
Family Age Dashboard — Flask app.
Run: python app.py
Open: http://localhost:5000
"""

from datetime import date
from pathlib import Path

from flask import Flask, render_template, request, url_for

import family_data as fd

app = Flask(__name__)


def photo_url(member_id: str) -> str | None:
    """Return static URL if a photo file exists for this member, else None."""
    for ext in ["jpg", "jpeg", "png", "webp"]:
        p = Path(__file__).parent / "static" / "photos" / f"{member_id}.{ext}"
        if p.exists():
            return url_for("static", filename=f"photos/{member_id}.{ext}")
    return None


def enrich_with_photo(member: dict) -> dict:
    member = dict(member)
    member["photo_url"] = photo_url(member["id"])
    member["initials"] = fd.initials(member["name"])
    age_info = fd.current_age(member)
    member["current_age"] = age_info["age"]
    member["age_exact"] = age_info["exact"]
    member["age_display"] = fd.format_age(age_info)
    return member


@app.route("/")
def index():
    families = fd.get_members_by_family()
    for family in families:
        family["members"] = [enrich_with_photo(m) for m in family["members"]]
        # Group by generation
        by_gen = {}
        for m in family["members"]:
            by_gen.setdefault(m["generation"], []).append(m)
        family["by_generation"] = dict(sorted(by_gen.items()))

    all_members = fd.get_all_members()
    exact_count = sum(
        1 for m in all_members
        if m.get("birth_month") and m.get("birth_day")
    )
    approx_count = len(all_members) - exact_count

    return render_template(
        "index.html",
        families=families,
        exact_count=exact_count,
        approx_count=approx_count,
        today=date.today(),
    )


@app.route("/birthdays")
def birthdays():
    all_members = fd.get_all_members()
    upcoming = fd.upcoming_birthdays(all_members, days_ahead=90)
    for item in upcoming:
        item["member"] = enrich_with_photo(item["member"])

    milestones_this_year = fd.birthday_year_summary(all_members)
    for item in milestones_this_year:
        item["member"] = enrich_with_photo(item["member"])

    has_birth_dates = any(m.get("birth_month") and m.get("birth_day") for m in all_members)

    return render_template(
        "birthdays.html",
        upcoming=upcoming,
        milestones_this_year=milestones_this_year,
        has_birth_dates=has_birth_dates,
        this_year=date.today().year,
    )


@app.route("/timeline")
def timeline():
    try:
        year = int(request.args.get("year", date.today().year))
    except ValueError:
        year = date.today().year
    year = max(1952, min(2095, year))

    families = fd.timeline_for_year(year)
    for family in families:
        for m in family["members"]:
            m["photo_url"] = photo_url(m["id"])
            m["initials"] = fd.initials(m["name"])

    all_members = fd.get_all_members()
    facts = fd.relational_facts_for_year(all_members, year)

    return render_template(
        "timeline.html",
        families=families,
        year=year,
        facts=facts,
        min_year=1952,
        max_year=2095,
        current_year=date.today().year,
    )


@app.route("/milestones")
def milestones():
    all_members = fd.get_all_members()
    families_list = fd.get_members_by_family()
    family_names = [f["family_line"] for f in families_list]

    family_filter = request.args.get("family", "")
    years_ahead = int(request.args.get("years", 5))
    today = date.today()

    items = fd.milestones_in_range(
        all_members,
        today.year,
        today.year + years_ahead,
        family_filter=family_filter or None,
    )
    for item in items:
        item["member"] = enrich_with_photo(item["member"])

    return render_template(
        "milestones.html",
        items=items,
        family_names=family_names,
        family_filter=family_filter,
        years_ahead=years_ahead,
        this_year=today.year,
    )


@app.route("/facts")
def facts():
    all_members = fd.get_all_members()
    all_facts = fd.generate_all_facts(all_members)

    # Enrich members referenced in facts for photo display (done in template via member dicts)
    mmap = {m["id"]: enrich_with_photo(m) for m in all_members}

    return render_template(
        "facts.html",
        facts=all_facts,
        mmap=mmap,
    )


if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 8080))
    debug = os.environ.get("FLASK_ENV") != "production"
    print("\n  Family Age Dashboard")
    print(f"  Open http://localhost:{port} in your browser\n")
    print("  Press Ctrl+C to stop\n")
    app.run(debug=debug, host="0.0.0.0", port=port)
