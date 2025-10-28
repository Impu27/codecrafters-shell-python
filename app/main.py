import sys


def main():
    sys.stdout.write("$ ")
    # Captures the user's command in the "command" variable
    command = input()
    print(f"{command}: command not found")
    pass


if __name__ == "__main__":
    main()
