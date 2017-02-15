import React from 'react'
import i18n from '../i18n'

const ValidationFailure = (options) => {
  this.message = options.message || i18n.trans('INVALID_INPUT')
  this.type = options.type || 'error'
}

const BasicWidgetMixin = {
  propTypes: {
    value: React.PropTypes.any,
    type: React.PropTypes.object,
    placeholder: React.PropTypes.any,
    onChange: React.PropTypes.func
  },

  getInputClass () {
    let rv = 'form-control'
    if (this.props.type.size === 'small') {
      rv = 'input-sm ' + rv
    } else if (this.props.type.size === 'large') {
      rv = 'input-lg ' + rv
    }
    return rv
  },

  getValidationFailure () {
    if (this.getValidationFailureImpl) {
      return this.getValidationFailureImpl()
    }
    return null
  }
}

export {
  ValidationFailure,
  BasicWidgetMixin
}
