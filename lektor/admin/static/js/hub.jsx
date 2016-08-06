'use strict'

import React from 'react'


class Hub {

  constructor() {
    this._subscriptions = {};
  }

  /* subscribes a callback to an event */
  subscribe(event, callback) {
    if (typeof event !== 'string') {
      event = event.getEventType();
    }

    let subs = this._subscriptions[event];
    if (subs === undefined) {
      this._subscriptions[event] = subs = [];
    }

    for (let i = 0; i < subs.length; i++) {
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

    const subs = this._subscriptions[event]
    if (subs === undefined) {
      return false;
    }

    for (let i = 0; i < subs.length; i++) {
      if (subs[i] === callback) {
        subs.splice(i, 1);
        return true;
      }
    }
    return false;
  }

  /* emits an event with some parameters */
  emit(event) {
    const subs = this._subscriptions[event.type]
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


const hub = new Hub()


export default hub
