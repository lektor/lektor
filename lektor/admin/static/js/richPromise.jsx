function bringUpDialog(error) {
  // we need to import this here due to circular dependencies
  const ErrorDialog = require('./dialogs/errorDialog')
  const dialogSystem = require('./dialogSystem')
  if (!dialogSystem.dialogIsOpen()) {
    dialogSystem.showDialog(ErrorDialog, {
      error: error
    });
  }
}


function makeRichPromise(callback, fallback) {
  if (!fallback) {
    fallback = bringUpDialog;
  }

  const rv = new Promise(callback)
  const then = rv.then
  let hasRejectionHandler = false;
  rv.then(null, (value) => {
    if (!hasRejectionHandler) {
      return fallback(value);
    }
  });
  rv.then = (onFulfilled, onRejected) => {
    if (onRejected) {
      hasRejectionHandler = true;
    }
    return then.call(rv, onFulfilled, onRejected);
  };
  return rv;
}


export default {
  makeRichPromise: makeRichPromise
}
