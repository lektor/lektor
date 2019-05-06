/*
 * Insert Image extension for TUI editor
 * Based on popupAddImage.js and colorSyntax.js
 *
 * Integrates with Lektor's attachment system to enable selecting an existing
 * attachment, and uploading a new image attachment.
 */

import React from 'react'

import hub from '../hub'
import utils from '../utils'
import { AttachmentsChangedEvent } from '../events'
import RecordComponent from '../components/RecordComponent'
import makeRichPromise from '../richPromise'

// name of the extension
const EXT_NAME = 'lektorLink'

class LektorImageExtension extends RecordComponent {
  constructor (props) {
    super(props)

    this.editor = null
    this.button = null

    this.initForm = {
      attachmentPath: '----',
      attachmentAltText: '',
      uploadFile: null,
      uploadAltText: '',
      externalPath: '',
      externalAltText: ''
    }

    this.state = {
      show: false,
      top: '',
      left: '',
      mode: 'attachment',
      files: [],
      form: this.initForm
    }

    this.modeChange = this.modeChange.bind(this)
    this.formChange = this.formChange.bind(this)
    this.canAddImage = this.canAddImage.bind(this)
    this.addImage = this.addImage.bind(this)
    this.init = this.init.bind(this)
    this.hide = this.hide.bind(this)
    this.show = this.show.bind(this)
  }

  // called when we switch tabs
  modeChange (e) {
    this.setState({
      mode: e.target.getAttribute('data-mode')
    })
  }

  // called whenever one of the controlled form elements is updated
  formChange (e) {
    const key = e.target.getAttribute('data-key')
    const val = e.target.type === 'file' ? e.target.files[0] : e.target.value

    this.setState(prevState => {
      return {
        form: {
          ...prevState.form,
          [key]: val
        }
      }
    })
  }

  hide () {
    this.setState({
      show: false
    })
  }

  show () {
    this.setState({
      form: this.initForm,
      show: true
    })
  }

  init () {
    // add the event for when the toolbar button is clicked
    this.editor.eventManager.addEventType('lektorImageButtonClicked')

    // add the button to the toolbar
    const toolbar = this.editor.getUI().getToolbar()
    toolbar.insertItem(14, {
      type: 'button',
      options: {
        name: EXT_NAME,
        className: 'tui-image',
        event: 'lektorImageButtonClicked',
        tooltip: 'Add Image'
      }
    })
    const lektorImageButtonIndex = toolbar.indexOfItem(EXT_NAME)
    const {$el: $button} = toolbar.getItem(lektorImageButtonIndex)
    this.button = $button

    // make the popup hide on editor focus, closeAllPopup, and close
    this.editor.eventManager.listen('focus', () => { this.hide() })
    this.editor.eventManager.listen('closeAllPopup', () => { this.hide() })
    this.editor.eventManager.listen('removeEditor', () => { this.hide() })

    // add event handler for when the toolbar button is clicked
    this.editor.eventManager.listen('lektorImageButtonClicked', () => {
      // if the popup is open, close it
      if (this.state.show) {
        this.hide()
        return
      }

      // get the current attachments of this page by calling the API
      utils.loadData('/recordinfo', {
        path: this.getRecordPath()
      }, null, makeRichPromise)
      .then((data) => {
        // filter out non-image files
        let imageAttachments = data.attachments.filter((file) => {
          return file.type === 'image'
        })

        // add the attachments into state
        this.setState({
          files: imageAttachments
        })
      })
      .finally(() => {
        // set popup location to be under the button
        const { offsetTop, offsetLeft } = this.button.get(0)
        this.setState({
          top: offsetTop + this.button.outerHeight() + 18 + 4,
          left: offsetLeft + 15
        })

        // show the popup
        this.editor.eventManager.emit('closeAllPopup')
        this.show()
      })
    })
  }

  // called when the add button on the popup is clicked
  addImage () {
    // what mode are we in?
    switch (this.state.mode) {
      case 'upload':
        // create new form object to send to the API to upload the image
        const formData = new window.FormData()
        formData.append('path', this.getRecordPath())
        formData.append('file', this.state.form.uploadFile, this.state.form.uploadFile.name)
        const xhr = new window.XMLHttpRequest()
        xhr.open('POST', utils.getApiUrl('/newattachment'))

        // upload finished event
        xhr.onload = (event) => {
          const data = JSON.parse(xhr.responseText)
          hub.emit(new AttachmentsChangedEvent({
            recordPath: this.getRecordPath(),
            attachmentsAdded: data.buckets.map((bucket) => {
              return bucket.stored_filename
            })
          }))
          // emit add image event to the editor to add the image in
          this.editor.eventManager.emit('command', 'AddImage', {
            imageUrl: data.path + '/' + data.buckets[0].stored_filename,
            altText: this.state.form.uploadAltText
          })
          this.hide()
        }
        xhr.send(formData)
        break

      case 'attachment':
      case 'external':
        // emit add image event to the editor to add the image in
        this.editor.eventManager.emit('command', 'AddImage', {
          imageUrl: this.state.mode === 'attachment' ? this.state.form.attachmentPath : this.state.form.externalPath,
          altText: this.state.mode === 'attachment' ? this.state.form.attachmentAltText : this.state.form.externalAltText
        })

        // close the popup
        this.hide()
        break
    }
  }

