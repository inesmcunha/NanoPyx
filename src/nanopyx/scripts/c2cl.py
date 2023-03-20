import os
from pathlib import Path

from __init__ import find_files


def extract_function_code(file_txt, function_name):
    """
    Extract function code from C file
    :param file_txt: file text
    :param function_name: Function name to extract
    :return: Function signature and code (str, str)
    """
    function_code_lines = []

    function_started = False
    brackets = 0

    for line in file_txt.splitlines():
        if function_name in line and "(" in line and ")" in line and ";" not in line:
            function_started = True
            brackets = 0

        if function_started:
            brackets += line.count("{")
            brackets -= line.count("}")

            if brackets > 0:
                function_code_lines.append(line)

            if brackets == 0:
                function_code_lines.append(line)
                function_started = False
                break

    if len(function_code_lines) == 0:
        return None

    function_signature = function_code_lines[0].split("{")[0].strip() + ";"

    return function_signature, "\n".join(function_code_lines)


def find_function_header(file_txt, function_name):
    """
    Find function header in C file
    :param file_txt: file text
    :param function_name: Function name to extract
    :return: Function header (str)
    """
    for line in file_txt.splitlines():
        if function_name in line and "(" in line and ")" in line and ";" in line:
            return line


def extract_define_code(file_txt, define_name):
    """
    Extract define code from C file
    :param file_txt: file text
    :param define_name: Define name to extract
    :return: Define code (str)
    """
    for line in file_txt.splitlines():
        if define_name in line and line.strip().startswith("#define"):
            return line


def confirm_c_file_absolute_path(c_filename):
    """
    Confirm that the C file is in the include directory
    :param c_filename: C file name
    :return: absolute path of C file
    """
    if os.path.exists(c_filename):
        return os.path.abspath(c_filename)

    # find file in include directory
    file_path = Path(__file__).parent.parent.parent / "include" / c_filename
    if os.path.exists(file_path):
        return os.path.abspath(file_path)

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Could not find file {file_path}")

    return None


def copy_c_function_to_cl(cl_filename: str) -> str:
    """
    Copy C functions to CL file
    :param cl_filename: .cl file to copy C functions to
    :return: Message
    """

    ext = os.path.splitext(cl_filename)[1]
    assert ext == ".cl", "File must be a cl file"

    # c_filename = os.path.splitext(cl_filename)[0] + ".c"
    # if not os.path.exists(c_filename):
    #    return "- Skipping .cl autocopy (no .c file): " + cl_filename

    # read the cl file
    functions_to_copy = {}
    defines_to_copy = {}

    tag_copy_functions = "// c2cl-function: "
    tag_copy_define = "// c2cl-define: "

    with open(cl_filename, "r") as f:
        cl_txt = f.read()
        if tag_copy_functions not in cl_txt:
            return f"- Skipping .cl autocopy (no {repr(tag_copy_functions)} tag): {cl_filename}"

        cl_lines = cl_txt.splitlines()

        for i, line in enumerate(cl_lines):
            if line.startswith(tag_copy_functions):
                # example: // c2cl-function: _c_mandelbrot from _c_mandelbrot_benchmark.c
                info = line.replace(tag_copy_functions, "").split(" from ")
                function_name = info[0]
                function_filename = confirm_c_file_absolute_path(info[1])
                function_signature_and_code = extract_function_code(
                    open(function_filename, "r").read(), function_name
                )
                functions_to_copy[info[0]] = function_signature_and_code
                # clear any text after the tag that is not a \n
                start = cl_txt.find(line) + len(line)
                end = cl_txt.find("\n\n", start)
                cl_txt = (
                    cl_txt[:start]
                    + "\n"
                    + function_signature_and_code[1]
                    + cl_txt[end:]
                )
                # clear function signature from cl file if it exists
                function_header = find_function_header(cl_txt, function_name)
                if function_header:
                    cl_txt = cl_txt.replace(
                        function_header, function_signature_and_code[0]
                    )
                else:
                    cl_txt = function_signature_and_code[0] + cl_txt

            if line.startswith(tag_copy_define):
                # example: // c2cl-define: MAX_ITERATIONS from _c_mandelbrot_benchmark.c
                info = line.replace(tag_copy_define, "").split(" from ")
                define_name = info[0]
                define_filename = confirm_c_file_absolute_path(info[1])
                define_code = extract_define_code(
                    open(define_filename, "r").read(), define_name
                )
                defines_to_copy[info[0]] = define_code
                # clear any text after the tag that is not a \n
                start = cl_txt.find(line) + len(line)
                end = cl_txt.find("\n\n", start)
                cl_txt = cl_txt[:start] + "\n" + define_code + cl_txt[end:]

    with open(cl_filename, "w") as f:
        f.write(cl_txt)
        return "- Generating .cl file: " + cl_filename


def autocopy_files(root_dir: str):
    print(f"Searching {root_dir} for .cl files...")
    cl_files = find_files(root_dir, ".cl")

    print("Autocopy .cl files...")
    msgs = []
    for file in cl_files:
        msgs.append(copy_c_function_to_cl(file))

    print("\n".join(sorted(msgs)))


def main():
    print(
        r"""
           ______       _
          (_____ \     | |
      ____  ____) )____| |
     / ___)/ ____// ___) |
    ( (___| (____( (___| |
     \____)_______)____)\_)
          nanopyx-c2cl
    """
    )

    path = Path(__file__).parent.parent / "liquid"
    autocopy_files(path)


if __name__ == "__main__":
    main()
