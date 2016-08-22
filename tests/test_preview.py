import pytest
from lektor.admin.webui import WebUI

@pytest.yield_fixture(scope='function')
def app(request, env, pad, simple_http_server):
    yield WebUI(env, output_path=simple_http_server.document_root)

def test_preview(live_server, browser):
    browser.visit('%s/dir_with_index_html' % live_server.url())
    assert browser.url == '%s/dir_with_index_html/' % live_server.url()

    browser.visit('%s/dir_with_index_htm' % live_server.url())
    assert browser.url == '%s/dir_with_index_htm/' % live_server.url()

    browser.visit('%s/dir_with_index_htm/index.htm' % live_server.url())
    assert browser.url == '%s/dir_with_index_htm/index.htm' % live_server.url()

    browser.visit('%s/empty' % live_server.url())
    assert browser.is_text_present('Not Found', wait_time=1)

    browser.visit('%s/doesnt_exist' % live_server.url())
    assert browser.is_text_present('Not Found', wait_time=1)