  // return true if all the required info on the current tab is filled out
  canAddImage () {
    switch (this.state.mode) {
      case 'attachment':
        return this.state.form.attachmentPath !== '----'
      case 'upload':
        return this.state.form.uploadFile !== null
      case 'external':
        return this.state.form.externalPath !== ''
    }
  }

  render () {
    // call init once we have the editor
    if (this.editor === null && this.props.editor !== null) {
      this.editor = this.props.editor
      this.init()
    }

    // render popup
    return (
      <div className='tui-popup-wrapper tui-popup-body' style={{display: this.state.show ? 'block' : 'none', width: 'auto', position: 'absolute', top: this.state.top, left: this.state.left, minWidth: '295px'}}>
        <div id='tabs' className='popup'>
          <ul className='nav'>
            <li><a onClick={this.modeChange} data-mode='attachment' className={this.state.mode === 'attachment' ? 'active' : ''}>Attachment</a></li>
            <li><a onClick={this.modeChange} data-mode='upload' className={this.state.mode === 'upload' ? 'active' : ''}>Upload</a></li>
            <li><a onClick={this.modeChange} data-mode='external' className={this.state.mode === 'external' ? 'active' : ''}>External</a></li>
          </ul>

          <div id='popup-tab-attachment' className='content attachment' style={{display: this.state.mode === 'attachment' ? 'block' : 'none'}}>
            <dl className='field'>
              <dt>File</dt>
              <dd>
                <div className='form-group'>
                  <div>
                    <select id='attachment-path' className='form-control' data-key='attachmentPath' onChange={this.formChange} value={this.state.form.attachmentPath}>
                      <option value='----'>----</option>
                      {this.state.files.map(file => <option key={file.id} value={file.path}>{file.id}</option>)}
                    </select>
                  </div>
                </div>
              </dd>
            </dl>
            <dl className='field'>
              <dt>Alt Text</dt>
              <dd>
                <div className='form-group'>
                  <div className='input-group'>
                    <input id='attachment-alt-text' type='text' className='form-control' data-key='attachmentAltText' onChange={this.formChange} value={this.state.form.attachmentAltText} />
                  </div>
                </div>
              </dd>
            </dl>
          </div>

          <div id='popup-tab-upload' className='content' style={{display: this.state.mode === 'upload' ? 'block' : 'none'}}>
            <dl className='field'>
              <dt>Image File</dt>
              <dd>
                <div className='form-group'>
                  <div className='input-group'>
                    <input id='upload-file' type='file' className='form-control' accept='image/*' data-key='uploadFile' onChange={this.formChange} />
                  </div>
                </div>
              </dd>
            </dl>
            <dl className='field'>
              <dt>Alt Text</dt>
              <dd>
                <div className='form-group'>
                  <div className='input-group'>
                    <input id='upload-alt-text' type='text' className='form-control' data-key='uploadAltText' onChange={this.formChange} value={this.state.form.uploadAltText} />
                  </div>
                </div>
              </dd>
            </dl>
          </div>

          <div id='popup-tab-external' className='content' style={{display: this.state.mode === 'external' ? 'block' : 'none'}}>
            <dl className='field'>
              <dt>Image URL</dt>
              <dd>
                <div className='form-group'>
                  <div className='input-group'>
                    <input id='external-path' type='text' className='form-control' data-key='externalPath' onChange={this.formChange} value={this.state.form.externalPath} />
                  </div>
                </div>
              </dd>
            </dl>
            <dl className='field'>
              <dt>Alt Text</dt>
              <dd>
                <div className='form-group'>
                  <div className='input-group'>
                    <input id='external-alt-text' type='text' className='form-control' data-key='externalAltText' onChange={this.formChange} value={this.state.form.externalAltText} />
                  </div>
                </div>
              </dd>
            </dl>
          </div>

          <div className='actions'>
            <div onClick={this.addImage} className={'btn btn-primary ' + (!this.canAddImage() ? 'disabled' : '')}>Add</div>
            <div onClick={this.hide} className='btn btn-default'>Cancel</div>
          </div>
        </div>
      </div>
    )
  }
}

export default LektorImageExtension
