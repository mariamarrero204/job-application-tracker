"""Flask route and rendering tests; MySQL operations are mocked.

End-to-end tests against a real MySQL database must also be run by the student.
"""
import json
import re
from datetime import date

import pytest
import app as app_module

COMPANY = {"company_id": 1, "company_name": "Test Company", "industry": "IT",
           "website": "https://example.com", "city": "Miami", "state": "Florida", "notes": "Notes"}
JOB = {"job_id": 2, "company_id": 1, "company_name": "Test Company", "job_title": "Flask Developer",
       "job_type": "Full-time", "salary_min": 50000, "salary_max": 70000, "job_url": None,
       "date_posted": date(2026, 11, 10), "requirements": json.dumps(["Python", "SQL", "Flask"])}
APPLICATION = {"application_id": 3, "job_id": 2, "company_id": 1, "job_title": "Flask Developer",
               "company_name": "Test Company", "application_date": date(2026, 11, 12),
               "status": "Interview", "resume_version": "v1", "cover_letter_sent": 1,
               "interview_data": json.dumps({"date":"2026-11-18", "mode":"Video", "notes":"Prepare"})}
CONTACT = {"contact_id": 4, "company_id": 1, "company_name": "Test Company",
           "contact_name": "Jordan Lee", "title": "Recruiter", "email": "jordan@example.com",
           "phone": None, "linkedin_url": None, "notes": "Friendly"}


@pytest.fixture()
def client(monkeypatch):
    def fake_one(sql, params=()):
        if "SELECT\n" in sql and "AS companies" in sql:
            return {"companies": 1, "jobs": 1, "applications": 1,
                    "contacts": 1, "interviews": 1, "offers": 0, "active": 1}
        if "SELECT * FROM companies WHERE" in sql:
            return dict(COMPANY)
        if "SELECT * FROM jobs WHERE" in sql:
            return dict(JOB)
        if "SELECT * FROM applications WHERE" in sql:
            return dict(APPLICATION)
        if "SELECT * FROM contacts WHERE" in sql:
            return dict(CONTACT)
        if "FROM jobs j" in sql and "WHERE j.job_id" in sql:
            return dict(JOB)
        if "FROM applications a" in sql and "WHERE a.application_id" in sql:
            return dict(APPLICATION)
        if "FROM contacts t" in sql and "WHERE t.contact_id" in sql:
            return dict(CONTACT)
        if "FROM companies" in sql:
            return {"company_id": 1}
        if "FROM jobs" in sql:
            return {"job_id": 2}
        raise AssertionError(f"Unexpected SQL: {sql}")

    def fake_all(sql, params=()):
        if "FROM companies c ORDER" in sql:
            return [{**COMPANY, "job_count": 1, "contact_count": 1}]
        if "FROM companies ORDER BY" in sql:
            return [{"company_id": 1, "company_name": "Test Company"}]
        if "FROM jobs j JOIN companies c" in sql and "WHERE" not in sql:
            return [{**JOB, "application_count": 1}]
        if "FROM jobs j" in sql and "JOIN companies c" in sql and "WHERE" not in sql:
            return [dict(JOB)]
        if "FROM applications a" in sql and "WHERE" not in sql:
            return [dict(APPLICATION)]
        if "FROM contacts t" in sql:
            return [dict(CONTACT)]
        if "FROM jobs j" in sql and "JOIN companies c" in sql:
            return [dict(JOB)]
        if "FROM jobs WHERE company_id=" in sql:
            return [{"job_id": 2, "job_title": "Flask Developer", "job_type": "Full-time"}]
        if "FROM contacts WHERE company_id=" in sql:
            return [{"contact_id": 4, "contact_name": "Jordan Lee", "title": "Recruiter"}]
        if "FROM applications" in sql and "WHERE job_id=" in sql:
            return [dict(APPLICATION)]
        if "FROM applications" in sql and "GROUP BY status" in sql:
            return [{"status": "Interview", "total": 1}]
        if "FROM applications a" in sql:
            return [dict(APPLICATION)]
        return []

    monkeypatch.setattr(app_module.db, "fetch_one", fake_one)
    monkeypatch.setattr(app_module.db, "fetch_all", fake_all)
    app = app_module.create_app({"TESTING": True, "SECRET_KEY": "safe-test-key"})
    with app.test_client() as client:
        yield client


def get_csrf(response):
    value = re.search(rb'name="csrf_token" value="([^"]+)"', response.data)
    assert value, "Expected hidden CSRF token in form"
    return value.group(1).decode()


@pytest.mark.parametrize("url, expected", [
    ("/", "Your search at a glance"), ("/companies", "Companies"),
    ("/jobs", "Saved jobs"), ("/applications", "Applications"),
    ("/contacts", "Contacts"), ("/job-match", "Find your fit"),
    ("/companies/new", "Add a company"), ("/jobs/new", "Add a job"),
    ("/applications/new", "Track an application"), ("/contacts/new", "Add a contact"),
    ("/companies/1", "Company information"), ("/jobs/2", "Position details"),
    ("/applications/3", "Application information"), ("/contacts/4", "Contact information"),
    ("/companies/1/edit", "Edit company"), ("/jobs/2/edit", "Edit job"),
    ("/applications/3/edit", "Edit application"), ("/contacts/4/edit", "Edit contact"),
])
def test_get_pages_render(client, url, expected):
    response = client.get(url)
    assert response.status_code == 200, (url, response.data.decode()[:600])
    assert expected.encode() in response.data


def test_job_match_renders_67_percent_and_missing_skill(client):
    token = get_csrf(client.get("/job-match"))
    response = client.post("/job-match", data={"csrf_token": token, "skills": "python, SQL"})
    assert response.status_code == 200
    assert b"67" in response.data
    assert b"Flask" in response.data
    assert b"MISSING" in response.data


def test_invalid_company_input_shows_validation_error(client):
    token = get_csrf(client.get("/companies/new"))
    response = client.post("/companies/new", data={
        "csrf_token": token, "company_name": "Test Company", "website": "not-a-url",
    })
    assert response.status_code == 200
    assert b"full http:// or https:// URL" in response.data


def test_company_create_posts_parameterized_values(client, monkeypatch):
    writes = []
    monkeypatch.setattr(app_module.db, "execute", lambda sql, params=(): (writes.append((sql, params)) or (10, 1)))
    token = get_csrf(client.get("/companies/new"))
    response = client.post("/companies/new", data={
        "csrf_token": token, "company_name": "Acme", "city": "Miami",
    })
    assert response.status_code == 302
    assert response.location.endswith("/companies/10")
    assert len(writes) == 1
    assert "%s" in writes[0][0]
    assert writes[0][1][0] == "Acme"


def test_missing_csrf_is_rejected(client):
    response = client.post("/companies/new", data={"company_name": "Acme"})
    assert response.status_code == 400
