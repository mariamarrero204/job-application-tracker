"""Automated tests for the skill matching algorithm."""
from matching import extract_requirements, normalize_skills, rank_jobs, score_job


def test_normalizes_and_deduplicates_case_insensitively():
    assert normalize_skills("  Python , SQL, python, FLASK , , sql ") == ["Python", "SQL", "FLASK"]


def test_json_skills_are_read_correctly():
    assert extract_requirements('["Python", "SQL", "Flask"]') == ["Python", "SQL", "Flask"]
    assert extract_requirements('{"skills": ["SQL", "Git"]}') == ["SQL", "Git"]


def test_bad_json_cannot_break_matching():
    assert extract_requirements("{invalid-json") == []
    assert extract_requirements(None) == []


def test_two_out_of_three_skills_is_67_percent():
    result = score_job('["Python", "SQL", "Flask"]', "python, SQL")
    assert result["percentage"] == 67
    assert result["matched"] == ["Python", "SQL"]
    assert result["missing"] == ["Flask"]
    assert result["matched_count"] == 2
    assert result["required_count"] == 3


def test_complete_match_and_empty_requirements():
    assert score_job('["Python", "SQL"]', "sql, python")["percentage"] == 100
    assert score_job("[]", "Python")["percentage"] == 0
    assert score_job("[]", "Python")["required_count"] == 0


def test_jobs_are_ranked_highest_first():
    jobs = [
        {"job_id": 1, "job_title": "Low", "requirements": '["Python","SQL","Tableau"]'},
        {"job_id": 2, "job_title": "High", "requirements": '["Python","SQL"]'},
        {"job_id": 3, "job_title": "None", "requirements": '["Java"]'},
    ]
    ranked = rank_jobs(jobs, "Python, SQL")
    assert [job["job_id"] for job in ranked] == [2, 1, 3]
    assert [job["percentage"] for job in ranked] == [100, 67, 0]
