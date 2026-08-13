from tools.read_file import read_file

TOOLS = [
    {
        "name": "read_file",
        "description": "Read and return the full text contents of a file at the given path.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Relative or absolute path to the file to read.",
                }
            },
            "required": ["path"],
        },
    }
]



availble_tools = {
    "read_file" : read_file,
}