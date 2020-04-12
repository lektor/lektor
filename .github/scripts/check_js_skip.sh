# Check if files ending in .js changed on the current PR

BASE_REF=test1=$(git rev-parse origin/$GITHUB_BASE_REF)
HEAD_REF=$(git rev-parse origin/$GITHUB_HEAD_REF)
result=$(git diff --name-only $test1 $test2 | grep -c ".*\.js.*")

if [[ $result != '0' ]]; then 
  echo "Files including the filter: $result"
  echo "::set-output name=JS_SKIP::true"
else
  echo "::set-output name=JS_SKIP::false"
fi
