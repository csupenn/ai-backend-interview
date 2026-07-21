Set up a minimal, interview-ready Python FastAPI backend project in this repository.

Goals:

* Provide clean project scaffolding only
* Keep the architecture simple and easy to explain
* Avoid implementing any business-specific functionality
* Make the project immediately runnable and testable

Create this structure:

app/
**init**.py
main.py
api/
**init**.py
routes.py
models/
**init**.py
schemas.py
services/
**init**.py
repositories/
**init**.py
tests/
**init**.py
test_health.py
README.md
requirements.txt
.env.example
.gitignore
pyproject.toml

Requirements:

1. Use Python 3.12.3 and FastAPI.
2. Add a GET /health endpoint returning:
   {"status": "ok"}
3. Keep routing separate from app initialization.
4. Add a pytest test for the health endpoint using FastAPI TestClient.
5. Configure Ruff in pyproject.toml for linting and formatting.
6. Include these dependencies:

   * fastapi[standard]
   * pytest
   * httpx
   * ruff
7. Add a .gitignore covering:

   * .venv
   * **pycache**
   * .pytest_cache
   * .ruff_cache
   * .env
   * *.pyc
8. Add an .env.example file without real credentials.
9. Write a concise README containing:

   * Project overview
   * Project structure
   * Environment setup
   * How to run the API
   * How to run tests
   * How to run linting
   * Current limitations
10. Do not add a database, authentication, Docker, migrations, queues, or unnecessary abstractions.
11. Use clear type annotations and simple, readable code.
12. After creating the files:

* install dependencies into the active virtual environment
* run Ruff
* run pytest
* start the FastAPI app briefly to verify it loads

13. Fix any errors you encounter.
14. Do not commit or push anything to GitHub.

Before making changes, briefly show me the proposed file structure. Then create the files, run the checks, and finish with a concise summary of:

* files created
* commands run
* test results
* how to start the application

This keeps the repository generic enough to adapt quickly once the interviewer gives you the actual backend problem.
