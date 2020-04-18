/* eslint-env mocha */
import { deepStrictEqual } from 'assert'
import { getRecordPathAndAlt } from './RecordComponent'

describe('Get Record paths', () => {
  it('Get Record path and alt', () => {
    deepStrictEqual(getRecordPathAndAlt(), [null, null])
    deepStrictEqual(getRecordPathAndAlt('root:about'), ['/about', undefined])
    deepStrictEqual(getRecordPathAndAlt('root+fr'), ['', 'fr'])
    deepStrictEqual(getRecordPathAndAlt('root:blog+fr'), ['/blog', 'fr'])
  })
})
