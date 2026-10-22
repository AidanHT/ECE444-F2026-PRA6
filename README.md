# ECE444 PRA6: TDD and Web App Deployment

Aidan Tran

Flaskr blog app built test-first by following the
[flaskr-tdd README](https://github.com/shuruizUofT/flaskr-tdd/blob/main/README.md).
Each tested feature has an `Add failing ...` commit with the new tests, followed
by the commit that makes them pass.

## Run locally

From this folder in Windows PowerShell:

```powershell
python -m venv env
.\env\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python create_db.py
python -m flask --app project/app.py run -p 5001
```

Open http://localhost:5001 and log in with `admin` / `admin`. When logged in,
you can share a post or delete one by clicking it. The Search page finds posts
whose title or text contains the query, ignoring case.

## Tests and linting

```powershell
python -m pytest
python -m flake8 --exclude env --ignore E402,E501 .
python -m black --exclude=env --check .
```

All tests are in [`tests/app_test.py`](tests/app_test.py). The `client` fixture
creates the tables in `test.db` before each test and drops them after, so every
test starts with an empty database.

| Test | Source | Checks |
| --- | --- | --- |
| `test_index` | README | `/` returns 200 |
| `test_database` | README | `test.db` exists |
| `test_uses_test_database` | mine | the tests use `test.db`, not the app's database |
| `test_empty_db` | README | an empty database shows "No entries yet. Add some!" |
| `test_login_logout` | README | logging in and out works, and a wrong username or password is rejected |
| `test_messages` | README | a logged-in user can post; the title is escaped and the text can contain HTML |
| `test_index_links_to_search` | mine | the index page links to `/search/` |
| `test_search_page` | mine | `/search/` loads with a search box |
| `test_search_by_title` | mine | a query matches titles, ignoring case, and leaves out other posts |
| `test_search_by_text` | mine | a query also matches the post text |
| `test_search_results_have_post_id` | mine | each result has the post id that `main.js` uses to delete it |
| `test_add_requires_login` | mine | posting while logged out returns 401 and adds nothing |
| `test_delete_message` | README | deleting returns status 0 when logged out and 1 when logged in |
| `test_delete_requires_login` | mine | deleting while logged out returns 401 with "Please log in." and keeps the post |
| `test_delete_removes_post` | mine | deleting while logged in removes the post from the page |
| `test_postgres_url_is_rewritten` | mine | a `postgres://` `DATABASE_URL` becomes `postgresql://` and the app can build a Postgres engine |

## Changes from the tutorial

- **Tests use `test.db`.** Flask-SQLAlchemy 3 creates the database engine when
  `SQLAlchemy(app)` runs. The README's fixture changes `SQLALCHEMY_DATABASE_URI`
  after that, so the tests actually ran on `project/flaskr.db`, and `drop_all()`
  deleted its table. With `DATABASE_URL` set to the Render database, as in the
  Postgres steps, they would have dropped the production table. I moved the
  README's `DATABASE_URL` setting up to the SQLAlchemy step, and the test file
  sets it to `test.db` before importing the app. `test_uses_test_database`
  checks this.
- **SQLAlchemy is pinned to 2.0.** SQLAlchemy 2.1 uses psycopg 3 for
  `postgresql://` URLs by default, but the tutorial installs psycopg2, so the app
  failed to start with a Postgres URL. `test_postgres_url_is_rewritten` caught
  this.
- **Search results use `entry.id`.** The README's `search.html` uses
  `entry.post_id`, which `Post` does not have, so results had an empty id and
  could not be deleted by clicking them.
- **The SQLite delete query uses a parameter** instead of string concatenation,
  to avoid SQL injection. SQLAlchemy later replaced this query.
- **Requirements are pinned** to the versions I tested with.
