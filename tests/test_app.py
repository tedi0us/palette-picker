import exporters
import presets


def test_index_renders(client):
    r = client.get("/")
    assert r.status_code == 200
    assert b"htmx" in r.data


def test_healthz(client):
    assert client.get("/healthz").status_code == 200


def test_planner_and_admin_render(client):
    assert client.get("/plan").status_code == 200
    assert client.get("/admin").status_code == 200


def test_every_export_format_renders():
    scheme = presets.default_scheme()
    for fmt in exporters.FORMATS:
        out = exporters.render(fmt, scheme)
        assert out.strip(), fmt
