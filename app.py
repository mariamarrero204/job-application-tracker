"""Flask web application for COP4751 Job Application Tracker."""
import json
import os
import re
import secrets
from datetime import date
from urllib.parse import urlparse

import mysql.connector
from flask import (
    Flask, abort, flash, redirect, render_template, request, session, url_for,
)
from werkzeug.exceptions import HTTPException

import database as db
from matching import extract_requirements, normalize_skills, parse_json, rank_jobs

JOB_TYPES = ("Full-time", "Part-time", "Contract", "Internship")
STATUSES = ("Applied", "Screening", "Interview", "Offer", "Rejected", "Withdrawn")


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=os.environ.get("SECRET_KEY", "local-development-key-change-me"),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
    )
    if test_config:
        app.config.update(test_config)

    @app.context_processor
    def template_globals():
        def csrf_token():
            if "csrf_token" not in session:
                session["csrf_token"] = secrets.token_urlsafe(32)
            return session["csrf_token"]
        return {
            "csrf_token": csrf_token,
            "job_types": JOB_TYPES,
            "statuses": STATUSES,
            "today": date.today().isoformat(),
        }

    @app.before_request
    def protect_forms():
        if request.method == "POST":
            expected = session.get("csrf_token", "")
            received = request.form.get("csrf_token", "")
            if not expected or not secrets.compare_digest(expected, received):
                abort(400, description="Form expired. Reload the page and try again.")

    @app.template_filter("money")
    def money(value):
        return "${:,.0f}".format(value) if value is not None else "—"

    @app.template_filter("datefmt")
    def datefmt(value):
        return value.strftime("%b %d, %Y") if hasattr(value, "strftime") else (value or "—")

    @app.errorhandler(mysql.connector.Error)
    def mysql_error(error):
        app.logger.exception("MySQL database error: %s", error)
        return render_template("database_error.html"), 503

    @app.errorhandler(HTTPException)
    def http_error(error):
        return render_template("http_error.html", error=error), error.code

    def get_or_404(table, pk, value):
        # 'table' and 'pk' always originate from hardcoded route definitions.
        record = db.fetch_one(f"SELECT * FROM {table} WHERE {pk} = %s", (value,))
        if record is None:
            abort(404, description="That record could not be found.")
        return record

    def required(form, key, label, errors, max_length=None):
        value = (form.get(key) or "").strip()
        if not value:
            errors.append(f"{label} is required.")
        if max_length and len(value) > max_length:
            errors.append(f"{label} must be {max_length} characters or fewer.")
        return value

    def optional(form, key, label, errors, max_length=None):
        value = (form.get(key) or "").strip()
        if max_length and len(value) > max_length:
            errors.append(f"{label} must be {max_length} characters or fewer.")
        return value or None

    def optional_url(form, key, label, errors, max_length):
        value = optional(form, key, label, errors, max_length)
        if value:
            parts = urlparse(value)
            if parts.scheme not in ("http", "https") or not parts.netloc:
                errors.append(f"{label} must be a full http:// or https:// URL.")
        return value

    def optional_date(form, key, label, errors):
        value = (form.get(key) or "").strip()
        if not value:
            return None
        try:
            return date.fromisoformat(value).isoformat()
        except ValueError:
            errors.append(f"{label} must be a valid date.")
            return None

    def optional_int(form, key, label, errors):
        raw = (form.get(key) or "").strip()
        if not raw:
            return None
        try:
            value = int(raw)
            if not 0 <= value <= 2147483647:
                raise ValueError
            return value
        except ValueError:
            errors.append(f"{label} must be a nonnegative whole number.")
            return None

    def foreign_id(form, key, label, table, pk, errors):
        raw = (form.get(key) or "").strip()
        try:
            value = int(raw)
            if value <= 0:
                raise ValueError
        except ValueError:
            errors.append(f"Select a valid {label}.")
            return None
        if db.fetch_one(f"SELECT {pk} FROM {table} WHERE {pk} = %s", (value,)) is None:
            errors.append(f"The selected {label} no longer exists.")
        return value

    def show_errors(errors):
        for message in errors:
            flash(message, "error")

    def delete_record(table, pk, record_id, label, redirect_endpoint):
        get_or_404(table, pk, record_id)
        try:
            db.execute(f"DELETE FROM {table} WHERE {pk} = %s", (record_id,))
            flash(f"{label} deleted successfully.", "success")
        except mysql.connector.IntegrityError:
            flash(
                f"Cannot delete this {label.lower()} while related records exist. "
                "Delete or reassign those records first.", "error"
            )
        return redirect(url_for(redirect_endpoint))

    @app.get("/")
    def dashboard():
        counts = db.fetch_one("""
            SELECT
              (SELECT COUNT(*) FROM companies) AS companies,
              (SELECT COUNT(*) FROM jobs) AS jobs,
              (SELECT COUNT(*) FROM applications) AS applications,
              (SELECT COUNT(*) FROM contacts) AS contacts,
              (SELECT COUNT(*) FROM applications WHERE status = 'Interview') AS interviews,
              (SELECT COUNT(*) FROM applications WHERE status = 'Offer') AS offers,
              (SELECT COUNT(*) FROM applications
                WHERE status IN ('Applied','Screening','Interview','Offer')) AS active
        """)
        recent = db.fetch_all("""
            SELECT a.application_id, a.application_date, a.status,
                   j.job_title, c.company_name
            FROM applications a
            JOIN jobs j ON a.job_id = j.job_id
            JOIN companies c ON j.company_id = c.company_id
            ORDER BY a.application_date DESC, a.application_id DESC LIMIT 6
        """)
        breakdown = db.fetch_all("""
            SELECT status, COUNT(*) AS total FROM applications
            GROUP BY status ORDER BY FIELD(
              status,'Applied','Screening','Interview','Offer','Rejected','Withdrawn')
        """)
        return render_template("dashboard.html", counts=counts,
                               recent=recent, breakdown=breakdown)

    # ---------------------------- COMPANIES ----------------------------
    @app.get("/companies")
    def companies():
        records = db.fetch_all("""
            SELECT c.*, (SELECT COUNT(*) FROM jobs j WHERE j.company_id=c.company_id) AS job_count,
                   (SELECT COUNT(*) FROM contacts t WHERE t.company_id=c.company_id) AS contact_count
            FROM companies c ORDER BY c.company_name
        """)
        return render_template("companies.html", records=records)

    @app.route("/companies/new", methods=["GET", "POST"])
    def company_new():
        data = {}
        if request.method == "POST":
            data = request.form.to_dict()
            errors = []
            name = required(request.form, "company_name", "Company name", errors, 100)
            industry = optional(request.form, "industry", "Industry", errors, 50)
            website = optional_url(request.form, "website", "Website", errors, 200)
            city = optional(request.form, "city", "City", errors, 50)
            state = optional(request.form, "state", "State", errors, 50)
            notes = optional(request.form, "notes", "Notes", errors)
            if not errors:
                pk, _ = db.execute("""
                    INSERT INTO companies (company_name,industry,website,city,state,notes)
                    VALUES (%s,%s,%s,%s,%s,%s)
                """, (name, industry, website, city, state, notes))
                flash("Company added successfully.", "success")
                return redirect(url_for("company_detail", record_id=pk))
            show_errors(errors)
        return render_template("company_form.html", record=data, is_edit=False)

    @app.get("/companies/<int:record_id>")
    def company_detail(record_id):
        record = get_or_404("companies", "company_id", record_id)
        jobs = db.fetch_all("SELECT job_id,job_title,job_type FROM jobs WHERE company_id=%s ORDER BY job_title", (record_id,))
        contacts = db.fetch_all("SELECT contact_id,contact_name,title FROM contacts WHERE company_id=%s ORDER BY contact_name", (record_id,))
        return render_template("company_detail.html", record=record, jobs=jobs, contacts=contacts)

    @app.route("/companies/<int:record_id>/edit", methods=["GET", "POST"])
    def company_edit(record_id):
        record = get_or_404("companies", "company_id", record_id)
        if request.method == "POST":
            record = request.form.to_dict()
            errors = []
            name = required(request.form, "company_name", "Company name", errors, 100)
            industry = optional(request.form, "industry", "Industry", errors, 50)
            website = optional_url(request.form, "website", "Website", errors, 200)
            city = optional(request.form, "city", "City", errors, 50)
            state = optional(request.form, "state", "State", errors, 50)
            notes = optional(request.form, "notes", "Notes", errors)
            if not errors:
                db.execute("""
                    UPDATE companies SET company_name=%s,industry=%s,website=%s,
                    city=%s,state=%s,notes=%s WHERE company_id=%s
                """, (name, industry, website, city, state, notes, record_id))
                flash("Company updated successfully.", "success")
                return redirect(url_for("company_detail", record_id=record_id))
            show_errors(errors)
        return render_template("company_form.html", record=record, is_edit=True, record_id=record_id)

    @app.post("/companies/<int:record_id>/delete")
    def company_delete(record_id):
        return delete_record("companies", "company_id", record_id, "Company", "companies")

    # ------------------------------- JOBS ------------------------------
    def job_form_data(form, errors):
        company_id = foreign_id(form, "company_id", "company", "companies", "company_id", errors)
        title = required(form, "job_title", "Job title", errors, 100)
        kind = optional(form, "job_type", "Job type", errors)
        if kind and kind not in JOB_TYPES:
            errors.append("Select a valid job type.")
        salary_min = optional_int(form, "salary_min", "Minimum salary", errors)
        salary_max = optional_int(form, "salary_max", "Maximum salary", errors)
        if salary_min is not None and salary_max is not None and salary_min > salary_max:
            errors.append("Minimum salary cannot exceed maximum salary.")
        job_url = optional_url(form, "job_url", "Job URL", errors, 300)
        posted = optional_date(form, "date_posted", "Posting date", errors)
        skills_text = (form.get("requirements_text") or "").strip()
        if len(skills_text) > 3000:
            errors.append("Skill requirements text is too long.")
        skills = normalize_skills(skills_text)
        if any(len(skill) > 100 for skill in skills):
            errors.append("Each skill must be 100 characters or fewer.")
        return (company_id, title, kind, salary_min, salary_max, job_url,
                posted, json.dumps(skills))

    def job_for_form(record):
        result = dict(record)
        result["requirements_text"] = ", ".join(extract_requirements(record.get("requirements")))
        if result.get("date_posted"):
            result["date_posted"] = str(result["date_posted"])
        return result

    @app.get("/jobs")
    def jobs():
        records = db.fetch_all("""
            SELECT j.*,c.company_name,
              (SELECT COUNT(*) FROM applications a WHERE a.job_id=j.job_id) AS application_count
            FROM jobs j JOIN companies c ON j.company_id=c.company_id
            ORDER BY j.job_id DESC
        """)
        return render_template("jobs.html", records=records)

    @app.route("/jobs/new", methods=["GET", "POST"])
    def job_new():
        companies_list = db.fetch_all("SELECT company_id,company_name FROM companies ORDER BY company_name")
        data = {"company_id": request.args.get("company_id", "")}
        if request.method == "POST":
            data = request.form.to_dict()
            errors = []
            fields = job_form_data(request.form, errors)
            if not errors:
                pk, _ = db.execute("""
                    INSERT INTO jobs (company_id,job_title,job_type,salary_min,salary_max,
                                      job_url,date_posted,requirements)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                """, fields)
                flash("Job added successfully.", "success")
                return redirect(url_for("job_detail", record_id=pk))
            show_errors(errors)
        return render_template("job_form.html", record=data, is_edit=False,
                               companies_list=companies_list)

    @app.get("/jobs/<int:record_id>")
    def job_detail(record_id):
        record = db.fetch_one("""
            SELECT j.*,c.company_name FROM jobs j
            JOIN companies c ON j.company_id=c.company_id WHERE j.job_id=%s
        """, (record_id,))
        if not record:
            abort(404)
        applications = db.fetch_all("""
            SELECT application_id,application_date,status FROM applications
            WHERE job_id=%s ORDER BY application_date DESC
        """, (record_id,))
        return render_template("job_detail.html", record=record,
                               requirements=extract_requirements(record["requirements"]),
                               applications=applications)

    @app.route("/jobs/<int:record_id>/edit", methods=["GET", "POST"])
    def job_edit(record_id):
        record = get_or_404("jobs", "job_id", record_id)
        companies_list = db.fetch_all("SELECT company_id,company_name FROM companies ORDER BY company_name")
        data = job_for_form(record)
        if request.method == "POST":
            data = request.form.to_dict()
            errors = []
            fields = job_form_data(request.form, errors)
            if not errors:
                db.execute("""
                    UPDATE jobs SET company_id=%s,job_title=%s,job_type=%s,
                      salary_min=%s,salary_max=%s,job_url=%s,date_posted=%s,
                      requirements=%s WHERE job_id=%s
                """, (*fields, record_id))
                flash("Job updated successfully.", "success")
                return redirect(url_for("job_detail", record_id=record_id))
            show_errors(errors)
        return render_template("job_form.html", record=data, is_edit=True,
                               record_id=record_id, companies_list=companies_list)

    @app.post("/jobs/<int:record_id>/delete")
    def job_delete(record_id):
        return delete_record("jobs", "job_id", record_id, "Job", "jobs")

    # ---------------------------- APPLICATIONS -------------------------
    def application_form_data(form, errors):
        job_id = foreign_id(form, "job_id", "job", "jobs", "job_id", errors)
        applied = optional_date(form, "application_date", "Application date", errors)
        if not applied:
            errors.append("Application date is required.")
        status = (form.get("status") or "Applied").strip()
        if status not in STATUSES:
            errors.append("Select a valid application status.")
        resume = optional(form, "resume_version", "Resume version", errors, 50)
        cover = int(form.get("cover_letter_sent") == "on")
        interview_date = optional_date(form, "interview_date", "Interview date", errors)
        mode = optional(form, "interview_mode", "Interview format", errors, 50)
        notes = optional(form, "interview_notes", "Interview notes", errors)
        interview = {"date": interview_date, "mode": mode, "notes": notes}
        interview_json = json.dumps(interview) if any(interview.values()) else None
        return job_id, applied, status, resume, cover, interview_json

    def application_for_form(record):
        result = dict(record)
        interview = parse_json(record.get("interview_data"), {})
        if not isinstance(interview, dict):
            interview = {}
        result.update(
            interview_date=interview.get("date") or "",
            interview_mode=interview.get("mode") or "",
            interview_notes=interview.get("notes") or "",
        )
        if result.get("application_date"):
            result["application_date"] = str(result["application_date"])
        return result

    def job_options():
        return db.fetch_all("""
            SELECT j.job_id,j.job_title,c.company_name FROM jobs j
            JOIN companies c ON c.company_id=j.company_id
            ORDER BY c.company_name,j.job_title
        """)

    @app.get("/applications")
    def applications():
        records = db.fetch_all("""
            SELECT a.*,j.job_title,c.company_name FROM applications a
            JOIN jobs j ON a.job_id=j.job_id
            JOIN companies c ON j.company_id=c.company_id
            ORDER BY a.application_date DESC,a.application_id DESC
        """)
        return render_template("applications.html", records=records)

    @app.route("/applications/new", methods=["GET", "POST"])
    def application_new():
        data = {"job_id": request.args.get("job_id", ""),
                "application_date": date.today().isoformat(), "status": "Applied"}
        options = job_options()
        if request.method == "POST":
            data = request.form.to_dict()
            errors = []
            fields = application_form_data(request.form, errors)
            if not errors:
                pk, _ = db.execute("""
                    INSERT INTO applications (job_id,application_date,status,resume_version,
                                              cover_letter_sent,interview_data)
                    VALUES (%s,%s,%s,%s,%s,%s)
                """, fields)
                flash("Application added successfully.", "success")
                return redirect(url_for("application_detail", record_id=pk))
            show_errors(errors)
        return render_template("application_form.html", record=data, is_edit=False, job_options=options)

    @app.get("/applications/<int:record_id>")
    def application_detail(record_id):
        record = db.fetch_one("""
            SELECT a.*,j.job_title,j.company_id,c.company_name FROM applications a
            JOIN jobs j ON a.job_id=j.job_id
            JOIN companies c ON j.company_id=c.company_id
            WHERE a.application_id=%s
        """, (record_id,))
        if not record:
            abort(404)
        interview = parse_json(record.get("interview_data"), {})
        return render_template("application_detail.html", record=record,
                               interview=interview if isinstance(interview, dict) else {})

    @app.route("/applications/<int:record_id>/edit", methods=["GET", "POST"])
    def application_edit(record_id):
        record = get_or_404("applications", "application_id", record_id)
        options = job_options()
        data = application_for_form(record)
        if request.method == "POST":
            data = request.form.to_dict()
            errors = []
            fields = application_form_data(request.form, errors)
            if not errors:
                db.execute("""
                    UPDATE applications SET job_id=%s,application_date=%s,status=%s,
                      resume_version=%s,cover_letter_sent=%s,interview_data=%s
                    WHERE application_id=%s
                """, (*fields, record_id))
                flash("Application updated successfully.", "success")
                return redirect(url_for("application_detail", record_id=record_id))
            show_errors(errors)
        return render_template("application_form.html", record=data, is_edit=True,
                               record_id=record_id, job_options=options)

    @app.post("/applications/<int:record_id>/delete")
    def application_delete(record_id):
        return delete_record("applications", "application_id", record_id,
                             "Application", "applications")

    # ------------------------------ CONTACTS ---------------------------
    def contact_form_data(form, errors):
        company_id = foreign_id(form, "company_id", "company", "companies", "company_id", errors)
        name = required(form, "contact_name", "Contact name", errors, 100)
        title = optional(form, "title", "Title", errors, 100)
        email = optional(form, "email", "Email", errors, 100)
        if email and not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
            errors.append("Email address is not valid.")
        phone = optional(form, "phone", "Phone", errors, 20)
        linkedin = optional_url(form, "linkedin_url", "LinkedIn URL", errors, 200)
        notes = optional(form, "notes", "Notes", errors)
        return company_id, name, title, email, phone, linkedin, notes

    @app.get("/contacts")
    def contacts():
        records = db.fetch_all("""
            SELECT t.*,c.company_name FROM contacts t
            JOIN companies c ON t.company_id=c.company_id
            ORDER BY t.contact_name
        """)
        return render_template("contacts.html", records=records)

    @app.route("/contacts/new", methods=["GET", "POST"])
    def contact_new():
        companies_list = db.fetch_all("SELECT company_id,company_name FROM companies ORDER BY company_name")
        data = {"company_id": request.args.get("company_id", "")}
        if request.method == "POST":
            data = request.form.to_dict()
            errors = []
            fields = contact_form_data(request.form, errors)
            if not errors:
                pk, _ = db.execute("""
                    INSERT INTO contacts (company_id,contact_name,title,email,phone,linkedin_url,notes)
                    VALUES (%s,%s,%s,%s,%s,%s,%s)
                """, fields)
                flash("Contact added successfully.", "success")
                return redirect(url_for("contact_detail", record_id=pk))
            show_errors(errors)
        return render_template("contact_form.html", record=data, is_edit=False,
                               companies_list=companies_list)

    @app.get("/contacts/<int:record_id>")
    def contact_detail(record_id):
        record = db.fetch_one("""
            SELECT t.*,c.company_name FROM contacts t
            JOIN companies c ON t.company_id=c.company_id WHERE t.contact_id=%s
        """, (record_id,))
        if not record:
            abort(404)
        return render_template("contact_detail.html", record=record)

    @app.route("/contacts/<int:record_id>/edit", methods=["GET", "POST"])
    def contact_edit(record_id):
        record = get_or_404("contacts", "contact_id", record_id)
        companies_list = db.fetch_all("SELECT company_id,company_name FROM companies ORDER BY company_name")
        data = dict(record)
        if request.method == "POST":
            data = request.form.to_dict()
            errors = []
            fields = contact_form_data(request.form, errors)
            if not errors:
                db.execute("""
                    UPDATE contacts SET company_id=%s,contact_name=%s,title=%s,email=%s,
                      phone=%s,linkedin_url=%s,notes=%s WHERE contact_id=%s
                """, (*fields, record_id))
                flash("Contact updated successfully.", "success")
                return redirect(url_for("contact_detail", record_id=record_id))
            show_errors(errors)
        return render_template("contact_form.html", record=data, is_edit=True,
                               record_id=record_id, companies_list=companies_list)

    @app.post("/contacts/<int:record_id>/delete")
    def contact_delete(record_id):
        return delete_record("contacts", "contact_id", record_id, "Contact", "contacts")

    # ----------------------------- JOB MATCH ---------------------------
    @app.route("/job-match", methods=["GET", "POST"])
    def job_match():
        user_skills = ""
        results = None
        if request.method == "POST":
            user_skills = (request.form.get("skills") or "").strip()
            if not user_skills:
                flash("Enter at least one skill to compare.", "error")
            elif len(user_skills) > 3000:
                flash("Skill list is too long.", "error")
            else:
                job_records = db.fetch_all("""
                    SELECT j.job_id,j.job_title,j.requirements,j.job_type,
                           c.company_name FROM jobs j
                    JOIN companies c ON j.company_id=c.company_id
                """)
                results = rank_jobs(job_records, user_skills)
                user_skills = ", ".join(normalize_skills(user_skills))
        return render_template("job_match.html", user_skills=user_skills, results=results)

    return app


app = create_app()

if __name__ == "__main__":
    # Set FLASK_DEBUG=1 for local development. Do not use debug mode in production.
    app.run(debug=os.getenv("FLASK_DEBUG") == "1")
