-- OPTIONAL demo data for your 3–7 minute recording.
-- Import once into the database created by schema.sql.
-- It will add new records on each run; avoid re-importing repeatedly.
USE job_tracker;

INSERT INTO companies (company_name,industry,website,city,state,notes) VALUES
('Harborview Systems','Information Technology','https://example.com/harborview','Miami','Florida','Example company for demonstrating the project.'),
('Cypress Analytics','Data Analytics','https://example.com/cypress','Fort Lauderdale','Florida','Example company for demonstrating the project.'),
('Northstar Cloud','Cloud Computing','https://example.com/northstar','Remote',NULL,'Example company for demonstrating the project.');

-- Resolve company IDs by their unique demonstration names (the inserts above).
INSERT INTO jobs (company_id,job_title,job_type,salary_min,salary_max,job_url,date_posted,requirements)
SELECT company_id,'IT Support Specialist','Full-time',52000,68000,NULL,'2026-11-10',JSON_ARRAY('Windows','Active Directory','Troubleshooting','Networking')
FROM companies WHERE company_name='Harborview Systems' ORDER BY company_id DESC LIMIT 1;
INSERT INTO jobs (company_id,job_title,job_type,salary_min,salary_max,job_url,date_posted,requirements)
SELECT company_id,'Junior Data Analyst','Full-time',58000,76000,NULL,'2026-11-08',JSON_ARRAY('SQL','Python','Tableau')
FROM companies WHERE company_name='Cypress Analytics' ORDER BY company_id DESC LIMIT 1;
INSERT INTO jobs (company_id,job_title,job_type,salary_min,salary_max,job_url,date_posted,requirements)
SELECT company_id,'Cloud Support Associate','Full-time',60000,80000,NULL,'2026-11-12',JSON_ARRAY('AWS','Python','Networking','Linux')
FROM companies WHERE company_name='Northstar Cloud' ORDER BY company_id DESC LIMIT 1;

INSERT INTO applications(job_id,application_date,status,resume_version,cover_letter_sent,interview_data)
SELECT job_id,'2026-11-11','Interview','IT-Support-v2',TRUE,
 JSON_OBJECT('date','2026-11-20','mode','Video','notes','Prepare troubleshooting examples.')
FROM jobs WHERE job_title='IT Support Specialist' ORDER BY job_id DESC LIMIT 1;
INSERT INTO applications(job_id,application_date,status,resume_version,cover_letter_sent,interview_data)
SELECT job_id,'2026-11-13','Applied','Data-Analyst-v1',FALSE,NULL
FROM jobs WHERE job_title='Junior Data Analyst' ORDER BY job_id DESC LIMIT 1;

INSERT INTO contacts(company_id,contact_name,title,email,phone,linkedin_url,notes)
SELECT company_id,'Jordan Lee','Recruiter','jordan.lee@example.com',NULL,NULL,'Example recruiter contact.'
FROM companies WHERE company_name='Harborview Systems' ORDER BY company_id DESC LIMIT 1;
