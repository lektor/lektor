'use strict'

import React from 'react'
import { flipSetValue } from '../utils'
import i18n from '../i18n'
import { getInputClass, widgetPropTypes } from './mixins'

function checkboxIsActive (field, props) {
  let value = props.value
  if (value == null) {
    value = props.placeholder
    if (value == null) {
      return false
    }
  }
  for (const item of value) {
    if (item === field) {
      return true
    }
  }
  return false
}

export class CheckboxesInputWidget extends React.PureComponent {
  static serializeValue (value) {
    return (value || '').join(', ')
  }

  static deserializeValue (value) {
    if (value === '') {
      return null
    }
    let rv = value.split(',').map((x) => {
      return x.match(/^\s*(.*?)\s*$/)[1]
    })
    if (rv.length === 1 && rv[0] === '') {
      rv = []
    }
    return rv
  }

  render () {
    let { className, value, placeholder, type, onChange, ...otherProps } = this.props
    className = (className || '') + ' checkbox'

    function onChangeHandler (field, event) {
      const newValue = flipSetValue(this.props.value, field, event.target.checked)
      onChange(newValue)
    }

    const choices = type.choices.map((item) => (
      <div className={className} key={item[0]}>
        <label>
          <input
            type='checkbox'
            {...otherProps}
            checked={checkboxIsActive(item[0], this.props)}
            onChange={(e) => onChangeHandler(item[0], e)}
          />
          {i18n.trans(item[1])}
        </label>
      </div>
    ))
    return (
      <div className='checkboxes'>
        {choices}
      </div>
    )
  }
}
CheckboxesInputWidget.propTypes = widgetPropTypes

export function SelectInputWidget (props) {
  const { className, type, value, placeholder, onChange, ...otherProps } = props

  const choices = type.choices.map((item) => (
    <option key={item[0]} value={item[0]}>
      {i18n.trans(item[1])}
    </option>
  ))

  return (
    <div className='form-group'>
      <div className={className}>
        <select
          className={getInputClass(type)}
          value={value || placeholder || ''}
          onChange={(e) => onChange(e.target.value)}
          {...otherProps}
        >
          <option key='' value=''>----</option>
          {choices}
        </select>
      </div>
    </div>
  )
}
SelectInputWidget.propTypes = widgetPropTypes
