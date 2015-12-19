function bringUpDialog(error) {
  // we need to import this here due to circular dependencies
  var ErrorDialog = require('./dialogs/errorDialog');
  var dialogSystem = require('./dialogSystem');
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

  var rv = new Promise(callback);
  var then = rv.then;
  var hasRejectionHandler = false;
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


module.exports = {
  makeRichPromise: makeRichPromise
}
