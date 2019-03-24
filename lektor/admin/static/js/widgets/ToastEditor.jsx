'use strict'

import React, { Component } from 'react'
import Editor from 'tui-editor'

import 'codemirror/lib/codemirror.css'
import 'tui-editor/dist/tui-editor.min.css'
import 'tui-editor/dist/tui-editor-contents.min.css'

const toolbarItems = [
  'heading',
  'bold',
  'italic',
  'strike',
  'divider',
  'hr',
  'quote',
  'divider',
  'ul',
  'ol',
  // 'task',
  'indent',
  'outdent',
  'divider',
  'table',
  // 'image',
  // 'link',
  'divider',
  'code',
  'codeblock'
]

class ToastEditor extends Component {
  constructor () {
    super()
    this.editor = null
    this.element = null
    this.count = 0

    this.onChange = this.onChange.bind(this)
    this.onRef = this.onRef.bind(this)
    this.blur = this.blur.bind(this)
    this.focus = this.focus.bind(this)

    this.state = {
      style: {}
    }
  }

  onLoad (editor) {
    // change label of 'WYSIWYG' to 'Rich Text'
    editor.getUI().getModeSwitch().$el[0].getElementsByClassName('wysiwyg')[0].innerText = 'Rich Text'
  }

  onImageUpload (file, cb, source) {
    // do image upload of file here, call cb once done
    cb(file.name) // leave second param null to use user-specified text
  }

  onChange () {
    const markdown = this.editor.getMarkdown()
    if (this.count === 0 && markdown === '') {
      this.count++
      return
    }

    if (this.props.onChange) {
      this.props.onChange(markdown)
    }
  }

  // focus and blur are used to implement the border-blur found on other widgets
  focus () {
    this.setState({
      style: {
        borderColor: '#807177',
        outline: 0,
        boxShadow: 'inset 0 1px 1px rgba(0,0,0,.075), 0 0 8px rgba(128, 113, 119, 0.6)',
        transition: 'border-color ease-in-out .15s, box-shadow ease-in-out .15s'
      }
    })
    this.element.firstChild.style.transition = 'border-color ease-in-out .15s, box-shadow ease-in-out .15s'
    this.element.firstChild.style.borderColor = '#807177'
  }
  blur () {
    this.setState({
      style: {
        transition: 'border-color ease-in-out .15s, box-shadow ease-in-out .15s'
      }
    })
    this.element.firstChild.style.borderColor = '#e5e5e5'
  }

  onRef (element) {
    if (element === null) {
      return
    }
    this.element = element
    this.editor = new Editor({
      el: element,
      initialValue: this.props.value,
      initialEditType: 'wysiwyg',
      useCommandShortcut: true,
      usageStatistics: false,
      previewStyle: null,
      toolbarItems: toolbarItems,
      hooks: {
        addImageBlobHook: this.onImageUpload
      },
      events: {
        load: this.onLoad,
        change: this.onChange,
        focus: this.focus,
        blur: this.blur
      }
    })
  }

  render () {
    return (
      <div
        ref={this.onRef}
        style={this.state.style}
      />
    )
  }
}

export default ToastEditor
