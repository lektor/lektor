'use strict'

import PropTypes from 'prop-types'
import React from 'react'
import RecordComponent from '../components/RecordComponent'
import SlideDialog from '../components/SlideDialog'
import dialogSystem from '../dialogSystem'
import i18n from '../i18n'

class SuccessDialog extends RecordComponent {
  onClose () {
    dialogSystem.dismissDialog()
    window.location.reload()
  }

  render () {
    return (
      <SlideDialog
        hasCloseButton
        closeOnEscape        
        title={i18n.trans('SUCCESS')}>
        <p>
          {this.props.message}
        </p>
        <div className='actions'>
          <button type='submit' className='btn btn-primary'
            onClick={this.onClose.bind(this)}>{i18n.trans('CLOSE')}</button>
        </div>
      </SlideDialog>
    )
  }
}

SuccessDialog.propTypes = {
  message: PropTypes.string
}

export default SuccessDialog
