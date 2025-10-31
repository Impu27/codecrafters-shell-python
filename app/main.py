import sys
import os
import subprocess
import shlex
import readline 


# --- 1. Autocompletion Logic ---
BUILTIN_COMMANDS = ["exit", "echo", "type", "pwd", "cd"] # List of commands to complete

def find_all_executables_with_prefix(prefix):
    """
    Searches all directories in PATH for executable files starting with the given prefix.
    """
    path_dirs = os.environ.get("PATH", "").split(os.pathsep)
    matches = set() # Use a set to avoid duplicates

    for directory in path_dirs:
        # Handle cases where PATH includes non-existent directories gracefully
        if not os.path.isdir(directory):
            continue
            
        try:
            # List all entries in the directory
            for item_name in os.listdir(directory):
                # Check if the item starts with the prefix
                if item_name.startswith(prefix):
                    full_path = os.path.join(directory, item_name)
                    # Check if the item is a regular file AND is executable
                    if os.path.isfile(full_path) and os.access(full_path, os.X_OK):
                        matches.add(item_name)
        except OSError:
            # Ignore directories we can't read
            continue
            
    return sorted(list(matches)) # Return a sorted list of unique external commands


def shell_completer(text, state):
    """
    Custom completer function for readline.
    """
    
    # 1. Check Built-ins
    builtin_matches = [cmd for cmd in BUILTIN_COMMANDS if cmd.startswith(text)]
    
    # 2. Check External Executables
    external_matches = find_all_executables_with_prefix(text)
    
    # 3. Combine and sort all matches
    all_matches = sorted(list(set(builtin_matches + external_matches)))
    
    # 4. Handle Bell Character (if no matches are found)
    if not all_matches and state == 0:
        sys.stdout.write('\x07')
        sys.stdout.flush()
        return None
    
    # 5. Return the match based on the state
    if state < len(all_matches):
        # Return the completed command plus a space
        return all_matches[state] + " "
    else:
        return None # No more matches found

def setup_readline():
    """Configures readline for autocompletion."""
    readline.set_completer(shell_completer)
    readline.parse_and_bind("tab: complete")

# --- End of Autocompletion Logic ---


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
        os.makedirs(os.path.dirname(stderr_redirect), exist_ok=True)
        mode = "a" if append else "w"
        with open(stderr_redirect, mode) as f:
            f.write(text + ("\n" if not text.endswith("\n") else ""))
        return
    else:
        print(text, flush=True)


def main():
    setup_readline()
    
    while True:
        try:
            command = input("$ ").strip() 
        except EOFError:
            break
        except KeyboardInterrupt:
            sys.stdout.write("\n")
            continue

        if command == "":
            continue
        try:
            parts = shlex.split(command)
        except ValueError as e:
            print(f"Error parsing command: {e}")
            continue
        if not parts:
            continue
        
        stdout_redirect = None
        stderr_redirect = None
        stdout_append = False  
        stderr_append = False  
        tokens_to_remove = []

        # Check for stderr append redirection (2>>)
        if "2>>" in parts:
            op_index = parts.index("2>>")
            if op_index + 1 < len(parts):
                stderr_redirect = parts[op_index + 1]
                stderr_append = True 
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
            if stdout_redirect:
                mode = "a" if stdout_append else "w"
                with open(stdout_redirect, mode) as f:
                    f.write(msg + ("\n" if not msg.endswith("\n") else ""))
            else:
                print(msg, flush=True)
            continue


        if cmd == 'type':
            if len(parts) < 2: continue
            target = parts[1]
            if target in BUILTIN_COMMANDS:
                output = f"{target} is a shell builtin"
            else:
                path = find_executable(target)
                if path: output = f"{target} is {path}"
                else: output = f"{target}: not found"
            
            write_output(output, stdout_redirect, stderr_redirect, stdout_append) 
            continue


        if cmd == "pwd":
            current_directory = os.getcwd()
            write_output(current_directory, stdout_redirect, stderr_redirect, stdout_append)
            continue


        if cmd == "cd":
            if len(parts) < 2: continue
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
        print(f"{command}: command not found")
    


if __name__ == "__main__":
    main()