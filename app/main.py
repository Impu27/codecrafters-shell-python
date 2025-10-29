import sys
import os
import subprocess

"""Searches for an executable in all directories listed in PATH.
Returns the full path if found and executable, otherwise None."""
def find_executable(program):
    path_dirs = os.environ.get("PATH", "").split(os.pathsep)
    for directory in path_dirs:
        full_path = os.path.join(directory, program)
        if os.path.isfile(full_path) and os.access(full_path, os.X_OK):
            return full_path
    return None


def main():
    while True:
        # READ
        sys.stdout.write("$ ")
        sys.stdout.flush() # ensures the prompt appears immediately
        try:
            #wait for user input
            command = input().strip()
        except EOFError:
            # When user presses Ctrl+D, gracefully exit
            break
        except KeyboardInterrupt:
            # Handle Ctrl+C gracefully
            sys.stdout.write("\n")
            continue

        if command == "":
            # Empty input: just show prompt again
            continue
        # EVAL
        #splitting command into words(for handling arguments)
        parts = command.split()
        cmd = parts[0]


        # --- Handle 'exit' command ---
        if cmd == "exit":
            #default exit code = 0
            exit_code = 0
            # If user gave an argument like 'exit 1'
            if len(parts) > 1:
                try:
                    exit_code = int(parts[1])
                except ValueError:
                    # If not a valid number, default to 1 (error)
                    exit_code = 1
            # Exit the shell immediately
            sys.exit(exit_code)


        # --- Handle 'echo' command ---
        if cmd == "echo":
            echoString = " ".join(parts[1:])
            print(echoString)
            continue


        # --- Handle 'type' command ---
        if cmd == 'type':
            if len(parts) < 2:
                continue
            builtin_commands = ["exit", "echo", "type", "pwd", "cd"]
            target = parts[1]
            # 1) Check if it's a builtin
            if target in builtin_commands:
                print(f"{parts[1]} is a shell builtin")
                continue

            # 2️⃣ Otherwise, check in PATH
            path_dirs = os.environ.get("PATH", "").split(os.pathsep)
            found = False
            for directory in path_dirs:
                full_path = os.path.join(directory, target)
                if os.path.isfile(full_path) and os.access(full_path, os.X_OK):
                    print(f"{target} is {full_path}")
                    found = True
                    break

            if not found:
                print(f"{parts[1]}: not found")
            continue


        # --- Handle 'pwd' comment ---
        if cmd == "pwd":
            current_directory = os.getcwd()
            print(current_directory)
            continue


        # --- Handle 'cd' comment ---
        if cmd == "cd":
            # Check if argument is provided
            if len(parts) < 2:
                # No path given (optional for later stages)
                # Usually defaults to the home directory, but we’ll skip that for now
                continue
            target_dir = parts[1]
            # Handle '~' expansion first
            if target_dir == "~" or target_dir.startswith("~/"):
                target_dir = os.path.expanduser(target_dir)
            # Check if the directory exists
            if not os.path.isdir(target_dir):
                print(f"cd: {target_dir}: No such file or directory")
                continue
            try:
                os.chdir(target_dir)
            except Exception as e:
                print(f"cd: {target_dir}: {e}")
            continue



         # --- Handle external programs ---
        full_path = find_executable(cmd)
        if full_path:
            try:
                # Run the external program with its arguments
                subprocess.run(parts)
            except Exception as e:
                print(f"Error executing {cmd}: {e}")
            continue


        # PRINT for Unknown command
        print(f"{command}: command not found")
    


if __name__ == "__main__":
    main()
