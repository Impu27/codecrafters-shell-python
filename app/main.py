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
    """Finds the longest common prefix among a list of strings."""
    if not strs: return ""
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
    """Searches all directories in PATH for executable files starting with the given prefix."""
    path_dirs = os.environ.get("PATH", "").split(os.pathsep)
    matches = set()
    for directory in path_dirs:
        if not os.path.isdir(directory): continue
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
    Custom completer function for readline, supporting LCP and hook activation.
    """
    global _TAB_PRESSED_COUNT, _LAST_COMPLETION_TEXT

    # 1. Reset logic (moved to hook as that's the primary event handler)
    
    # 2. Gather all matches
    builtin_matches = [cmd for cmd in BUILTIN_COMMANDS if cmd.startswith(text)]
    external_matches = find_all_executables_with_prefix(text)
    all_matches = sorted(list(set(builtin_matches + external_matches)))
    
    if not all_matches:
        if state == 0: # Print bell only on first tab press when no matches are found
            sys.stdout.write('\a')
            sys.stdout.flush()
        return None
        
    # LCP Completion Logic (Runs only on the first call: state == 0)
    if state == 0 and len(all_matches) > 1:
        lcp = get_longest_common_prefix(all_matches)
        
        # If the LCP extends the current text, return the LCP. 
        if len(lcp) > len(text):
            return lcp
            
    # Standard readline completion 
    if state < len(all_matches):
        match = all_matches[state]
        
        # If there's only one unique match, complete it with a trailing space.
        if len(all_matches) == 1:
            return match + " "
            
        # For multiple ambiguous matches, return without a space to allow more typing 
        # or trigger the hook on subsequent tabs.
        return match
    else:
        return None


def display_matches_hook(substitution_text, matches, longest_match_length):
    """
    Custom hook to handle the display of multiple ambiguous matches (bell/list).
    """
    global _TAB_PRESSED_COUNT, _LAST_COMPLETION_TEXT
    
    # Reset logic: If the current input is different from the last time TAB was pressed, reset.
    if substitution_text != _LAST_COMPLETION_TEXT:
        _TAB_PRESSED_COUNT = 0
    
    # This needs to be captured from the completer's input
    _LAST_COMPLETION_TEXT = substitution_text 
    _TAB_PRESSED_COUNT += 1
    
    # 1. First TAB press: Ring the bell.
    if _TAB_PRESSED_COUNT == 1:
        sys.stdout.write('\a')
        sys.stdout.flush()
        
    # 2. Second TAB press: Print the list and redraw the prompt.
    elif _TAB_PRESSED_COUNT == 2:
        
        # Print a newline to move the cursor below the current input line
        sys.stdout.write('\n')
        
        # Print the list of matches separated by 2 spaces, followed by a newline
        # The order in `matches` here is guaranteed by the completer's sort logic.
        list_output = "  ".join(matches)
        sys.stdout.write(list_output + '\n') 
        
        # CRITICAL FIX: Instruct readline to redraw its own prompt and input line
        # This is reliable for testers capturing standard output.
        readline.redisplay()

    if _TAB_PRESSED_COUNT > 2:
        _TAB_PRESSED_COUNT = 0


def setup_readline():
    """Configures readline for autocompletion."""
    readline.set_completer(shell_completer)
    readline.set_completion_display_matches_hook(display_matches_hook)
    readline.parse_and_bind("tab: complete")


# --- The rest of the main function code remains the same ---
def find_executable(program):
    path_dirs = os.environ.get("PATH", "").split(os.pathsep)
    for directory in path_dirs:
        full_path = os.path.join(directory, program)
        if os.path.isfile(full_path) and os.access(full_path, os.X_OK):
            return full_path
    return None

def write_output(text, stdout_redirect=None, stderr_redirect=None, append=False):
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
        except EOFError: break
        except KeyboardInterrupt: sys.stdout.write("\n"); continue

        if command == "": continue
        try: parts = shlex.split(command)
        except ValueError as e: print(f"Error parsing command: {e}"); continue
        if not parts: continue
        
        # Reset TAB counter after a command is executed
        global _TAB_PRESSED_COUNT
        _TAB_PRESSED_COUNT = 0 
        
        stdout_redirect = None; stderr_redirect = None
        stdout_append = False; stderr_append = False  
        tokens_to_remove = []

        # --- Redirection Logic (truncated for display) ---
        if "2>>" in parts: op_index = parts.index("2>>"); 
        # ... redirection handling ...
        if "2>" in parts: op_index = parts.index("2>");
        # ... redirection handling ...
        if ">>" in parts or "1>>" in parts: op_index = parts.index("1>>") if "1>>" in parts else parts.index(">>");
        # ... redirection handling ...
        elif ">" in parts or "1>" in parts: op_index = parts.index("1>") if "1>" in parts else parts.index(">");
        # ... redirection handling ...
                
        if tokens_to_remove: tokens_to_remove.sort(reverse=True); 
        # ... token removal ...

        if not parts: continue
        cmd = parts[0]

        # --- File and Directory Setup (truncated for display) ---
        # ... file setup logic ...

        # --- Handle builtins (truncated for display) ---
        if cmd == "exit": 
        # ... exit logic ...
        if cmd == "echo": 
        # ... echo logic ...
        if cmd == 'type':
        # ... type logic ...
        if cmd == "pwd": 
        # ... pwd logic ...
        if cmd == "cd":
        # ... cd logic ...

        # --- Handle external programs (truncated for display) ---
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
            except Exception as e: print(f"Error executing {cmd}: {e}")
            continue

        # PRINT for Unknown command
        print(f"{command}: command not found")
    


if __name__ == "__main__":
    main()