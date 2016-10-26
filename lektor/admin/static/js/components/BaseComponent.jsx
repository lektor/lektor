// the base component.  This really should not exist in the first place
// but react is a bit meh when it comes to what's on the base component
// which breaks super.  This is why we do this here.  Note that this is
// also used by the standalone admin UI app.

'use strict'

import React from 'react'


class BaseComponent extends React.Component {

  componentDidMount() {
  }

  componentWillUnmount() {
  }

  componentDidUpdate() {
  }

  componentWillReceiveProps(nextProps) {
  }
}

export default BaseComponent
