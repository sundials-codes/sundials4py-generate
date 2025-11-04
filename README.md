This script generates Python bindings for the SUNDIALS library using litgen and nanobind.

Overview:
---------

- Parses a YAML configuration file (generate.yaml) describing modules and header files to process.
- Configures litgen options for SUNDIALS-specific pointer types, enum handling, function adapters, and other binding behaviors.
- Reads C/C++ header files, optionally dumps their srcML XML representation, or generates Python binding code.
- Writes the generated binding code to specified output files.

Key Features:
-------------

- Customizes binding generation for SUNDIALS pointer types and function signatures.
- Excludes comments from docstrings, exports enum values with prefixes, and handles nullable pointer parameters.
- Supports custom adapters for array pointers, modifiable output parameters, and shared pointer returns.
- Allows per-module configuration for pointer types, nullable parameters, enum/class/function exclusions, and macro defines.
- Can process a single YAML file or recursively process all generate.yaml files in a directory.

Usage:
------

```
    python generate.py <config_yaml_path> [--dump-srcml]
```

License
--------

This code is licensed under GPLv3 due to its use of litgen, but the generated code is not subject to GPLv3.
