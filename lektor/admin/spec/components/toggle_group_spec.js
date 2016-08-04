import ToggleGroup from '../../static/js/components/ToggleGroup';
import jsdomify from 'jsdomify';
let React, ReactDOM, ReactTestUtils;

describe('ToggleGroup', () => {
  beforeEach(() => {
    jsdomify.create('<!DOCTYPE html><html><head></head><body><div id="container"></div></body></html>');
    React = require('react');
    ReactDOM = require('react-dom');
    ReactTestUtils = require('react-addons-test-utils')
  });

  afterEach(() => {
    jsdomify.destroy();
  });

  describe('when rendered with defaults', () => {
    beforeEach(() => {
      ReactDOM.render(
        <ToggleGroup>
          <div>Rick Astley rulz</div>
        </ToggleGroup>,
        document.getElementById('container')
      );
    });

    it('renders a closed toggle group', () => {
      expect(document.getElementById('container').innerHTML).toContain('toggle-group-closed');
    });

    describe('when toggled', () => {
      beforeEach(() => {
        ReactTestUtils.Simulate.click(document.querySelector('.toggle'));
      });

      it('renders an open toggle group', () => {
        expect(document.getElementById('container').innerHTML).toContain('toggle-group-open');
      });
    });
  });

  describe('when rendered with a default visibility of true', () => {
    beforeEach(() => {
      ReactDOM.render(
        <ToggleGroup defaultVisibility={true}>
          <div>Rick Astley rulz</div>
        </ToggleGroup>,
        document.getElementById('container')
      );
    });

    it('renders an open toggle group', () => {
      expect(document.getElementById('container').innerHTML).toContain('toggle-group-open');
    });
  });
});
