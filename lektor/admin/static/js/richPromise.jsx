import ErrorDialog from './dialogs/errorDialog'
import dialogSystem from './dialogSystem'

const bringUpDialog = (error) => {
  if (!dialogSystem.dialogIsOpen()) {
    dialogSystem.showDialog(ErrorDialog, {
      error: error
    })
  }
}

const makeRichPromise = (callback, fallback = bringUpDialog) => {
  const rv = new Promise(callback)
  const then = rv.then
  let hasRejectionHandler = false

  rv.then(null, (value) => {
    if (!hasRejectionHandler) {
      return fallback(value)
    }
  })

  rv.then = (onFulfilled, onRejected) => {
    if (onRejected) {
      hasRejectionHandler = true
    }
    return then.call(rv, onFulfilled, onRejected)
  }

  return rv
}

export default makeRichPromise
