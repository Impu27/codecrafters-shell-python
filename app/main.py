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
        # EVAL
        if command == "":
            # Empty input: just show prompt again
            continue
        # PRINT
        print(f"{command}: command not found")
    


if __name__ == "__main__":
    main()
