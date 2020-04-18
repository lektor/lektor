'use strict'

import { widgetPropTypes } from './mixins'
import React from 'react'
import i18n from '../i18n'

export function LineWidget () {
  return <hr />
}
LineWidget.isFakeWidget = true
LineWidget.propTypes = widgetPropTypes

export function SpacingWidget () {
  return <div className='spacing' />
}
SpacingWidget.isFakeWidget = true
SpacingWidget.propTypes = widgetPropTypes

export function InfoWidget (props) {
  const label = i18n.trans(props.field.label_i18n)
  return (
    <div className='info'>
      <p>
        {label ? <strong>{label + ': '}</strong> : null}
        {i18n.trans(props.field.description_i18n)}
      </p>
    </div>
  )
}
InfoWidget.isFakeWidget = true
InfoWidget.propTypes = widgetPropTypes

export function HeadingWidget (props) {
  return (
    <h3>{i18n.trans(props.type.heading_i18n)}</h3>
  )
}
HeadingWidget.isFakeWidget = true
HeadingWidget.propTypes = widgetPropTypes
