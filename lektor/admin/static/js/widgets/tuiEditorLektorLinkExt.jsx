/*
 * Insert Link extension for TUI editor
 * Based on popupAddLink.js and colorSyntax.js
 *
 * Integrates with Lektor's search system to provide suggestions of pages to
 * link to.
 */

import React from 'react'

import i18n from '../i18n'
import FindFiles from '../dialogs/findFiles'

// name of the extension
const EXT_NAME = 'lektorImage'

// regex expression to use to match against URLs
const URL_REGEX = /^(https?:\/\/)?([\da-z.-]+)\.([a-z.]{2,6})(\/([^\s]*))?$/

class LektorLinkExtension extends FindFiles {
  constructor (props) {
    super(props)

    this.editor = null
    this.button = null

    this.initForm = {
      pagePath: '',
      pageLinkText: '',
      externalPath: '',
      externalLinkText: ''
    }

    this.state = {
      show: false,
      top: '',
      left: '',
      mode: 'page',
      form: this.initForm,
      newOpen: true,
      query: '',
      currentSelection: -1,
      results: []
    }

    this.init = this.init.bind(this)
    this.hide = this.hide.bind(this)
    this.show = this.show.bind(this)
    this.modeChange = this.modeChange.bind(this)
    this.formChange = this.formChange.bind(this)
    this.updateFormState = this.updateFormState.bind(this)
    this.addLink = this.addLink.bind(this)
  }

  // overrides from FindFiles, called when a page search dropdown is selected
  onActiveItem (index) {
    const item = this.state.results[index]
    if (item !== undefined) {
      // set the query (text in the field) to the title
      this.setState({
        results: [],
        query: item.title
      })
      // update the form object with the page path
      this.updateFormState('pagePath', item.path)
    }
  }

  // called on change of the page search
  onPreInputChange (e) {
    // update the form object page path to nothing, as we are still searching
    this.updateFormState('pagePath', '')
    this.onInputChange.bind(this)(e)
  }

  hide () {
    this.setState({
      show: false
    })
  }

  show () {
    // on show, set the selected text to current text selection
    const selectedText = this.editor.getSelectedText()
    // if a url is selected, go to the external tab, and set the url to it
    const externalPath = URL_REGEX.exec(selectedText) ? selectedText : ''
    const mode = URL_REGEX.exec(selectedText) ? 'external' : 'page'

    // reset the state
    this.setState({
      mode: mode,
      show: true,
      newOpen: true,
      query: '',
      currentSelection: -1,
      results: [],
      form: {
        ...this.initForm,
        pageLinkText: selectedText,
        externalLinkText: selectedText,
        externalPath: externalPath
      }
    })
  }

  // called when we switch tabs
  modeChange (event) {
    this.setState({
      mode: event.target.getAttribute('data-mode')
    })
  }

