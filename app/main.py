import sys
import os
import subprocess
import shlex
import readline 


# --- Global State for Double-Tab Logic ---
_TAB_PRESSED_COUNT = 0
_LAST_COMPLETION_TEXT = ""


# --- LCP Helper ---
def get_longest_common_prefix(strs):
    """
    Finds the longest common prefix among a list of strings.
    """
    if not strs:
        return ""
    
    # Sort the list to easily compare the shortest and longest strings
    strs.sort()
    s1 = strs[0]
    s2 = strs[-1]
    
    prefix = ""
    for i in range(len(s1)):
        if i < len(s2) and s1[i] == s2[i]:
            prefix += s1[i]
        else:
            break
    return prefix


# --- Autocompletion Logic ---
BUILTIN_COMMANDS = ["exit", "echo", "type", "pwd", "cd"] 

def find_all_executables_with_prefix(prefix):
    """
    Searches all directories in PATH for executable files starting with the given prefix.
    """
    path_dirs = os.environ.get("PATH", "").split(os.pathsep)
    matches = set()

    for directory in path_dirs:
        if not os.path.isdir(directory):
            continue
            
        try:
            for item_name in os.listdir(directory):
                if item_name.startswith(prefix):
                    full_path = os.path.join(directory, item_name)
                    if os.path.isfile(full_path) and os.access(full_path, os.X_OK):
                        matches.add(item_name)
        except OSError:
            continue
            
    return sorted(list(matches))


def shell_completer(text, state):
    """
    Custom completer function for readline, now supporting Longest Common Prefix (LCP) completion.
    """
    global _TAB_PRESSED_COUNT, _LAST_COMPLETION_TEXT

    if text != _LAST_COMPLETION_TEXT:
        _TAB_PRESSED_COUNT = 0
    _LAST_COMPLETION_TEXT = text
    
    # 1. Gather all matches
    builtin_matches = [cmd for cmd in BUILTIN_COMMANDS if cmd.startswith(text)]
    external_matches = find_all_executables_with_prefix(text)
    all_matches = sorted(list(set(builtin_matches + external_matches)))
    
    if not all_matches:
        if state == 0:
            sys.stdout.write('\a')
            sys.stdout.flush()
        return None
        
    # LCP Completion Logic (Runs only on the first call: state == 0)
    if state == 0 and len(all_matches) > 1:
        lcp = get_longest_common_prefix(all_matches)
        
        # If the LCP extends the current text, return the LCP. 
        if len(lcp) > len(text):
            return lcp
        # else: LCP is the same as the input (e.g., input "xyz_foo" matches 
        # "xyz_foo" and "xyz_foo_bar"). Fall through to state logic to trigger hook.
            
    # Standard readline completion (single match, or iterating over matches for the hook)
    if state < len(all_matches):
        match = all_matches[state]
        
        # If there's only one unique match, complete it with a trailing space.
        if len(all_matches) == 1:
            return match + " "
            
        # For multiple ambiguous matches (or LCP couldn't extend), 
        # return the match without a space to trigger the hook on subsequent tabs.
        return match
    else:
        return None


def display_matches_hook(substitution_text, matches, longest_match_length):
    """
    Custom hook to handle the display of multiple ambiguous matches (on double-tab).
    """
    global _TAB_PRESSED_COUNT, _LAST_COMPLETION_TEXT
    
    _TAB_PRESSED_COUNT += 1
    
    # 1. First TAB press: Ring the bell.
    if _TAB_PRESSED_COUNT == 1:
        sys.stdout.write('\a')
        sys.stdout.flush()
        
    # 2. Second TAB press: Print the list and redraw the prompt.
    elif _TAB_PRESSED_COUNT == 2:
        sys.stdout.write('\n')
        list_output = "  ".join(matches)
        sys.stdout.write(list_output + '\n') 
        sys.stdout.write(f"$ {_LAST_COMPLETION_TEXT}")
        sys.stdout.flush()

    if _TAB_PRESSED_COUNT > 2:
        _TAB_PRESSED_COUNT = 0


