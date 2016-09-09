import pytest
import mock

from lektor.admin.webui import WebUI

@pytest.yield_fixture(scope='function')
def app(scratch_env, simple_http_server):
    yield WebUI(scratch_env, output_path=simple_http_server.document_root)

def test_preview(live_server, browser):
    test_server = live_server.url()
    
    browser.visit('{url}/dir_with_index_html'.format(url=test_server))
    assert browser.url == '{url}/dir_with_index_html'.format(url=test_server)

    browser.visit('{url}/dir_with_index_htm/'.format(url=test_server))
    assert browser.url == '{url}/dir_with_index_htm/'.format(url=test_server)

    browser.visit('{url}/dir_with_index_htm/index.htm'.format(url=test_server))
    assert browser.url == '{url}/dir_with_index_htm/index.htm'.format(url=test_server)

    browser.visit('{url}/empty'.format(url=test_server))
    assert browser.is_text_present('Not Found', wait_time=2)

    browser.visit('{url}/doesnt_exist'.format(url=test_server))
    assert browser.is_text_present('Not Found', wait_time=2)
