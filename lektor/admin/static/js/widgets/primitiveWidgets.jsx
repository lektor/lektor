'use strict'

import React from 'react'
import { ValidationFailure, getInputClass, widgetPropTypes } from './mixins'
import { isValidUrl } from '../utils'
import userLabel from '../userLabel'
import i18n from '../i18n'

const isTrue = (value) => {
  return value === 'true' || value === 'yes' || value === '1'
}

const isValidDate = (year, month, day) => {
  year = parseInt(year, 10)
  month = parseInt(month, 10)
  day = parseInt(day, 10)
  const date = new Date(year, month - 1, day)
  if (date.getFullYear() === year &&
      date.getMonth() === month - 1 &&
      date.getDate() === day) {
    return true
  }
  return false
}

function InputWidgetBase (props) {
  let { type, value, onChange, className, postprocessValue, inputAddon, inputType, validate, ...otherProps } = props
  let help = null
  let failure = null
  if (validate) {
    failure = validate(props.value)
  }
  className = (className || '')
  className += ' input-group'
  function onChangeHandler (event) {
    let value = event.target.value
    if (postprocessValue) {
      value = postprocessValue(value)
    }
    onChange(value)
  }

  if (failure !== null) {
    className += ' has-feedback has-' + failure.type
    const valClassName = 'validation-block validation-block-' + failure.type
    help = <div className={valClassName}>{failure.message}</div>
  }

  let addon = null
  const configuredAddon = type.addon_label_i18n
  if (configuredAddon) {
    addon = userLabel.format(configuredAddon)
  } else if (inputAddon) {
    addon = inputAddon
  }

  return (
    <div className='form-group'>
      <div className={className}>
        <input
          type={inputType}
          className={getInputClass(type)}
          onChange={onChangeHandler}
          value={value || ''}
          {...otherProps}
        />
        {addon ? <span className='input-group-addon'>{addon}</span> : null}
      </div>
      {help}
    </div>
  )
}

export function SingleLineTextInputWidget (props) {
  return <InputWidgetBase inputType='text' inputAddon={<i className='fa fa-paragraph' />} {...props} />
}
SingleLineTextInputWidget.propTypes = widgetPropTypes

function postprocessSlug (value) {
  return value.replace(/\s+/g, '-')
}

export function SlugInputWidget (props) {
  return <InputWidgetBase inputType='text' inputAddon={<i className='fa fa-link' />} postprocessValue={postprocessSlug} {...props} />
}
SlugInputWidget.propTypes = widgetPropTypes

function postprocessInteger (value) {
  return value.match(/^\s*(.*?)\s*$/)[1]
}

function validateInteger (value) {
  if (value && !value.match(/^-?\d+$/)) {
    return new ValidationFailure({
      message: i18n.trans('ERROR_INVALID_NUMBER')
    })
  }
  return null
}

export function IntegerInputWidget (props) {
  return <InputWidgetBase inputType='text' inputAddon='0' postprocessValue={postprocessInteger} validate={validateInteger} {...props} />
}
IntegerInputWidget.propTypes = widgetPropTypes

function postprocessFloat (value) {
  return value.match(/^\s*(.*?)\s*$/)[1]
}

function validateFloat (value) {
  if (value && isNaN(parseFloat(value))) {
    return new ValidationFailure({
      message: i18n.trans('ERROR_INVALID_NUMBER')
    })
  }
  return null
}

export function FloatInputWidget (props) {
  return <InputWidgetBase inputType='text' inputAddon='0.0' postprocessValue={postprocessFloat} validate={validateFloat} {...props} />
}
FloatInputWidget.propTypes = widgetPropTypes

function postprocessDate (value) {
  value = value.match(/^\s*(.*?)\s*$/)[1]
  const match = value.match(/^(\d{1,2})\.(\d{1,2})\.(\d{4})\s*$/)
  let day, month, year
  if (match) {
    day = parseInt(match[1], 10)
    month = parseInt(match[2], 10)
    year = parseInt(match[3], 10)
    return (
      year + '-' +
      (month < 10 ? '0' : '') + month + '-' +
      (day < 10 ? '0' : '') + day
    )
  }
  return value
}

