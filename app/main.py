import sys
import os
import subprocess
import shlex


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
        # --- UPDATED: Use shlex for proper quote parsing ---
        try:
            parts = shlex.split(command)
        except ValueError as e:
            print(f"Error parsing command: {e}")
            continue
        cmd = parts[0]


        # --- Handle output redirection early ---
        stdout_redirect = None
        stderr_redirect = None
        stdout_append = False  # track if it's append mode
        #Check for stderr
        if "2>" in parts:
            op_index = parts.index("2>")
            if op_index + 1 < len(parts):
                stderr_redirect = parts[op_index + 1]
                parts = parts[:op_index] #remove redirection tokens
            else:
                print("syntax error: no file after redirection operator")
                continue

        # --- Handle stdout redirection (overwrite & append) ---
        # 1. Detect append redirection first (>> or 1>>)
        if ">>" in parts or "1>>" in parts:
            if "1>>" in parts:
                op_index = parts.index("1>>")
            else:
                op_index = parts.index(">>")

            if op_index + 1 < len(parts):
                stdout_redirect = parts[op_index + 1]
                stdout_append = True  # enable append mode
                parts = parts[:op_index]  # remove tokens
            else:
                print("syntax error: no file after redirection operator")
                continue

        # 2. Detect normal overwrite redirection (>, 1>)
        elif ">" in parts or "1>" in parts:
            if "1>" in parts:
                op_index = parts.index("1>")
            else:
                op_index = parts.index(">")

            if op_index + 1 < len(parts):
                stdout_redirect = parts[op_index + 1]
                parts = parts[:op_index]
            else:
                print("syntax error: no file after redirection operator")
                continue


        if not parts:
            continue
        cmd = parts[0]


        # --- Handle builtins ---
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
            echo_str = " ".join(parts[1:])
            if stdout_redirect:
                mode = "a" if stdout_append else "w"
                with open(stdout_redirect, mode) as f:
                    f.write(echo_str + "\n")
            else:
                print(echo_str)
            continue


        # --- Handle 'type' command ---
        if cmd == 'type':
            if len(parts) < 2:
                continue
            builtin_commands = ["exit", "echo", "type", "pwd", "cd"]
            target = parts[1]
            # 1) Check if it's a builtin
            if target in builtin_commands:
                output = f"{target} is a shell builtin"
            # 2) Otherwise, check in PATH
            else:
                path = find_executable(target)
                if path:
                    output = f"{target} is {path}"
                else:
                    output = f"{target}: not found"
            if stdout_redirect:
                mode = "a" if stdout_append else "w"
                with open(stdout_redirect, mode) as f:
                    f.write(output + "\n")
            else:
                print(output)
            continue


        # --- Handle 'pwd' comment ---
        if cmd == "pwd":
            current_directory = os.getcwd()
            if stdout_redirect:
                mode = "a" if stdout_append else "w"
                with open(stdout_redirect, mode) as f:
                    f.write(current_directory + "\n")
            else:
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
                # Choose correct mode for stdout
                stdout_target = None
                stderr_target = None

                if stdout_redirect:
                    mode = "a" if stdout_append else "w"
                    stdout_target = open(stdout_redirect, mode)
                if stderr_redirect:
                    stderr_target = open(stderr_redirect, "w")

                subprocess.run(
                    parts,
                    stdout=stdout_target or sys.stdout,
                    stderr=stderr_target or sys.stderr
                )

                # Close files after use
                if stdout_target:
                    stdout_target.close()
                if stderr_target:
                    stderr_target.close()

            except Exception as e:
                print(f"Error executing {cmd}: {e}")
            continue
        


        # PRINT for Unknown command
        print(f"{command}: command not found")
    


if __name__ == "__main__":
    main()
