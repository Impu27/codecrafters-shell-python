import sys


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
            if cmd == 'type' or 'echo' or 'exit':
                print(f"{cmd} is a shell builtin")
            else:
                print(f"{cmd}: not found")
        # PRINT
        print(f"{command}: command not found")
    


if __name__ == "__main__":
    main()
