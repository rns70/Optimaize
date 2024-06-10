import pyoptimaizer
import os
from pathlib import Path

def read_instruction_template(folder, version):
    # get this package __file__
    _package_dir = Path(os.path.dirname(pyoptimaizer.__file__))
    # get the folder containing the instruction template
    instruction_template_path = _package_dir / "instruction_templates" / folder / f"{version}.txt"
    with open(instruction_template_path, 'r') as f:
        instruction_template = f.read()
    messages = instruction_template.split("<-next_message->")
    messages_parsed = []
    for message in messages:
        role, content = message.split(":", 1)
        messages_parsed.append({
            "role": role,
            "content": content
        })
    return messages_parsed