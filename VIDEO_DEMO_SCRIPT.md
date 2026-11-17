# Required 3–7 Minute Video — Recording Plan

**The instructor states that the project will not be graded without a real video file uploaded to GitHub.** This file is only a guide, not a substitute for the recording.

## Suggested 5-minute walkthrough

| Approximate time | What to show on your computer |
| --- | --- |
| 0:00–0:35 | Briefly show the project folder/repository, `app.py`, `database.py`, `schema.sql`, and open the running homepage in the browser. |
| 0:35–1:15 | Show MySQL Workbench with the four tables and their columns/foreign keys; demonstrate that rows exist. |
| 1:15–2:15 | In the browser, create a company, add a job with skills (`Python, SQL, Flask`), and add a contact. |
| 2:15–3:05 | Add an application for the saved job. Update the status to `Interview` and save interview information. Show the dashboard counts changing. |
| 3:05–3:45 | Edit one record. Delete a demo contact after confirming the deletion; verify that the row disappears. |
| 3:45–4:30 | Use Job Match: input `Python, SQL`, demonstrate a 67% match for a job requiring `Python, SQL, Flask`, and point out `Flask` as a missing skill. |
| 4:30–5:00 | Return to MySQL Workbench and run `SELECT` queries showing newly created/edited/deleted data; briefly show the running Flask terminal. |

The instructor allows a video **between 3 and 7 minutes**. Narration is optional, but it can help make each step obvious. Record the **actual running application**, not screenshots, code alone, or a static slideshow.

## SQL queries useful in the recording

```sql
USE job_tracker;
SELECT * FROM companies;
SELECT job_id, company_id, job_title, requirements FROM jobs;
SELECT application_id, job_id, status, interview_data FROM applications;
SELECT * FROM contacts;
```

## How to record and submit

On Windows 11 you can use the built-in Snipping Tool screen recorder or another screen recorder. Make sure the browser, terminal showing Flask, and MySQL Workbench appear clearly during the demonstration. Export the final recording to `.mp4` (or another playable format accepted by GitHub) and **put that actual file in your repository**. Avoid recording personal passwords, `.env` contents, or private job-search data; the example `seed.sql` uses fictional companies for this purpose.

Keep the file reasonably small (ideally under 25 MB for GitHub web uploads; GitHub imposes additional file-size limits) and verify that the committed recording is visible to your instructor through the repository. Then submit the **GitHub repository URL** in Canvas.

## Final checklist

- [ ] Recording lasts at least 3 and no more than 7 minutes.
- [ ] Browser demonstrates all four tables' CRUD functionality.
- [ ] Dashboard and Job Match are demonstrated with meaningful data.
- [ ] MySQL Workbench or SQL query output is visible.
- [ ] Flask server is visible in the running terminal.
- [ ] Recording file is actually committed/uploaded to GitHub.
- [ ] README includes reproducible setup instructions.
- [ ] AI_USAGE.md has been personalized with truthful usage records.
- [ ] Repository is accessible to the instructor.
