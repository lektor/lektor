import pytest

from lektor.admin.webui import WebUI
from lektor.publisher import RsyncPublisher

@pytest.yield_fixture(scope='function')
def app(request, scratch_env, pad, simple_http_server):
    original_publish = RsyncPublisher.publish
    def fake_publish(self, target_url, credentials=None, **extra):
        pass
    RsyncPublisher.publish = fake_publish
    try:
        yield WebUI(scratch_env, output_path=simple_http_server.document_root)
    finally:
        RsyncPublisher.publish = original_publish

def test_publication(live_server, browser, simple_http_server):
    browser.visit(live_server.url())
    browser.find_by_css('#lektor-edit-link').click()
    assert browser.title == 'Lektor Admin'

    browser.find_by_css('.form-control').fill('Melissa is cool')
    browser.find_by_css('.btn-primary').click()

    browser.find_by_css('.fa-cloud-upload').click()
    assert browser.is_text_present('publish the current version of the website', wait_time=1)

    browser.find_by_css('.actions .btn-primary').click()
    assert browser.is_text_present('Status: Publishing done', wait_time=1)

    browser.visit('http://0.0.0.0:%d' % simple_http_server.port)
    assert browser.is_text_present('Melissa is cool', wait_time=1)
