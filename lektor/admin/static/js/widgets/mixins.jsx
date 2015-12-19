var React = require('react');

var i18n = require('../i18n');


function ValidationFailure(options) {
  this.message = options.message || i18n.trans('INVALID_INPUT');
  this.type = options.type || 'error';
}

var BasicWidgetMixin = {
  propTypes: {
    value: React.PropTypes.any,
    type: React.PropTypes.object,
    placeholder: React.PropTypes.any,
    onChange: React.PropTypes.func
  },

  getInputClass() {
    var rv = 'form-control';
    if (this.props.type.size === 'small') {
      rv = 'input-sm ' + rv;
    } else if (this.props.type.size === 'large') {
      rv = 'input-lg ' + rv;
    }
    return rv;
  },

  getValidationFailure: function() {
    if (this.getValidationFailureImpl) {
      return this.getValidationFailureImpl();
    }
    return null;
  }
}


module.exports = {
  ValidationFailure: ValidationFailure,
  BasicWidgetMixin: BasicWidgetMixin
};
