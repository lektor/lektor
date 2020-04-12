# Check if files ending in .js changed on the current PR
BASE_REF=test1=$(git rev-parse origin/$GITHUB_BASE_REF)
HEAD_REF=$(git rev-parse origin/$GITHUB_HEAD_REF)
result=$(git diff --name-only $test1 $test2 | grep -c ".*\.js.*")

echo "Files including the filter: $result"
if [[ $result != '0' ]]; then 
  echo "Skip JS!"
  echo ::set-output name=RUN_BUILD_JS::false
else
  echo "All good!"
  echo ::set-output name=RUN_BUILD_JS::true
fi
