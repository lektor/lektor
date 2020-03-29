import PropTypes from 'prop-types'
import i18n from '../i18n'

function ValidationFailure (options) {
  this.message = options.message || i18n.trans('INVALID_INPUT')
  this.type = options.type || 'error'
}

export const widgetPropTypes = {
  value: PropTypes.any,
  type: PropTypes.object,
  placeholder: PropTypes.any,
  onChange: PropTypes.func
}

export function getInputClass (type) {
  let rv = 'form-control'
  if (type.size === 'small') {
    rv = 'input-sm ' + rv
  } else if (type.size === 'large') {
    rv = 'input-lg ' + rv
  }
  return rv
}

const BasicWidgetMixin = {
  propTypes: widgetPropTypes,

  getInputClass () {
    return getInputClass(this.props.type)
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
