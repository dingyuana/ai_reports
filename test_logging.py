
import os
import sys

# Add current directory to path
sys.path.append(os.getcwd())

from log_manager import log_manager
from database import init_db_pool, close_db_pool

# Initialize DB pool
init_db_pool()

try:
    print("Attempting to log action...")
    log_manager.log_action(
        user_id=1,  # Assuming user ID 1 exists (admin usually)
        action="test_log",
        details="This is a test log entry"
    )
    print("Log action called.")

    # Check if it was inserted
    logs = log_manager.get_all_logs(limit=1)
    if logs and logs[0][2] == "test_log":
        print("Log verification successful!")
        print(f"Log entry: {logs[0]}")
    else:
        print("Log verification failed. Latest log is not the test log.")
        if logs:
            print(f"Latest log: {logs[0]}")
        else:
            print("No logs found.")

except Exception as e:
    print(f"An error occurred: {e}")
finally:
    close_db_pool()
