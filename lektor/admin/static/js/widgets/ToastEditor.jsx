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
    this.onLoad = this.onLoad.bind(this)
    this.onRef = this.onRef.bind(this)
    this.blur = this.blur.bind(this)
    this.focus = this.focus.bind(this)

    this.state = {
      style: {}
    }
  }

  // from http://youmightnotneedjquery.com/#outer_height_with_margin
  outerHeight (el) {
    var height = el.offsetHeight
    var style = window.getComputedStyle(el)

    height += parseInt(style.marginTop) + parseInt(style.marginBottom)
    return height
  }

  onLoad (editor) {
    // change label of 'WYSIWYG' to 'Rich Text'
    editor.getUI().getModeSwitch().$el[0].getElementsByClassName('wysiwyg')[0].innerText = 'Rich Text'
    this.recalculateHeight(editor)
  }

  onImageUpload (file, cb, source) {
    // do image upload of file here, call cb once done
    cb(file.name) // leave second param null to use user-specified text
  }

  recalculateHeight (editor) {
    let currentEditor = editor.getCurrentModeEditor()
    let editorHeight
    try {
      // markdown
      let editorEl = currentEditor.editorContainerEl.getElementsByClassName('CodeMirror-sizer')[0]
      editorHeight = this.outerHeight(editorEl)
    } catch (e) {
      // wysiwyg

      // get height of all children in editor
      let editorEl = currentEditor.$editorContainerEl[0].firstChild
      let editorChildren = Array.from(editorEl.children)
      let editorChildrenHeights = editorChildren.map(el => this.outerHeight(el))
      editorHeight = editorChildrenHeights.reduce((a, b) => a + b)

      // add on padding/border/margin of editor element
      let marginTop = parseInt(window.getComputedStyle(editorEl).marginTop)
      let marginBottom = parseInt(window.getComputedStyle(editorEl).marginBottom)
      let paddingTop = parseInt(window.getComputedStyle(editorEl).paddingTop)
      let paddingBottom = parseInt(window.getComputedStyle(editorEl).paddingBottom)
      let borderTop = parseInt(window.getComputedStyle(editorEl).borderTopWidth)
      let borderBottom = parseInt(window.getComputedStyle(editorEl).borderBottomWidth)
      editorHeight += (marginTop + marginBottom + paddingTop + paddingBottom + borderTop + borderBottom)
    }

    let totalHeight = editorHeight + 31 + 31
    let totalHeightStr = totalHeight + 'px'
    editor.height(totalHeightStr)
  }

  onChange () {
    const markdown = this.editor.getMarkdown()
    if (this.count === 0 && markdown === '') {
      this.count++
      return
    }

    // recalculate height - delay is required to get most up to date height
    setTimeout(function () {
      this.recalculateHeight(this.editor)
    }.bind(this), 10)

    // send markdown up
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
        stateChange: this.onChange,
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
