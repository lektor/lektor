'use strict'

import React from 'react'
import utils from '../utils'
import i18n from '../i18n'
import {BasicWidgetMixin} from './mixins'

const CheckboxesInputWidget = React.createClass({
  mixins: [BasicWidgetMixin],

  statics: {
    deserializeValue: (value) => {
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
    },

    serializeValue: (value) => {
      return (value || '').join(', ')
    }
  },

  onChange: function (field, event) {
    const newValue = utils.flipSetValue(this.props.value,
                                      field, event.target.checked)
    if (this.props.onChange) {
      this.props.onChange(newValue)
    }
  },

  isActive: function (field) {
    let value = this.props.value
    if (value == null) {
      value = this.props.placeholder
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
  },

  render () {
    let {className, value, placeholder, type, ...otherProps} = this.props  // eslint-disable-line no-unused-vars
    className = (className || '') + ' checkbox'

    const choices = this.props.type.choices.map((item) => {
      return (
        <div className={className} key={item[0]}>
          <label>
            <input type='checkbox'
              {...otherProps}
              checked={this.isActive(item[0])}
              onChange={this.onChange.bind(this, item[0])} />
            {i18n.trans(item[1])}
          </label>
        </div>
      )
    })
    return (
      <div className='checkboxes'>
        {choices}
      </div>
    )
  }
})

const SelectInputWidget = React.createClass({
  mixins: [BasicWidgetMixin],

  onChange (event) {
    this.props.onChange(event.target.value)
  },

  render () {
    let {className, type, value, placeholder, onChange, ...otherProps} = this.props  // eslint-disable-line no-unused-vars
    value = value || placeholder

    let choices = this.props.type.choices.map((item) => {
      return (
        <option key={item[0]} value={item[0]}>
          {i18n.trans(item[1])}
        </option>
      )
    })
    choices.unshift(
      <option key='' value=''>{'----'}</option>
    )

    return (
      <div className='form-group'>
        <div className={className}>
          <select
            className={this.getInputClass()}
            onChange={onChange ? this.onChange : null}
            value={value}
            {...otherProps}>
            {choices}
          </select>
        </div>
      </div>
    )
  }
})

export default {
  CheckboxesInputWidget: CheckboxesInputWidget,
  SelectInputWidget: SelectInputWidget
}
