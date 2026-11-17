# Job Application Tracker

## Setup Instructions

### 1. Requirements

Make sure the following software is installed:

- Python 3.10 or newer
- MySQL Server 8.0 or newer
- MySQL Workbench
- IntelliJ IDEA or another code editor
- Git (optional, for cloning the repository)

### 2. Download the Project

Clone the repository using Git:

```bash
git clone https://github.com/mariamarrero204/job-application-tracker.git
cd job-application-tracker
```

Alternatively, download the repository as a ZIP file, extract it, and open the project folder in IntelliJ IDEA.

### 3. Install Dependencies

Open a terminal in the project directory and create a Python virtual environment.

For Windows:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

For macOS or Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install the required Python packages:

```bash
python -m pip install -r requirements.txt
```

### 4. Set Up the MySQL Database

1. Open MySQL Workbench and connect to your local MySQL server.
2. Select **File → Open SQL Script** and open `schema.sql`.
3. Execute the script to create the `job_tracker` database.
4. Verify that the following tables were created:
   - `companies`
   - `jobs`
   - `applications`
   - `contacts`

Optional: Execute `seed.sql` once to populate a new database with sample records.

### 5. Configure the Database Connection

Create a `.env` file in the project's root directory by copying `.env.example`.

On Windows:

```powershell
Copy-Item .env.example .env
```

Update the `.env` file with your MySQL credentials:

```dotenv
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=YOUR_MYSQL_PASSWORD
DB_NAME=job_tracker
SECRET_KEY=YOUR_SECRET_KEY
```

Replace `YOUR_MYSQL_PASSWORD` with your local MySQL password.

Generate a secret key using:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

Copy the generated value into `SECRET_KEY`.

**Note:** The `.env` file contains private configuration information and should not be uploaded to GitHub.

### 6. Run the Application

Make sure MySQL Server is running and the Python virtual environment is activated.

Start the Flask application:

```bash
python app.py
```

Open your browser and navigate to:

**http://127.0.0.1:5000**

The Job Application Tracker dashboard should appear. Keep the terminal running while using the application.

To stop the server, press `Ctrl + C`.

### 7. Run Tests

To execute the automated tests, run:

```bash
python -m pytest -v
```

To manually verify database functionality, use the application to create, view, edit, and delete records from each table. Confirm the changes in MySQL Workbench.

The application is ready to use once the database connection, dashboard, and CRUD operations are working correctly.
