import json
from contextlib import asynccontextmanager

import pytest

from nativestore import App


def test_real_flask_forms_and_cookies(project):
    flask = pytest.importorskip("flask")
    application = flask.Flask(__name__)

    @application.post("/submit")
    def submit():
        reply = flask.make_response({"name": flask.request.form["name"]})
        reply.set_cookie("first", "one")
        reply.set_cookie("second", "two")
        return reply

    app = App(root=project)
    app.mount_wsgi(application, prefix="/legacy")
    try:
        result = app.dispatch(
            "/legacy/submit",
            method="POST",
            raw_body=b"name=Ada",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert result.status == 200
        assert json.loads(result.body) == {"name": "Ada"}
        assert len([v for k, v in result.headers if k.lower() == "set-cookie"]) == 2
        assert app.dispatch("/legacy/missing").status == 404
    finally:
        app.close()


def test_real_fastapi_lifespan_body_and_validation(project):
    fastapi = pytest.importorskip("fastapi")
    events = []

    @asynccontextmanager
    async def lifespan(application):
        events.append("startup")
        yield
        events.append("shutdown")

    application = fastapi.FastAPI(lifespan=lifespan)

    @application.post("/items")
    async def items(value: int):
        return {"value": value}

    app = App(root=project)
    app.mount_asgi(application, prefix="/backend")
    try:
        assert events == ["startup"]
        result = app.dispatch("/backend/items", method="POST", query={"value": ["12"]})
        assert result.status == 200
        assert json.loads(result.body) == {"value": 12}
        assert app.dispatch("/backend/items", method="POST").status == 422
    finally:
        app.close()
    assert events == ["startup", "shutdown"]


def test_failed_asgi_startup_closes_loop(project):
    async def application(scope, receive, send):
        raise RuntimeError("startup rejected")

    from nativestore.errors import NativeStoreError

    app = App(root=project)
    try:
        with pytest.raises(NativeStoreError, match="startup"):
            app.mount_asgi(application)
    finally:
        app.close()
