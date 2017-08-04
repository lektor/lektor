'use strict'

import React from 'react'
import update from 'react-addons-update'
import RecordEditComponent from '../components/RecordEditComponent'
import utils from '../utils'
import i18n from '../i18n'
import widgets from '../widgets'
import makeRichPromise from '../richPromise'

class EditPage extends RecordEditComponent {
  constructor (props) {
    super(props)

    this.state = {
      recordInitialData: null,
      recordData: null,
      recordDataModel: null,
      recordInfo: null,
      hasPendingChanges: false
    }
    this._onKeyPress = this._onKeyPress.bind(this)
  }

  componentDidMount () {
    super.componentDidMount()
    this.syncEditor()
    window.addEventListener('keydown', this._onKeyPress)
  }

  componentWillReceiveProps (nextProps) {
    /*
    if (nextProps.params.path !== this.props.params.path) {
      this.syncEditor();
    }
    */
  }

  componentDidUpdate (prevProps, prevState) {
    if (prevProps.params.path !== this.props.params.path) {
      this.syncEditor()
    }
  }

  componentWillUnmount () {
    window.removeEventListener('keydown', this._onKeyPress)
  }

  hasPendingChanges () {
    return this.state.hasPendingChanges
  }

  _onKeyPress (event) {
    // meta+s is open find files
    if (event.which === 83 && utils.isMetaKey(event)) {
      event.preventDefault()
      this.saveChanges()
    }
  }

  isIllegalField (field) {
    switch (field.name) {
      case '_id':
      case '_path':
      case '_gid':
      case '_alt':
      case '_source_alt':
      case '_model':
      case '_attachment_for':
        return true
      case '_attachment_type':
        return !this.state.recordInfo.is_attachment
    }
    return false
  }

  syncEditor () {
    utils.loadData('/rawrecord', {
      path: this.getRecordPath(),
      alt: this.getRecordAlt()
    }, null, makeRichPromise)
    .then((resp) => {
      this.setState({
        recordInitialData: resp.data,
        recordData: {},
        recordDataModel: resp.datamodel,
        recordInfo: resp.record_info,
        hasPendingChanges: false
      })
    })
  }

  onValueChange (field, value) {
    let updates = {}
    updates[field.name] = {$set: value || ''}
    const rd = update(this.state.recordData, updates)
    this.setState({
      recordData: rd,
      hasPendingChanges: true
    })
  }

  getValues () {
    let rv = {}
    this.state.recordDataModel.fields.forEach((field) => {
      if (this.isIllegalField(field)) {
        return
      }

      let value = this.state.recordData[field.name]

      if (value !== undefined) {
        const Widget = widgets.getWidgetComponentWithFallback(field.type)
        if (Widget.serializeValue) {
          value = Widget.serializeValue(value, field.type)
        }
      } else {
        value = this.state.recordInitialData[field.name]
        if (value === undefined) {
          value = null
        }
      }

      rv[field.name] = value
    })

    return rv
  }

  saveChanges () {
    const path = this.getRecordPath()
    const alt = this.getRecordAlt()
    const newData = this.getValues()
    utils.apiRequest('/rawrecord', {json: {
      data: newData, path: path, alt: alt},
      method: 'PUT'}, makeRichPromise)
      .then((resp) => {
        this.setState({
          hasPendingChanges: false
        }, () => {
          this.transitionToAdminPage('.preview', {
            path: this.getUrlRecordPathWithAlt(path)
          })
        })
      })
  }

  deleteRecord (event) {
    this.transitionToAdminPage('.delete', {
      path: this.getUrlRecordPathWithAlt()
    })
  }

  getValueForField (widget, field) {
    let value = this.state.recordData[field.name]
    if (value === undefined) {
      value = this.state.recordInitialData[field.name] || ''
      if (widget.deserializeValue) {
        value = widget.deserializeValue(value, field.type)
      }
    }
    return value
  }

  getPlaceholderForField (widget, field) {
    if (field['default'] !== null) {
      if (widget.deserializeValue) {
        return widget.deserializeValue(field['default'], field.type)
      }
      return field['default']
    } else if (field.name === '_slug') {
      return this.state.recordInfo.slug_format
    } else if (field.name === '_template') {
      return this.state.recordInfo.default_template
    } else if (field.name === '_attachment_type') {
      return this.state.recordInfo.implied_attachment_type
    }
    return null
  }

  renderFormField (field, idx) {
    const widget = widgets.getWidgetComponentWithFallback(field.type)
    return (
      <widgets.FieldBox
        key={idx}
        value={this.getValueForField(widget, field)}
        placeholder={this.getPlaceholderForField(widget, field)}
        field={field}
        onChange={this.onValueChange.bind(this, field)}
        disabled={!(field.alts_enabled == null || (field.alts_enabled ^ this.state.recordInfo.alt === '_primary'))}
      />
    )
  }

  renderFormFields () {
    return widgets.renderFieldRows(
      this.state.recordDataModel.fields,
      this.isIllegalField.bind(this),
      this.renderFormField.bind(this)
    )
  }

  render () {
    // we have not loaded anything yet.
    if (this.state.recordInfo === null) {
      return null
    }

    let deleteButton = null
    if (this.state.recordInfo.can_be_deleted) {
      deleteButton = (
        <button type='submit' className='btn btn-default'
          onClick={this.deleteRecord.bind(this)}>{i18n.trans('DELETE')}</button>
      )
    }

    const title = this.state.recordInfo.is_attachment
      ? i18n.trans('EDIT_ATTACHMENT_METADATA_OF')
      : i18n.trans('EDIT_PAGE_NAME')

    const label = this.state.recordInfo.label_i18n
      ? i18n.trans(this.state.recordInfo.label_i18n)
      : this.state.recordInfo.label

    return (
      <div className='edit-area'>
        <h2>{title.replace('%s', label)}</h2>
        {this.renderFormFields()}
        <div className='actions'>
          <button type='submit' className='btn btn-primary'
            onClick={this.saveChanges.bind(this)}>{i18n.trans('SAVE_CHANGES')}</button>
          {deleteButton}
        </div>
      </div>
    )
  }
}

export default EditPage
