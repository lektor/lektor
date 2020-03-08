'use strict'

import React from 'react'
import PropTypes from 'prop-types'

class ToggleGroup extends React.Component {
  constructor (props) {
    super(props)
    this.state = {
      isVisible: props.defaultVisibility
    }
  }

  toggle (event) {
    event.preventDefault()
    this.setState({
      isVisible: !this.state.isVisible
    })
  }

  render () {
    let { className, groupTitle, children, defaultVisibility, ...otherProps } = this.props
    className = (className || '') + ' toggle-group'
    if (this.state.isVisible) {
      className += ' toggle-group-open'
    } else {
      className += ' toggle-group-closed'
    }

    return (
      <div className={className} {...otherProps}>
        <div className='header'>
          <h4 className='toggle' onClick={
            this.toggle.bind(this)}>{groupTitle}</h4>
        </div>
        <div className='children'>
          {children}
        </div>
      </div>
    )
  }
}

ToggleGroup.propTypes = {
  groupTitle: PropTypes.string,
  defaultVisibility: PropTypes.bool
}

export default ToggleGroup
