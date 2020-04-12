#!/bin/bash -ex

# Check if files ending in .js changed on the current PR
result=$(git diff --name-only $BASE_BRANCH | grep -c ".*\.jsx?")
if [[ $result != '0' ]]; then 
  echo 'Files including the filter: $result'
  echo "::set-output name=JS_SKIP::true"
else
  echo "::set-output name=JS_SKIP::false"
fi