function validateDate (value) {
  if (!value) {
    return null
  }

  const match = value.match(/^\s*(\d{4})-(\d{1,2})-(\d{1,2})\s*$/)
  if (match && isValidDate(match[1], match[2], match[3])) {
    return null
  }

  return new ValidationFailure({
    message: i18n.trans('ERROR_INVALID_DATE')
  })
}

export function DateInputWidget (props) {
  return <InputWidgetBase inputType='date' inputAddon={<i className='fa fa-calendar' />} postprocessValue={postprocessDate} validate={validateDate} {...props} />
}
DateInputWidget.propTypes = widgetPropTypes

function validateUrl (value) {
  if (value && !isValidUrl(value)) {
    return new ValidationFailure({
      message: i18n.trans('ERROR_INVALID_URL')
    })
  }
  return null
}

export function UrlInputWidget (props) {
  return <InputWidgetBase inputType='text' inputAddon={<i className='fa fa-external-link' />} validate={validateUrl} {...props} />
}
UrlInputWidget.propTypes = widgetPropTypes

export class MultiLineTextInputWidget extends React.Component {
  constructor (props) {
    super(props)
    this.recalculateSize = this.recalculateSize.bind(this)
  }

  onChange (event) {
    this.recalculateSize()
    if (this.props.onChange) {
      this.props.onChange(event.target.value)
    }
  }

  componentDidMount () {
    this.recalculateSize()
    window.addEventListener('resize', this.recalculateSize)
  }

  componentWillUnmount () {
    window.removeEventListener('resize', this.recalculateSize)
  }

  componentDidUpdate (prevProps) {
    this.recalculateSize()
  }

  isInAutoResizeMode () {
    return this.props.rows === undefined
  }

  recalculateSize () {
    if (!this.isInAutoResizeMode()) {
      return
    }
    let diff
    const node = this.refs.ta

    if (window.getComputedStyle) {
      const s = window.getComputedStyle(node)
      if (s.getPropertyValue('box-sizing') === 'border-box' ||
          s.getPropertyValue('-moz-box-sizing') === 'border-box' ||
          s.getPropertyValue('-webkit-box-sizing') === 'border-box') {
        diff = 0
      } else {
        diff = (
          parseInt(s.getPropertyValue('padding-bottom') || 0, 10) +
          parseInt(s.getPropertyValue('padding-top') || 0, 10)
        )
      }
    } else {
      diff = 0
    }

    const updateScrollPosition = node === document.activeElement
    // Cross-browser compatibility for scroll position
    const oldScrollTop = document.documentElement.scrollTop || document.body.scrollTop
    const oldHeight = node.offsetHeight

    node.style.height = 'auto'
    const newHeight = (node.scrollHeight - diff)
    node.style.height = newHeight + 'px'

    if (updateScrollPosition) {
      window.scrollTo(
        document.body.scrollLeft, oldScrollTop + (newHeight - oldHeight))
    }
  }

  render () {
    let { className, type, onChange, style, ...otherProps } = this.props
    className = (className || '')

    style = style || {}
    if (this.isInAutoResizeMode()) {
      style.display = 'block'
      style.overflow = 'hidden'
      style.resize = 'none'
    }

    return (
      <div className={className}>
        <textarea
          ref='ta'
          className={getInputClass(type)}
          onChange={this.onChange.bind(this)}
          style={style}
          {...otherProps}
        />
      </div>
    )
  }
}
MultiLineTextInputWidget.propTypes = widgetPropTypes

export class BooleanInputWidget extends React.Component {
  onChange (event) {
    this.props.onChange(event.target.checked ? 'yes' : 'no')
  }

  componentDidMount () {
    const checkbox = this.refs.checkbox
    if (!this.props.value && this.props.placeholder) {
      checkbox.indeterminate = true
      checkbox.checked = isTrue(this.props.placeholder)
    } else {
      checkbox.indeterminate = false
    }
  }

  render () {
    let { className, type, placeholder, onChange, value, ...otherProps } = this.props
    className = (className || '') + ' checkbox'

    return (
      <div className={className}>
        <label>
          <input
            type='checkbox'
            {...otherProps}
            ref='checkbox'
            checked={isTrue(value)}
            onChange={onChange ? this.onChange.bind(this) : undefined}
          />
          {type.checkbox_label_i18n ? i18n.trans(type.checkbox_label_i18n) : null}
        </label>
      </div>
    )
  }
}
BooleanInputWidget.propTypes = widgetPropTypes
