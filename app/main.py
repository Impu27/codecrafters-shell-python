import sys
import os
import subprocess
import shlex

# 1. Initialize a global list to store command history
command_history = [] 

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
        # --- UPDATE FOR STAGE 2>> ---
        # If a built-in's *error* is being written, use stderr_redirect
        os.makedirs(os.path.dirname(stderr_redirect), exist_ok=True)
        # Use append mode ('a') if the append flag is True, otherwise use overwrite ('w').
        mode = "a" if append else "w"
        with open(stderr_redirect, mode) as f:
            f.write(text + ("\n" if not text.endswith("\n") else ""))
        return
    else:
        print(text, flush=True)


def main():
    while True:
        # READ
        sys.stdout.write("$ ")
        sys.stdout.flush() 
        try:
            # We read the original, unparsed command for history recording
            command = input()
            command_stripped = command.strip()
        except EOFError:
            break
        except KeyboardInterrupt:
            sys.stdout.write("\n")
            continue

        if command_stripped == "":
            continue

        # 2. Record the command before parsing/redirection logic
        # Record only non-empty commands.
        command_history.append(command_stripped)

        try:
            parts = shlex.split(command_stripped)
        except ValueError as e:
            print(f"Error parsing command: {e}")
            continue
        if not parts:
            continue

        # --- Handle output redirection early ---
        stdout_redirect = None
        stderr_redirect = None
        stdout_append = False  
        stderr_append = False  # <--- NEW FLAG for 2>>
        
        tokens_to_remove = []

        # Check for stderr append redirection (2>>) <--- NEW BLOCK
        if "2>>" in parts:
            op_index = parts.index("2>>")
            if op_index + 1 < len(parts):
                stderr_redirect = parts[op_index + 1]
                stderr_append = True # Set flag for append mode
                tokens_to_remove.extend([op_index, op_index + 1])
            else:
                print("syntax error: no file after redirection operator")
                continue

        # Check for stderr overwrite redirection (2>)
        elif "2>" in parts:
            op_index = parts.index("2>")
            if op_index + 1 < len(parts):
                stderr_redirect = parts[op_index + 1]
                tokens_to_remove.extend([op_index, op_index + 1])
            else:
                print("syntax error: no file after redirection operator")
                continue

        # Handle stdout append (>> or 1>>)
        if ">>" in parts or "1>>" in parts:
            if "1>>" in parts:
                op_index = parts.index("1>>")
            else:
                op_index = parts.index(">>")

            if op_index + 1 < len(parts):
                stdout_redirect = parts[op_index + 1]
                stdout_append = True
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
                
        # Remove redirection tokens
        if tokens_to_remove:
            tokens_to_remove.sort(reverse=True)
            for index in tokens_to_remove:
                parts.pop(index)

        if not parts:
            continue
        cmd = parts[0]

        # --- File and Directory Setup ---
        # This section ensures directories exist and truncates overwrite files immediately.
        if stdout_redirect:
            if os.path.dirname(stdout_redirect):
                 os.makedirs(os.path.dirname(stdout_redirect), exist_ok=True)
            if not stdout_append:
                try:
                    open(stdout_redirect, "w").close()
                except Exception as e:
                    print(f"shell: failed to create file {stdout_redirect}: {e}")
                    continue
                 
        if stderr_redirect:
            if os.path.dirname(stderr_redirect):
                 os.makedirs(os.path.dirname(stderr_redirect), exist_ok=True)
            # Only truncate for OVERWRITE (2>), not APPEND (2>>)
            if not stderr_append: 
                try:
                    open(stderr_redirect, "w").close()
                except Exception as e:
                    print(f"shell: failed to create file {stderr_redirect}: {e}")
                    continue

        # --- Handle builtins ---
        if cmd == "exit":
            exit_code = 0
            if len(parts) > 1:
                try: exit_code = int(parts[1])
                except ValueError: exit_code = 1
            sys.exit(exit_code)

        if cmd == "echo":
            msg = " ".join(parts[1:])
            # Note: We can reuse write_output for echo, but the existing code is fine too
            if stdout_redirect:
                mode = "a" if stdout_append else "w"
                with open(stdout_redirect, mode) as f:
                    f.write(msg + ("\n" if not msg.endswith("\n") else ""))
            else:
                print(msg, flush=True)
            continue


        if cmd == 'type':
            if len(parts) < 2: continue
            # 4. Add "history" to the list of builtins
            builtin_commands = ["exit", "echo", "type", "pwd", "cd", "history"]
            target = parts[1]
            if target in builtin_commands:
                output = f"{target} is a shell builtin"
            else:
                path = find_executable(target)
                if path: output = f"{target} is {path}"
                else: output = f"{target}: not found"
            
            # Note: built-in success output is stdout. We use the stdout_append flag here.
            write_output(output, stdout_redirect, stderr_redirect, stdout_append) 
            continue


        if cmd == "pwd":
            current_directory = os.getcwd()
            write_output(current_directory, stdout_redirect, stderr_redirect, stdout_append)
            continue


        if cmd == "cd":
            if len(parts) < 2: 
                # According to common shell behavior, 'cd' without arguments usually
                # goes to the home directory. We'll skip for now if no argument.
                continue 
            target_dir = parts[1]
            if target_dir == "~" or target_dir.startswith("~/"):
                target_dir = os.path.expanduser(target_dir)
            if not os.path.isdir(target_dir):
                # Errors should go to stderr, but for this project, builtins typically print to stdout/print
                print(f"cd: {target_dir}: No such file or directory") 
                continue
            try:
                os.chdir(target_dir)
            except Exception as e:
                print(f"cd: {target_dir}: {e}")
            continue

        # 3. Implement the history builtin
        if cmd == "history":
            history_output = ""
            # command_history is 1-indexed for display
            for i, entry in enumerate(command_history, 1):
                # Format: "    1  command"
                history_output += f"{i:5}  {entry}\n" 
            
            # Write to stdout, respecting redirection
            # write_output handles the final newline if not present, but our loop adds it.
            # We remove the trailing newline if present before calling write_output
            write_output(history_output.rstrip("\n"), stdout_redirect, stderr_redirect, stdout_append)
            continue


        # --- Handle external programs ---
        full_path = find_executable(cmd)
        if full_path:
            try:
                # Open stdout target: 'a' if stdout_append, 'w' otherwise
                stdout_target = open(stdout_redirect, "a" if stdout_append else "w") if stdout_redirect else None
                
                # --- UPDATE FOR STAGE 2>> ---
                # Determine stderr mode: 'a' if stderr_append, 'w' otherwise.
                stderr_mode = "a" if stderr_append else "w"
                stderr_target = open(stderr_redirect, stderr_mode) if stderr_redirect else None
                
                args_for_program = [cmd] + parts[1:] 

                subprocess.run(
                    args_for_program, 
                    executable=full_path, 
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
        print(f"{command_stripped}: command not found")
    


if __name__ == "__main__":
    main()