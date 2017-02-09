'use strict'

import React from 'react'
import jQuery from 'jquery'
import {BasicWidgetMixin, ValidationFailure} from './mixins'
import utils from '../utils'
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

const InputWidgetMixin = {
  mixins: [BasicWidgetMixin],

  onChange (event) {
    let value = event.target.value
    if (this.postprocessValue) {
      value = this.postprocessValue(value)
    }
    this.props.onChange(value)
  },

  render () {
    let {type, onChange, className, ...otherProps} = this.props
    let help = null
    const failure = this.getValidationFailure()
    className = (className || '')
    className += ' input-group'

    if (failure !== null) {
      className += ' has-feedback has-' + failure.type
      const valClassName = 'validation-block validation-block-' + failure.type
      help = <div className={valClassName}>{failure.message}</div>
    }

    let addon = null
    const configuredAddon = type.addon_label_i18n
    if (configuredAddon) {
      addon = userLabel.format(configuredAddon)
    } else if (this.getInputAddon) {
      addon = this.getInputAddon()
    }

    return (
      <div className='form-group'>
        <div className={className}>
          <input
            type={this.getInputType()}
            className={this.getInputClass()}
            onChange={onChange ? this.onChange : undefined}
            {...otherProps} />
          {addon ? <span className='input-group-addon'>{addon}</span> : null}
        </div>
        {help}
      </div>
    )
  }
}

const SingleLineTextInputWidget = React.createClass({
  mixins: [InputWidgetMixin],

  getInputType () {
    return 'text'
  },

  getInputAddon () {
    return <i className='fa fa-paragraph' />
  }
})

const SlugInputWidget = React.createClass({
  mixins: [InputWidgetMixin],

  postprocessValue (value) {
    return value.replace(/\s+/g, '-')
  },

  getInputType () {
    return 'text'
  },

  getInputAddon () {
    return <i className='fa fa-link' />
  }
})

const IntegerInputWidget = React.createClass({
  mixins: [InputWidgetMixin],

  postprocessValue (value) {
    return value.match(/^\s*(.*?)\s*$/)[1]
  },

  getValidationFailureImpl () {
    if (this.props.value && !this.props.value.match(/^\d+$/)) {
      return new ValidationFailure({
        message: i18n.trans('ERROR_INVALID_NUMBER')
      })
    }
    return null
  },

  getInputType () {
    return 'text'
  },

  getInputAddon () {
    return '0'
  }
})

const FloatInputWidget = React.createClass({
  mixins: [InputWidgetMixin],

  postprocessValue (value) {
    return value.match(/^\s*(.*?)\s*$/)[1]
  },

  getValidationFailureImpl () {
    if (this.props.value && isNaN(parseFloat(this.props.value))) {
      return new ValidationFailure({
        message: i18n.trans('ERROR_INVALID_NUMBER')
      })
    }
    return null
  },

  getInputType () {
    return 'text'
  },

  getInputAddon () {
    return '0.0'
  }
})

const DateInputWidget = React.createClass({
  mixins: [InputWidgetMixin],

  postprocessValue (value) {
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
  },

  getValidationFailureImpl () {
    if (!this.props.value) {
      return null
    }

    const match = this.props.value.match(/^\s*(\d{4})-(\d{1,2})-(\d{1,2})\s*$/)
    if (match && isValidDate(match[1], match[2], match[3])) {
      return null
    }

    return new ValidationFailure({
      message: i18n.trans('ERROR_INVALID_DATE')
    })
  },

  getInputType () {
    return 'date'
  },

  getInputAddon () {
    return <i className='fa fa-calendar' />
  }
})

const UrlInputWidget = React.createClass({
  mixins: [InputWidgetMixin],

  getValidationFailureImpl () {
    if (this.props.value && !utils.isValidUrl(this.props.value)) {
      return new ValidationFailure({
        message: i18n.trans('ERROR_INVALID_URL')
      })
    }
    return null
  },

  getInputType () {
    return 'text'
  },

  getInputAddon () {
    return <i className='fa fa-external-link' />
  }
})

const MultiLineTextInputWidget = React.createClass({
  mixins: [BasicWidgetMixin],

  onChange (event) {
    this.recalculateSize()
    if (this.props.onChange) {
      this.props.onChange(event.target.value)
    }
  },

  componentDidMount () {
    this.recalculateSize()
    window.addEventListener('resize', this.recalculateSize)
  },

  componentWillUnmount () {
    window.removeEventListener('resize', this.recalculateSize)
  },

  componentDidUpdate (prevProps) {
    this.recalculateSize()
  },

  isInAutoResizeMode () {
    return this.props.rows === undefined
  },

  recalculateSize () {
    if (!this.isInAutoResizeMode()) {
      return
    }
    let diff
    let node = this.refs.ta

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

    const updateScrollPosition = jQuery(node).is(':focus')
    // Cross-browser compatibility for scroll position
    const oldScrollTop = document.documentElement.scrollTop || document.body.scrollTop
    const oldHeight = jQuery(node).outerHeight()

    node.style.height = 'auto'
    const newHeight = (node.scrollHeight - diff)
    node.style.height = newHeight + 'px'

    if (updateScrollPosition) {
      window.scrollTo(
        document.body.scrollLeft, oldScrollTop + (newHeight - oldHeight))
    }
  },

  render () {
    let {className, type, onChange, style, ...otherProps} = this.props  // eslint-disable-line no-unused-vars
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
          className={this.getInputClass()}
          onChange={onChange ? this.onChange : undefined}
          style={style}
          {...otherProps} />
      </div>
    )
  }
})

const BooleanInputWidget = React.createClass({
  mixins: [BasicWidgetMixin],

  onChange (event) {
    this.props.onChange(event.target.checked ? 'yes' : 'no')
  },

  componentDidMount () {
    const checkbox = this.refs.checkbox
    if (!this.props.value && this.props.placeholder) {
      checkbox.indeterminate = true
      checkbox.checked = isTrue(this.props.placeholder)
    } else {
      checkbox.indeterminate = false
    }
  },

  render () {
    let {className, type, placeholder, onChange, value, ...otherProps} = this.props  // eslint-disable-line no-unused-vars
    className = (className || '') + ' checkbox'

    return (
      <div className={className}>
        <label>
          <input type='checkbox'
            {...otherProps}
            ref='checkbox'
            checked={isTrue(value)}
            onChange={onChange ? this.onChange : undefined} />
          {type.checkbox_label_i18n ? i18n.trans(type.checkbox_label_i18n) : null}
        </label>
      </div>
    )
  }
})

export default {
  SingleLineTextInputWidget: SingleLineTextInputWidget,
  SlugInputWidget: SlugInputWidget,
  IntegerInputWidget: IntegerInputWidget,
  FloatInputWidget: FloatInputWidget,
  DateInputWidget: DateInputWidget,
  UrlInputWidget: UrlInputWidget,
  MultiLineTextInputWidget: MultiLineTextInputWidget,
  BooleanInputWidget: BooleanInputWidget
}
