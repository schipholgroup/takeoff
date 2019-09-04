
echo "-- Databricks                   --"
echo "Find databricks run"
if [ "$(grep -c "Found Job with ID 1" logs)" != 1 ]
then
  exit_out
fi

echo "Cancel databricks run"
if [ "$(grep -c "Canceling active runs" logs)" != 1 ]
then
  exit_out
fi

echo "Delete databricks job"
if [ "$(grep -c "Deleting Job with ID 1" logs)" != 1 ]
then
  exit_out
fi

echo "Create databricks job"
if [ "$(grep -c "Created Job with ID 1" logs)" != 1 ]
then
  exit_out
fi

echo "Create databricks run"
if [ "$(grep -c "Created run with ID 43" logs)" != 1 ]
then
  exit_out
fi
