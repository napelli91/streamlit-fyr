from unittest.mock import MagicMock

from streamlit_fyr.dashboard import make_dashboard_page


def test_make_dashboard_page_returns_callable():
    backend = MagicMock()
    page_fn = make_dashboard_page(backend)
    assert callable(page_fn)


def test_make_dashboard_page_closes_over_backend():
    """Each backend gets its own page function."""
    backend_a = MagicMock()
    backend_b = MagicMock()
    assert make_dashboard_page(backend_a) is not make_dashboard_page(backend_b)
