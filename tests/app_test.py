import json
import os
import subprocess
import sys
import pytest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
TEST_DB = "test.db"

# Flask-SQLAlchemy builds the engine when project.app is imported,
# so the test database has to be chosen before that import
os.environ["DATABASE_URL"] = f"sqlite:///{BASE_DIR.joinpath(TEST_DB)}"

from project.app import app, db


@pytest.fixture
def client():
    app.config["TESTING"] = True

    with app.app_context():
        db.create_all()  # setup
        yield app.test_client()  # tests run here
        db.drop_all()  # teardown


def login(client, username, password):
    """Login helper function"""
    return client.post(
        "/login",
        data=dict(username=username, password=password),
        follow_redirects=True,
    )


def logout(client):
    """Logout helper function"""
    return client.get("/logout", follow_redirects=True)


def test_index(client):
    response = client.get("/", content_type="html/text")
    assert response.status_code == 200


def test_database(client):
    """initial test. ensure that the database exists"""
    tester = Path("test.db").is_file()
    assert tester


def test_uses_test_database(client):
    """Ensure the tests run against test.db, not the app's database"""
    assert Path(db.engine.url.database) == BASE_DIR.joinpath(TEST_DB)


def test_empty_db(client):
    """Ensure database is blank"""
    rv = client.get("/")
    assert b"No entries yet. Add some!" in rv.data


def test_login_logout(client):
    """Test login and logout using helper functions"""
    rv = login(client, app.config["USERNAME"], app.config["PASSWORD"])
    assert b"You were logged in" in rv.data
    rv = logout(client)
    assert b"You were logged out" in rv.data
    rv = login(client, app.config["USERNAME"] + "x", app.config["PASSWORD"])
    assert b"Invalid username" in rv.data
    rv = login(client, app.config["USERNAME"], app.config["PASSWORD"] + "x")
    assert b"Invalid password" in rv.data


def test_messages(client):
    """Ensure that user can post messages"""
    login(client, app.config["USERNAME"], app.config["PASSWORD"])
    rv = client.post(
        "/add",
        data=dict(title="<Hello>", text="<strong>HTML</strong> allowed here"),
        follow_redirects=True,
    )
    assert b"No entries here so far" not in rv.data
    assert b"&lt;Hello&gt;" in rv.data
    assert b"<strong>HTML</strong> allowed here" in rv.data


def test_add_requires_login(client):
    """Ensure a logged out user cannot add a post"""
    rv = add_post(client, "Sneaky", "Not logged in")
    assert rv.status_code == 401
    rv = client.get("/")
    assert b"Sneaky" not in rv.data


def test_delete_message(client):
    """Ensure the messages are being deleted"""
    rv = client.get("/delete/1")
    data = json.loads(rv.data)
    assert data["status"] == 0
    login(client, app.config["USERNAME"], app.config["PASSWORD"])
    rv = client.get("/delete/1")
    data = json.loads(rv.data)
    assert data["status"] == 1


def test_delete_requires_login(client):
    """Ensure a logged out user gets a 401 and the post is kept"""
    login(client, app.config["USERNAME"], app.config["PASSWORD"])
    add_post(client, "Keep me", "Still here")
    logout(client)
    rv = client.get("/delete/1")
    assert rv.status_code == 401
    assert json.loads(rv.data) == {"status": 0, "message": "Please log in."}
    rv = client.get("/")
    assert b"Keep me" in rv.data


def test_delete_removes_post(client):
    """Ensure a logged in user's delete removes the post"""
    login(client, app.config["USERNAME"], app.config["PASSWORD"])
    add_post(client, "Delete me", "Gone soon")
    rv = client.get("/delete/1")
    assert json.loads(rv.data)["status"] == 1
    rv = client.get("/")
    assert b"Delete me" not in rv.data
    assert b"No entries yet. Add some!" in rv.data


def add_post(client, title, text):
    """Add post helper function"""
    return client.post(
        "/add",
        data=dict(title=title, text=text),
        follow_redirects=True,
    )


def test_index_links_to_search(client):
    """Ensure the index page has a link to the search page"""
    rv = client.get("/")
    assert b'href="/search/"' in rv.data


def test_search_page(client):
    """Ensure the search page loads with a search box"""
    rv = client.get("/search/")
    assert rv.status_code == 200
    assert b'name="query"' in rv.data


def test_search_by_title(client):
    """Ensure search returns posts whose title matches, ignoring case"""
    login(client, app.config["USERNAME"], app.config["PASSWORD"])
    add_post(client, "Flask tips", "Use blueprints")
    add_post(client, "Pasta", "Boil the water")
    rv = client.get("/search/?query=flask")
    assert b"Flask tips" in rv.data
    assert b"Pasta" not in rv.data


def test_search_by_text(client):
    """Ensure search also matches the post text"""
    login(client, app.config["USERNAME"], app.config["PASSWORD"])
    add_post(client, "Flask tips", "Use blueprints")
    add_post(client, "Pasta", "Boil the water")
    rv = client.get("/search/?query=WATER")
    assert b"Pasta" in rv.data
    assert b"Flask tips" not in rv.data


def test_search_results_have_post_id(client):
    """Ensure search results carry the post id that main.js deletes by"""
    login(client, app.config["USERNAME"], app.config["PASSWORD"])
    add_post(client, "Flask tips", "Use blueprints")
    rv = client.get("/search/?query=flask")
    assert b'<h2 id="1">Flask tips</h2>' in rv.data


def test_postgres_url_is_rewritten():
    """Ensure a postgres:// DATABASE_URL is changed to postgresql://"""
    # run in a new process, since the URL is read when project.app is imported
    env = {**os.environ, "DATABASE_URL": "postgres://user:pw@host:5432/flaskr"}
    code = "from project.app import app; print(app.config['SQLALCHEMY_DATABASE_URI'])"
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=BASE_DIR,
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "postgresql://user:pw@host:5432/flaskr"
