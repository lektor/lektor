'use strict'

import React from 'react'
import Editor from 'tui-editor'

import Component from '../components/Component'

import 'codemirror/lib/codemirror.css'
import 'tui-editor/dist/tui-editor.min.css'
import 'tui-editor/dist/tui-editor-contents.min.css'

import LektorLinkExtension from './tuiEditorLektorLinkExt.jsx'
import LektorImageExtension from './tuiEditorLektorImageExt.jsx'

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
    this.element = null
    this.count = 0
    this.content = null

    this.onChange = this.onChange.bind(this)
    this.onLoad = this.onLoad.bind(this)
    this.onRef = this.onRef.bind(this)
    this.blur = this.blur.bind(this)
    this.focus = this.focus.bind(this)

    this.state = {
      style: {},
      editor: null
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
    // add in the mode switcher
    let toolbar = editor.getUI().getToolbar()
    toolbar.insertItem(0, {type: 'button', options: {name: 'richtext-tab', text: 'Rich Text', event: 'mode-tab-richtext', tooltip: 'Use Rich Text Editor', className: 'mode-tab'}})
    toolbar.insertItem(1, {type: 'button', options: {name: 'markdown-tab', text: 'Markdown', event: 'mode-tab-markdown', tooltip: 'Use Markdown Editor', className: 'mode-tab'}})
    toolbar.insertItem(2, {type: 'divider', options: {name: 'switch-divider', className: 'mode-tab-divider'}})
    let richtextbtn = toolbar.getItem(0).$el
    let markdownbtn = toolbar.getItem(1).$el
    editor.eventManager.addEventType('mode-tab-richtext')
    editor.eventManager.addEventType('mode-tab-markdown')
    editor.eventManager.listen('mode-tab-richtext', () => { markdownbtn.removeClass('active'); richtextbtn.addClass('active'); editor.changeMode('wysiwyg', true) })
    editor.eventManager.listen('mode-tab-markdown', () => { richtextbtn.removeClass('active'); markdownbtn.addClass('active'); editor.changeMode('markdown', true) })
    let activebtn = (this.props.type.default_view === 'richtext') ? richtextbtn : markdownbtn
    activebtn.addClass('active')

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
    if (!this.state.editor) {
      return
    }

    const markdown = this.state.editor.getMarkdown()
    if (this.count === 0 && markdown === '') {
      this.count++
      return
    }

    // recalculate height - delay is required to get most up to date height
    setTimeout(function () {
      this.recalculateHeight(this.state.editor)
    }.bind(this), 10)

    // send markdown up
    let contentChanged = markdown !== this.content
    if (this.props.onChange && this.content !== null && contentChanged) {
      this.content = markdown
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
    this.content = this.props.value
    let editor = new Editor({
      el: element,
      initialValue: this.props.value,
      initialEditType: (this.props.type.default_view === 'richtext') ? 'wysiwyg' : 'markdown',
      useCommandShortcut: true,
      usageStatistics: false,
      previewStyle: null,
      hideModeSwitch: true,
      toolbarItems: toolbarItems,
      hooks: {
        addImageBlobHook: this.onImageUpload
      },
      events: {
        load: this.onLoad,
        change: this.onChange,
        stateChange: this.onChange,
        contentChangedFromWysiwyg: () => { setTimeout(this.onChange, 100) },
        focus: this.focus,
        blur: this.blur
      },
      exts: ['lektorImage', 'lektorLink']
    })
    this.setState({
      editor: editor
    })
  }

  render () {
    return (
      <div>
        <div
          ref={this.onRef}
          style={this.state.style}
        />
        <LektorImageExtension editor={this.state.editor} {...this.getRoutingProps()} />
        <LektorLinkExtension editor={this.state.editor} {...this.getRoutingProps()} />
      </div>
    )
  }
}

export default ToastEditor
