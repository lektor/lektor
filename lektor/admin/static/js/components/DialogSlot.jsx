'use strict'

import React from 'react'
import dialogSystem from '../dialogSystem'
import { DialogChangedEvent } from '../events'
import hub from '../hub'

class DialogSlot extends React.Component {
  constructor (props) {
    super(props)
    this.state = {
      currentDialog: null,
      currentDialogOptions: null
    }
    this.onDialogChanged = this.onDialogChanged.bind(this)
  }

  componentDidMount () {
    hub.subscribe(DialogChangedEvent, this.onDialogChanged)
  }

  componentWillUnmount () {
    hub.unsubscribe(DialogChangedEvent, this.onDialogChanged)
  }

  onDialogChanged (event) {
    this.setState({
      currentDialog: event.dialog,
      currentDialogOptions: event.dialogOptions || {}
    })
  }

  initDialogInstance (dialog) {
    dialogSystem.notifyDialogInstance(dialog)
    window.scrollTo(0, 0)
  }

  render () {
    let dialog = null
    if (this.state.currentDialog) {
      dialog = (
        <this.state.currentDialog
          ref={(ref) => this.initDialogInstance(ref)}
          {...this.props}
          {...this.state.currentDialogOptions}
        />)
    } else {
      dialogSystem.notifyDialogInstance(null)
    }

    if (!dialog) {
      return null
    }

    return (
      <div className='dialog-slot'>
        {dialog}
        <div className='interface-protector' />
      </div>
    )
  }
}

export default DialogSlot
