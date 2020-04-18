'use strict'

import Component from './Component'
import { getParentFsPath, urlToFsPath, fsToUrlPath, urlPathToSegments } from '../utils'

export function getRecordPathAndAlt (path) {
  if (!path) {
    return [null, null]
  }
  const items = path.split(/\+/, 2)
  return [urlToFsPath(items[0]), items[1]]
}

/* a react component baseclass that has some basic knowledge about
   the record it works with. */
class RecordComponent extends Component {
  /* this returns the current record path segments as array */
  getRecordPathSegments () {
    const path = this.props.match.params.path
    return path ? urlPathToSegments(path) : []
  }

  /* this returns the path of the current record.  If the current page does
   * not have a path component then null is returned. */
  getRecordPath () {
    const [path] = getRecordPathAndAlt(this.props.match.params.path)
    return path
  }

  /* returns the current alt */
  getRecordAlt () {
    const [, alt] = getRecordPathAndAlt(this.props.match.params.path)
    return !alt ? '_primary' : alt
  }

  /* return the url path for the current record path (or a modified one)
     by preserving or overriding the alt */
  getUrlRecordPathWithAlt (newPath, newAlt) {
    if (newPath === undefined || newPath === null) {
      newPath = this.getRecordPath()
    }
    if (newAlt === undefined || newAlt === null) {
      newAlt = this.getRecordAlt()
    }
    let rv = fsToUrlPath(newPath)
    if (newAlt !== '_primary') {
      rv += '+' + newAlt
    }
    return rv
  }

  /* returns the parent path if available */
  getParentRecordPath () {
    return getParentFsPath(this.getRecordPath())
  }

  /* returns true if this is the root record */
  isRootRecord () {
    return this.getRecordPath() === ''
  }

  /* returns the breadcrumbs for the current record path */
  getRecordCrumbs () {
    const segments = this.getRecordPathSegments()
    if (segments === null) {
      return []
    }

    segments.unshift('root')

    const rv = []
    for (let i = 0; i < segments.length; i++) {
      const curpath = segments.slice(0, i + 1).join(':')
      rv.push({
        id: 'path:' + curpath,
        urlPath: curpath,
        segments: segments.slice(1, i + 1),
        title: segments[i]
      })
    }

    return rv
  }
}

export default RecordComponent
