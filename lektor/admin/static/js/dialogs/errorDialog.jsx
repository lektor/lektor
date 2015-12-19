'use strict';

var React = require('react');

var RecordComponent = require('../components/RecordComponent');
var SlideDialog = require('../components/SlideDialog');
var dialogSystem = require('../dialogSystem');
var i18n = require('../i18n');


class ErrorDialog extends RecordComponent {

  onClose() {
    dialogSystem.dismissDialog();
  }

  render() {
    return (
      <SlideDialog
        hasCloseButton={true}
        closeOnEscape={true}
        title={i18n.trans('ERROR')}>
        <p>
          {i18n.trans('ERROR_OCURRED')}{': '}
          {i18n.trans('ERROR_' + this.props.error.code)}
        </p>
        <div className="actions">
          <button type="submit" className="btn btn-primary"
            onClick={this.onClose.bind(this)}>{i18n.trans('CLOSE')}</button>
        </div>
      </SlideDialog>
    );
  }
}

ErrorDialog.propTypes = {
  error: React.PropTypes.object
}

module.exports = ErrorDialog;
