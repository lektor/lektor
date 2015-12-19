'use strict';

var React = require('react');


class Hub {

  constructor() {
    this._subscriptions = {};
  }

  /* subscribes a callback to an event */
  subscribe(event, callback) {
    if (typeof event !== 'string') {
      event = event.getEventType();
    }

    var subs = this._subscriptions[event];
    if (subs === undefined) {
      this._subscriptions[event] = subs = [];
    }

    for (var i = 0; i < subs.length; i++) {
      if (subs[i] === callback) {
        return false;
      }
    }

    subs.push(callback);
    return true;
  }

  /* unsubscribes a callback from an event */
  unsubscribe(event, callback) {
    if (typeof event !== 'string') {
      event = event.getEventType();
    }

    var subs = this._subscriptions[event];
    if (subs === undefined) {
      return false;
    }

    for (var i = 0; i < subs.length; i++) {
      if (subs[i] === callback) {
        subs.splice(i, 1);
        return true;
      }
    }
    return false;
  }

  /* emits an event with some parameters */
  emit(event) {
    var subs = this._subscriptions[event.type];
    if (subs !== undefined) {
      subs.forEach(function(callback) {
        try {
          callback(event);
        } catch (e) {
          console.log('Event callback failed: ', e, 'callback=',
                      callback, 'event=', event);
        }
      })
    }
  }
}


var hub = new Hub();


module.exports = hub;
