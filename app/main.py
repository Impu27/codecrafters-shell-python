import sys
import os
import subprocess
import shlex
import readline # <--- NEW IMPORT


# --- 1. Autocompletion Logic ---
BUILTIN_COMMANDS = ["exit", "echo", "type", "pwd", "cd"] # List of commands to complete

def shell_completer(text, state):
    """
    Custom completer function for readline.
    'text' is the word currently being typed by the user (e.g., 'ech').
    'state' is used by readline to get multiple matches (0 for the first, 1 for the second, etc.).
    """
    
    # Filter the list of built-in commands to find matches
    matches = [cmd for cmd in BUILTIN_COMMANDS if cmd.startswith(text)]
    
    # readline calls this function repeatedly, incrementing 'state'.
    # When state is 0, return the first match. When state is 1, return the second, and so on.
    if state < len(matches):
        # The tester explicitly requires a space after the completed command.
        return matches[state] + " "
    else:
        return None # No more matches found

def setup_readline():
    """Configures readline for autocompletion."""
    # Set the custom completer function
    readline.set_completer(shell_completer)
    
    # Configure readline to automatically use the completer function on Tab press
    # 'tab: complete' is the standard binding for Tab to initiate completion
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
    # --- 2. Setup Readline before the loop starts ---
    setup_readline()
    
    while True:
        # READ
        # print() is safer than sys.stdout.write() when using readline
        try:
            # readline automatically handles prompt display, input, and TAB completion
            command = input("$ ").strip() 
        except EOFError:
            break
        except KeyboardInterrupt:
            # Readline typically handles this more cleanly, but keep for robustness
            sys.stdout.write("\n")
            continue

        if command == "":
            continue
        # --- (Rest of the command execution logic remains the same) ---
        
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