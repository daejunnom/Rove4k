"""C conditional specialization using the selected compiler's actual preprocessor.

System headers are processed, so their feature macros affect conditionals as in
the original build. Their expanded declarations are omitted from the packaged
source and restored as includes. Local headers become part of each translation
unit. Macro replacement is deferred to compilation (-fdirectives-only), avoiding
blind textual evaluation or identifier replacement in this tool.
"""

from pathlib import Path
import re
import subprocess


def specialize_c(files, directory, command, environment):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    for name, data in files.items():
        path = directory / name
        path.parent.mkdir(parents=True, exist_ok=True)
        text = data.decode()
        text = re.sub(r'(?m)^(\s*)#\s*include\s*(<[^>\n]+>)([^\n]*)$',
                      lambda match: '#pragma rove_keep_include ' + match.group(2) + '\n' + match.group(), text)
        path.write_text(text)
    owned = {(directory / name).resolve() for name in files}
    prefix = [command[0]] + [item for item in command[1:]
                             if item.startswith(("-D", "-std=", "-m")) or item == "-pthread"]
    result, observations = {}, []
    for name in sorted(item for item in files if item.endswith(".c")):
        invocation = prefix + ["-E", "-fdirectives-only", name]
        process = subprocess.run(invocation, cwd=directory, env=environment, check=True,
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120)
        active, output = False, []
        for line in process.stdout.decode().splitlines(keepends=True):
            marker = re.match(r'^\s*#\s+\d+\s+"([^\"]+)"', line)
            if marker:
                source = marker.group(1)
                active = not source.startswith("<") and (directory / source).resolve() in owned
            elif active:
                keep = re.match(r'^\s*#pragma\s+rove_keep_include\s+(<[^>]+>)', line)
                output.append("#include " + keep.group(1) + "\n" if keep else line)
        result[name] = "".join(output).encode()
        observations.append({"command": invocation, "stderr": process.stderr.decode(errors="replace"),
                             "input": name, "output_bytes": len(result[name])})
    return result, observations
