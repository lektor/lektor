'use strict'

import PropTypes from 'prop-types'
import React from 'react'
import RecordComponent from '../components/RecordComponent'
import SlideDialog from '../components/SlideDialog'
import dialogSystem from '../dialogSystem'
import i18n from '../i18n'

class ErrorDialog extends RecordComponent {
  onClose () {
    dialogSystem.dismissDialog()
  }

  render () {
    return (
      <SlideDialog
        hasCloseButton
        closeOnEscape
        title={i18n.trans('ERROR')}>
        <p>
          {i18n.trans('ERROR_OCURRED')}{': '}
          {i18n.trans('ERROR_' + this.props.error.code)}
        </p>
        <div className='actions'>
          <button type='submit' className='btn btn-primary'
            onClick={this.onClose.bind(this)}>{i18n.trans('CLOSE')}</button>
        </div>
      </SlideDialog>
    )
  }
}

ErrorDialog.propTypes = {
  error: PropTypes.object
}

export default ErrorDialog
