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


def write_output(text, stdout_redirect=None, stderr_redirect=None, append=False):
    """Writes text to redirected file or prints to stdout. 
    This is typically used for builtin commands' output (stdout)."""
    if stdout_redirect:
        os.makedirs(os.path.dirname(stdout_redirect), exist_ok=True)
        mode = "a" if append else "w"
        with open(stdout_redirect, mode) as f:
            # Add newline only if not already present
            f.write(text + ("\n" if not text.endswith("\n") else ""))
        return
    elif stderr_redirect:
        # If a built-in's *error* is being written, use stderr_redirect
        os.makedirs(os.path.dirname(stderr_redirect), exist_ok=True)
        with open(stderr_redirect, "w") as f:
            f.write(text + ("\n" if not text.endswith("\n") else ""))
        return
    else:
        print(text, flush=True)


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
        if not parts:
            continue
        # cmd = parts[0] # Defined later after token removal


        # --- Handle output redirection early ---
        stdout_redirect = None
        stderr_redirect = None
        stdout_append = False  # track if it's append mode
        
        # Keep track of which indices to remove
        tokens_to_remove = []

        # Check for stderr redirection (2>)
        if "2>" in parts:
            op_index = parts.index("2>")
            if op_index + 1 < len(parts):
                stderr_redirect = parts[op_index + 1]
                tokens_to_remove.extend([op_index, op_index + 1])
            else:
                print("syntax error: no file after redirection operator")
                continue

        # Handle stdout redirection (overwrite & append)
        # 1. Detect append redirection first (>> or 1>>)
        if ">>" in parts or "1>>" in parts:
            if "1>>" in parts:
                op_index = parts.index("1>>")
            else:
                op_index = parts.index(">>")

            if op_index + 1 < len(parts):
                stdout_redirect = parts[op_index + 1]
                stdout_append = True  # enable append mode
                tokens_to_remove.extend([op_index, op_index + 1])
            else:
                print("syntax error: no file after redirection operator")
                continue

        # stdout overwrite (>, 1>)
        elif ">" in parts or "1>" in parts:
            op_index = parts.index("1>") if "1>" in parts else parts.index(">")
            if op_index + 1 < len(parts):
                stdout_redirect = parts[op_index + 1]
                tokens_to_remove.extend([op_index, op_index + 1])
            else:
                print("syntax error: missing file after >")
                continue
                
        # Remove redirection tokens from the parts list
        # Remove them in reverse order to keep indices correct
        if tokens_to_remove:
            tokens_to_remove.sort(reverse=True)
            for index in tokens_to_remove:
                parts.pop(index)

        if not parts:
            continue
        cmd = parts[0]

        # --- FIX: Ensure redirection files/directories exist for all commands (especially built-ins) ---
        if stdout_redirect:
            if os.path.dirname(stdout_redirect):
                 os.makedirs(os.path.dirname(stdout_redirect), exist_ok=True)
            # For overwrite (> or 1>), explicitly create the file here to ensure it exists and is truncated.
            if not stdout_append:
                try:
                    open(stdout_redirect, "w").close()
                except Exception as e:
                    print(f"shell: failed to create file {stdout_redirect}: {e}")
                    continue
                 
        if stderr_redirect:
            if os.path.dirname(stderr_redirect):
                 os.makedirs(os.path.dirname(stderr_redirect), exist_ok=True)
            try:
                # Create and truncate the file for stderr redirection, ensuring it exists for the test.
                open(stderr_redirect, "w").close()
            except Exception as e:
                print(f"shell: failed to create file {stderr_redirect}: {e}")
                continue

        # --- Handle builtins ---
        # --- Handle 'exit' command ---
        if cmd == "exit":
            exit_code = 0
            if len(parts) > 1:
                try:
                    exit_code = int(parts[1])
                except ValueError:
                    exit_code = 1
            sys.exit(exit_code)


        # --- Handle 'echo' command (Quote Stripping REMOVED) ---
        if cmd == "echo":
            msg = " ".join(parts[1:])
            
            # The manual quote stripping logic was removed to fix Stage #YT5.

            # Echo's normal output is always stdout. 
            if stdout_redirect:
                mode = "a" if stdout_append else "w"
                with open(stdout_redirect, mode) as f:
                    f.write(msg + ("\n" if not msg.endswith("\n") else ""))
            else:
                print(msg, flush=True)
            continue


        # --- Handle 'type' command ---
        if cmd == 'type':
            if len(parts) < 2:
                continue
            builtin_commands = ["exit", "echo", "type", "pwd", "cd"]
            target = parts[1]
            if target in builtin_commands:
                output = f"{target} is a shell builtin"
            else:
                path = find_executable(target)
                if path:
                    output = f"{target} is {path}"
                else:
                    output = f"{target}: not found"
            write_output(output, stdout_redirect, stderr_redirect, stdout_append)
            continue


        # --- Handle 'pwd' comment ---
        if cmd == "pwd":
            current_directory = os.getcwd()
            write_output(current_directory, stdout_redirect, stderr_redirect, stdout_append)
            continue


        # --- Handle 'cd' comment ---
        if cmd == "cd":
            if len(parts) < 2:
                continue
            target_dir = parts[1]
            if target_dir == "~" or target_dir.startswith("~/"):
                target_dir = os.path.expanduser(target_dir)
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
                stdout_target = open(stdout_redirect, "a" if stdout_append else "w") if stdout_redirect else None
                stderr_target = open(stderr_redirect, "w") if stderr_redirect else None
                
                # --- FIX FOR STAGE #IP1 ---
                # Pass the simple command name (cmd) as the first argument in the list (argv[0]),
                # and use the 'executable' parameter to specify the full path of the program to run.
                args_for_program = [cmd] + parts[1:] 

                subprocess.run(
                    args_for_program,  # The list of arguments, starting with 'custom_exe_9708'
                    executable=full_path, # Tells the OS to run the found full path
                    stdout=stdout_target or sys.stdout,
                    stderr=stderr_target or sys.stderr
                )

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