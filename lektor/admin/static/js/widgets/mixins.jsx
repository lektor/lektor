import PropTypes from 'prop-types'
import i18n from '../i18n'

function ValidationFailure (options) {
  this.message = options.message || i18n.trans('INVALID_INPUT')
  this.type = options.type || 'error'
}

const BasicWidgetMixin = {
  propTypes: {
    value: PropTypes.any,
    type: PropTypes.object,
    placeholder: PropTypes.any,
    onChange: PropTypes.func
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
