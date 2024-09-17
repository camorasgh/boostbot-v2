import os

logfile = "logs.txt"

def cls() -> None:
    try:
        os.system("cls" if os.name == "nt" else "clear")
    except Exception as e:
        print(f"Error clearing screen: {e}")

def pause() -> None:
    input("Press any key to continue...")

def header(text) -> None:
    cls()
    print("=" * len(text))
    print(text)
    print("=" * len(text))

def log(content) -> None:
    file_exists = os.path.exists(logfile)
    with open(logfile, 'w') as file:
        if file_exists and os.path.getsize(logfile) > 0:
            file.write("\n")

        if isinstance(content, list):
            file.write("\n".join(content))
        else:
            file.write(content)