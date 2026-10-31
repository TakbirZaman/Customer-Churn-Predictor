from pathlib import Path
from streamlit.testing.v1 import AppTest


def test_ui_demo_and_new_session(tmp_path,monkeypatch):
    monkeypatch.setenv('ANALYST_HOME',str(tmp_path))
    monkeypatch.setenv('PROVIDER_ORDER','')
    app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py')).run(timeout=30)
    assert not app.exception
    button=next(b for b in app.button if 'complete sample' in b.label)
    button.click().run(timeout=30)
    assert not app.exception
    assert any('63,000' in m.value for m in app.markdown)
    old=app.session_state['sid']
    next(b for b in app.button if 'New analysis' in b.label).click().run(timeout=30)
    assert not app.exception
    assert app.session_state['sid']!=old
