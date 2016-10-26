'use strict'

import React from 'react'
import Router from 'react-router'
var {Link, RouteHandler} = Router

import RecordComponent from '../components/RecordComponent'
import SlideDialog from '../components/SlideDialog'
import utils from '../utils'
import i18n from '../i18n'
import dialogSystem from '../dialogSystem'

class FindFiles extends RecordComponent {

  constructor(props) {
    super(props)
    this.state = {
      query: '',
      currentSelection: -1,
      results: []
    };
  }

  componentDidMount() {
    super.componentDidMount()
    this.refs.q.focus()
  }

  onInputChange(e) {
    var q = e.target.value

    if (q === '') {
      this.setState({
        query: '',
        results: [],
        currentSelection: -1
      })
    } else {
      this.setState({
        query: q
      })

      utils.apiRequest('/find', {
        data: {
          q: q,
          alt: this.getRecordAlt(),
          lang: i18n.currentLanguage
        },
        method: 'POST'
      }).then((resp) => {
        this.setState({
          results: resp.results,
          currentSelection: Math.min(this.state.currentSelection,
                                     resp.results.length - 1)
        })
      })
    }
  }

  onInputKey(e) {
    var sel = this.state.currentSelection
    var max = this.state.results.length
    if (e.which == 40) {
      e.preventDefault()
      sel = (sel + 1) % max
    } else if (e.which == 38) {
      e.preventDefault()
      sel = (sel - 1 + max) % max
    } else if (e.which == 13) {
      this.onActiveItem(this.state.currentSelection)
    }
    this.setState({
      currentSelection: sel
    });
  }

  onActiveItem(index) {
    var item = this.state.results[index]
    if (item !== undefined) {
      var target = this.isRecordPreviewActive() ? '.preview' : '.edit'
      var urlPath = this.getUrlRecordPathWithAlt(item.path)
      dialogSystem.dismissDialog()
      this.transitionToAdminPage(target, {path: urlPath})
    }
  }

  selectItem (index) {
    this.setState({
      currentSelection: Math.min(index, this.state.results.length - 1)
    })
  }

  renderResults() {
    var rv = []

    var rv = this.state.results.map((result, idx) => {
      var parents = result.parents.map((item, idx) => {
        return (
          <span className="parent" key={idx}>
            {item.title}
          </span>
        )
      })

      return (
        <li
          key={idx}
          className={idx == this.state.currentSelection ? 'active': ''}
          onClick={this.onActiveItem.bind(this, idx)}
          onMouseEnter={this.selectItem.bind(this, idx)}>
          {parents}
          <strong>{result.title}</strong>
        </li>
      )
    })

    return (
      <ul className="search-results">{rv}</ul>
    )
  }

  render () {
    return (
      <SlideDialog
        hasCloseButton={true}
        closeOnEscape={true}
        title={i18n.trans('FIND_FILES')}>
        <div className="form-group">
          <input type="text"
            ref="q"
            className="form-control"
            value={this.state.query}
            onChange={this.onInputChange.bind(this)}
            onKeyDown={this.onInputKey.bind(this)}
            placeholder={i18n.trans('FIND_FILES_PLACEHOLDER')} />
        </div>
        {this.renderResults()}
      </SlideDialog>
    )
  }
}

export default FindFiles
