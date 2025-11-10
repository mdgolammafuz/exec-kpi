from backend.main import app

def test_healthz_route_exists():
    # verify FastAPI has the route
    routes = {r.path for r in app.routes}
    assert "/healthz" in routes
