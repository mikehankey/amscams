import subprocess

def get_processes_by_user(username):
    # Execute the ps command
    result = subprocess.run(['ps', '-eo', 'user,pid,etime,cmd', '--sort=start_time'], capture_output=True, text=True)
    # Check if the command was successful
    if result.returncode != 0:
        print("Error executing ps command")
        return []
    
    # Split the output into lines
    lines = result.stdout.splitlines()
    
    # Parse the header to get the column indices
    header = lines[0].split()
    user_idx = header.index('USER')
    pid_idx = header.index('PID')
    etime_idx = header.index('ELAPSED')
    cmd_idx = header.index('CMD')
    
    # Initialize an array to hold process information
    processes = []
    
    # Parse each line
    for line in lines[1:]:
        parts = line.split(None, 3)  # Split the line into at most 4 parts
        if parts[user_idx] == username:
            process_info = {
                'user': parts[user_idx],
                'pid': parts[pid_idx],
                'etime': parts[etime_idx],
                'cmd': parts[cmd_idx] if len(parts) > 3 else ''
            }
            processes.append(process_info)
    return processes

# Example usage
username = 'ams'
processes = get_processes_by_user(username)

# Print the processes
for process in processes:
    if "-" in process['etime']:
        print("Process running for >1 day", process)