  init () {
    // add the event for when the toolbar button is clicked
    this.editor.eventManager.addEventType('lektorLinkButtonClicked')

    // add the button to the toolbar
    const toolbar = this.editor.getUI().getToolbar()
    toolbar.insertItem(14, {
      type: 'button',
      options: {
        name: EXT_NAME,
        className: 'tui-link',
        event: 'lektorLinkButtonClicked',
        tooltip: 'Add Link'
      }
    })
    const lektorImageButtonIndex = toolbar.indexOfItem(EXT_NAME)
    const { $el: $button } = toolbar.getItem(lektorImageButtonIndex)
    this.button = $button

    // make the popup hide on editor focus, closeAllPopup, and close
    this.editor.eventManager.listen('focus', () => { this.hide() })
    this.editor.eventManager.listen('closeAllPopup', () => { this.hide() })
    this.editor.eventManager.listen('removeEditor', () => { this.hide() })

    // add event handler for when the toolbar button is clicked
    this.editor.eventManager.listen('lektorLinkButtonClicked', () => {
      // if the popup is open, close it
      if (this.state.show) {
        this.hide()
        return
      }

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
  }

  // return true if all the required info on the current tab is filled out
  canAddLink () {
    switch (this.state.mode) {
      case 'page':
        return this.state.form.pagePath !== ''
      case 'external':
        return this.state.form.externalPath !== ''
    }
  }

  // helper function for updating a value for a key in the form state object
  updateFormState (key, val) {
    this.setState(prevState => {
      return {
        form: {
          ...prevState.form,
          [key]: val
        }
      }
    })
  }

  // called when the add button on the popup is clicked
  addLink () {
    // get the link text and url, depending on what mode we're in
    var linkText = this.state.form.pageLinkText
    var url = this.state.form.pagePath + '/'
    if (this.state.mode === 'external') {
      linkText = this.state.form.externalLinkText
      url = this.state.form.externalPath
    }

    // send the command to the editor
    this.editor.eventManager.emit('command', 'AddLink', {
      linkText,
      url
    })

    // close the popup
    this.hide()
  }

  // called whenever one of the controlled form elements is updated
  formChange (event) {
    const key = event.target.getAttribute('data-key')
    const val = event.target.type = event.target.value
    this.updateFormState(key, val)
  }

  render () {
    // call init once we have the editor
    if (this.editor === null && this.props.editor !== null) {
      this.editor = this.props.editor
      this.init()
    }

    // render popup
    return (
      <div className='tui-popup-wrapper tui-popup-body' style={{ display: this.state.show ? 'block' : 'none', width: 'auto', position: 'absolute', top: this.state.top, left: this.state.left }}>
        <div id='tabs' className='popup'>
          <ul className='nav'>
            <li><a onClick={this.modeChange} data-mode='page' className={this.state.mode === 'page' ? 'active' : ''}>Page</a></li>
            <li><a onClick={this.modeChange} data-mode='external' className={this.state.mode === 'external' ? 'active' : ''}>URL</a></li>
          </ul>

          <div id='popup-tab-attachment' className='content attachment' style={{ display: this.state.mode === 'page' ? 'block' : 'none' }}>
            <dl className='field'>
              <dt>Page Search</dt>
              <dd>
                <div className='form-group'>
                  <div className='input-group'>
                    <div style={{ position: 'initial' }} className='dialog-slot'>
                      <div style={{ width: '260px', position: 'initial', padding: 'initial' }} className='sliding-panel container'>
                        <div style={{ boxShadow: 'initial', padding: 'initial' }}>
                          <div className='form-group'>
                            <input type='text'
                              ref='q'
                              className='form-control'
                              value={this.state.query}
                              onChange={this.onPreInputChange.bind(this)}
                              onKeyDown={this.onInputKey.bind(this)}
                              placeholder={i18n.trans('FIND_FILES_PLACEHOLDER')}
                            />
                          </div>
                          {this.renderResults()}
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </dd>
            </dl>
            <dl className='field'>
              <dt>Link Text</dt>
              <dd>
                <div className='form-group'>
                  <div className='input-group'>
                    <input id='page-link-text' type='text' className='form-control' data-key='pageLinkText' onChange={this.formChange} value={this.state.form.pageLinkText} />
                  </div>
                </div>
              </dd>
            </dl>
          </div>

          <div id='popup-tab-upload' className='content' style={{ display: this.state.mode === 'external' ? 'block' : 'none' }}>
            <dl className='field'>
              <dt>URL</dt>
              <dd>
                <div className='form-group'>
                  <div className='input-group'>
                    <input id='external-path' type='text' className='form-control' data-key='externalPath' onChange={this.formChange} value={this.state.form.externalPath} />
                  </div>
                </div>
              </dd>
            </dl>
            <dl className='field'>
              <dt>Link Text</dt>
              <dd>
                <div className='form-group'>
                  <div className='input-group'>
                    <input id='external-link-text' type='text' className='form-control' data-key='externalLinkText' onChange={this.formChange} value={this.state.form.externalLinkText} />
                  </div>
                </div>
              </dd>
            </dl>
          </div>

          <div className='actions'>
            <div onClick={this.addLink} className={'btn btn-primary ' + (!this.canAddLink() ? 'disabled' : '')}>Add</div>
            <div onClick={this.hide} className='btn btn-default'>Cancel</div>
          </div>
        </div>
      </div>
    )
  }
}

export default LektorLinkExtension
