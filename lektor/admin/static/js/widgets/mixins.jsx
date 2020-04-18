import PropTypes from 'prop-types'
import i18n from '../i18n'

export function ValidationFailure (options) {
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
