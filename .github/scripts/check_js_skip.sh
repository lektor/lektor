# Check if files ending in .js changed on the current PR

test1=$(git rev-parse origin/$GITHUB_BASE_REF)
test2=$(git rev-parse origin/$GITHUB_HEAD_REF)
result=$(git diff --name-only $test1 $test2)
echo $test1
echo $test2
echo $result

if [[ $result != '0' ]]; then 
  echo "Files including the filter: $result"
  echo "::set-output name=JS_SKIP::true"
else
  echo "::set-output name=JS_SKIP::false"
fi
