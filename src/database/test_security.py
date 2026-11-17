
from query_runner import execute_read_only

# Valid query
valid = execute_read_only("select * from students limit 3")
print("SELECT:", valid["success"])

# Modification attempt
invalid = execute_read_only("delete from students")
print("DELETE:", invalid["success"])

# Multiple statement attempt
multiple = execute_read_only("select * from students; delete from students")
print("MULTIPLE:", multiple["success"])
