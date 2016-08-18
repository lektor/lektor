import pytest
import mock
import sys

from lektor.admin.webui import WebUI

@pytest.yield_fixture(scope='function')
def app(mocker, scratch_env, simple_http_server):
    mocker.patch("lektor.publisher.RsyncPublisher.publish")
    yield WebUI(scratch_env, output_path=simple_http_server.document_root)


@pytest.mark.skipif(sys.version_info > (3,0),
                    reason="python 3 currently not compatible pytest plugin")
def test_publication(live_server, browser, simple_http_server):
    test_server = live_server.url()

    browser.visit(test_server)
    browser.find_by_css('#lektor-edit-link').click()
    assert browser.title == 'Lektor Admin'

    browser.find_by_css('.form-control').fill('Melissa is cool')
    browser.find_by_css('.btn-primary').click()

    browser.find_by_css('.fa-cloud-upload').click()
    assert browser.is_text_present('publish the current version of the website', wait_time=1)

    browser.find_by_css('.actions .btn-primary').click()
    assert browser.is_text_present('Status: Publishing done', wait_time=1)

    browser.visit('http://0.0.0.0:{port}'.format(port=simple_http_server.port))
    assert browser.is_text_present('Melissa is cool', wait_time=1)
