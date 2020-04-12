# Check if files ending in .py changed on the current PR
BASE_REF=test1=$(git rev-parse origin/$GITHUB_BASE_REF)
HEAD_REF=$(git rev-parse origin/$GITHUB_HEAD_REF)
result=$(git diff --name-only $test1 $test2 | grep -c ".*\.py")

if [[ $result != '0' ]]; then 
  echo "Files including the filter: $result"
  echo ::set-output name=PY_SKIP::true
else
  echo ::set-output name=PY_SKIP::false
fi
