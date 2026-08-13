def read_file(path):
    try:
        with open(path, "r") as f:
            return f.read() 
    except FileNotFoundError:
        return f"Error: File not found at '{path}'."
    except Exception as e:  # noqa: BLE001
        return f"Error reading file '{path}': {e}" 
