'use strict'

import PropTypes from 'prop-types'
import React from 'react'
import {BasicWidgetMixin} from './mixins'
import i18n from '../i18n'

const FakeWidgetMixin = {
  mixins: [BasicWidgetMixin],
  propTypes: {
    field: PropTypes.any
  },

  statics: {
    isFakeWidget: true
  }
}

const LineWidget = React.createClass({
  mixins: [FakeWidgetMixin],

  render () {
    return <hr />
  }
})

const SpacingWidget = React.createClass({
  mixins: [FakeWidgetMixin],

  render () {
    return <div className='spacing' />
  }
})

const InfoWidget = React.createClass({
  mixins: [FakeWidgetMixin],

  render () {
    const label = i18n.trans(this.props.field.label_i18n)
    return (
      <div className='info'>
        <p>
          {label ? <strong>{label + ': '}</strong> : null}
          {i18n.trans(this.props.field.description_i18n)}
        </p>
      </div>
    )
  }
})

const HeadingWidget = React.createClass({
  mixins: [FakeWidgetMixin],

  render () {
    return (
      <h3>{i18n.trans(this.props.type.heading_i18n)}</h3>
    )
  }
})

export default {
  LineWidget: LineWidget,
  SpacingWidget: SpacingWidget,
  InfoWidget: InfoWidget,
  HeadingWidget: HeadingWidget
}
