# Check if files ending in .js changed on the current PR
BASE_REF=$(git rev-parse origin/$GITHUB_BASE_REF)
HEAD_REF=$(git rev-parse HEAD)
echo "base: $BASE_REF"
echo "head: $HEAD_REF"
FILES=$(git diff --name-only $BASE_REF $HEAD_REF)
COUNT=$(echo $FILES | grep -c ".*\.js.*")

echo "Files including the filter: $FILES"
echo "JS files filter count: $COUNT"

if [[ $COUNT == '0' ]]; then 
  echo "Skip JS!"
  echo "::set-env name=RUN_BUILD_JS::false"
else
  echo "Run JS!"
  echo "::set-env name=RUN_BUILD_JS::true"
fi

echo " "
