#!/bin/bash -ex

# Check if files ending in .py changed on the current PR
result=$(git diff --name-only $BASE_BRANCH | grep -c ".*\.py")
if [[ $result != '0' ]]; then 
  echo 'Files including the filter: $result'
  echo "::set-output name=PYTHON_SKIP::true"
else
  echo "::set-output name=PYTHON_SKIP::false"
fi
