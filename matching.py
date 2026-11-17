"""Pure, database-independent job matching helpers."""
import json


def parse_json(value, default=None):
    """Decode a MySQL JSON field whether returned as a string or Python value."""
    if value is None or value == "":
        return default
    if isinstance(value, (dict, list)):
        return value
    if isinstance(value, bytes):
        value = value.decode("utf-8")
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return default


def normalize_skills(skills):
    """Case-insensitively deduplicate comma-separated skills, retaining display text."""
    if isinstance(skills, str):
        skills = skills.split(",")
    result = []
    seen = set()
    for skill in skills or []:
        if not isinstance(skill, str):
            continue
        clean = " ".join(skill.strip().split())
        key = clean.casefold()
        if clean and key not in seen:
            seen.add(key)
            result.append(clean)
    return result


def extract_requirements(value):
    """Accept a JSON skill list or an object with a 'skills' list."""
    parsed = parse_json(value, [])
    if isinstance(parsed, dict):
        parsed = parsed.get("skills", [])
    return normalize_skills(parsed) if isinstance(parsed, list) else []


def score_job(requirements, user_skills):
    """Match percentage = matched required skills / total required skills * 100.

    Jobs with no listed requirements receive 0%, not an artificial 100%.
    """
    required = extract_requirements(requirements)
    provided = {skill.casefold() for skill in normalize_skills(user_skills)}
    matched = [skill for skill in required if skill.casefold() in provided]
    missing = [skill for skill in required if skill.casefold() not in provided]
    percent = round(100 * len(matched) / len(required)) if required else 0
    return {
        "percentage": percent,
        "matched": matched,
        "missing": missing,
        "matched_count": len(matched),
        "required_count": len(required),
    }


def rank_jobs(jobs, user_skills):
    """Return jobs with skill metrics, highest matches first."""
    results = []
    for job in jobs:
        results.append({**job, **score_job(job.get("requirements"), user_skills)})
    return sorted(
        results,
        key=lambda job: (-job["percentage"], -job["matched_count"],
                         str(job.get("job_title", "")).casefold()),
    )
