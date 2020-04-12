# Get text for last commit
last_commit_text="$(git log -1 --pretty=format:%s)"
echo "Last commit text: $last_commit_text"

# Use a regex and grep to count found patterns
result=$(echo $last_commit_text | grep -c -E "\[ci skip\]|\[skip ci\]")
echo "Count: $result"

if [[ $result != '0' ]]; then 
  echo 'Skipping build!'
  echo 'Commits including the filter: $result'
  echo "::set-output name=SKIP::true"
else
  echo 'All good!'
  echo "::set-output name=SKIP::false"
fi