def setup_readline():
    """Configures readline for autocompletion."""
    readline.set_completer(shell_completer)
    readline.set_completion_display_matches_hook(display_matches_hook)
    readline.parse_and_bind("tab: complete")
    
    # Ensure TAB completion is always initiated (especially relevant for LCP when LCP=text)
    # The default behavior for "tab: complete" usually includes LCP calculation.
    # The crucial part is our completer returning the LCP explicitly.


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
    """Writes text to redirected file or prints to stdout."""
    if stdout_redirect:
        os.makedirs(os.path.dirname(stdout_redirect), exist_ok=True)
        mode = "a" if append else "w"
        with open(stdout_redirect, mode) as f:
            text = text + ("\n" if not text.endswith("\n") else "")
            f.write(text)
        return
    elif stderr_redirect:
        os.makedirs(os.path.dirname(stderr_redirect), exist_ok=True)
        mode = "a" if append else "w"
        with open(stderr_redirect, mode) as f:
            text = text + ("\n" if not text.endswith("\n") else "")
            f.write(text)
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
        
        # Reset TAB counter after a command is executed
        global _TAB_PRESSED_COUNT
        _TAB_PRESSED_COUNT = 0 
        
        stdout_redirect = None
        stderr_redirect = None
        stdout_append = False  
        stderr_append = False  
        tokens_to_remove = []

        # --- Redirection Logic (omitted for brevity, remains unchanged) ---
        if "2>>" in parts:
            op_index = parts.index("2>>")
            if op_index + 1 < len(parts):
                stderr_redirect = parts[op_index + 1]
                stderr_append = True 
                tokens_to_remove.extend([op_index, op_index + 1])
            else:
                print("syntax error: no file after redirection operator")
                continue
        elif "2>" in parts:
            op_index = parts.index("2>")
            if op_index + 1 < len(parts):
                stderr_redirect = parts[op_index + 1]
                tokens_to_remove.extend([op_index, op_index + 1])
            else:
                print("syntax error: no file after redirection operator")
                continue
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
        elif ">" in parts or "1>" in parts:
            op_index = parts.index("1>") if "1>" in parts else parts.index(">")
            if op_index + 1 < len(parts):
                stdout_redirect = parts[op_index + 1]
                tokens_to_remove.extend([op_index, op_index + 1])
            else:
                print("syntax error: missing file after >")
                continue
                
        if tokens_to_remove:
            tokens_to_remove.sort(reverse=True)
            for index in tokens_to_remove:
                parts.pop(index)

        if not parts:
            continue
        cmd = parts[0]

        # --- File and Directory Setup (omitted for brevity, remains unchanged) ---
        if stdout_redirect:
            if os.path.dirname(stdout_redirect):
                 os.makedirs(os.path.dirname(stdout_redirect), exist_ok=True)
            if not stdout_append:
                try: open(stdout_redirect, "w").close()
                except Exception as e:
                    print(f"shell: failed to create file {stdout_redirect}: {e}"); continue
        if stderr_redirect:
            if os.path.dirname(stderr_redirect):
                 os.makedirs(os.path.dirname(stderr_redirect), exist_ok=True)
            if not stderr_append: 
                try: open(stderr_redirect, "w").close()
                except Exception as e:
                    print(f"shell: failed to create file {stderr_redirect}: {e}"); continue

        # --- Handle builtins (omitted for brevity, remains unchanged) ---
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
                with open(stdout_redirect, mode) as f: f.write(msg + ("\n" if not msg.endswith("\n") else ""))
            else:
                print(msg, flush=True)
            continue

        if cmd == 'type':
            if len(parts) < 2: continue
            target = parts[1]
            if target in BUILTIN_COMMANDS: output = f"{target} is a shell builtin"
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
            if target_dir == "~" or target_dir.startswith("~/"): target_dir = os.path.expanduser(target_dir)
            if not os.path.isdir(target_dir):
                print(f"cd: {target_dir}: No such file or directory"); continue
            try: os.chdir(target_dir)
            except Exception as e: print(f"cd: {target_dir}: {e}")
            continue


        # --- Handle external programs (omitted for brevity, remains unchanged) ---
        full_path = find_executable(cmd)
        if full_path:
            try:
                stdout_target = open(stdout_redirect, "a" if stdout_append else "w") if stdout_redirect else None
                stderr_mode = "a" if stderr_append else "w"
                stderr_target = open(stderr_redirect, stderr_mode) if stderr_redirect else None
                args_for_program = [cmd] + parts[1:] 

                subprocess.run(
                    args_for_program, executable=full_path, stdout=stdout_target or sys.stdout, stderr=stderr_target or sys.stderr
                )

                if stdout_target: stdout_target.close()
                if stderr_target: stderr_target.close()
            except Exception as e:
                print(f"Error executing {cmd}: {e}")
            continue


        # PRINT for Unknown command
        print(f"{command}: command not found")
    


if __name__ == "__main__":
    main()