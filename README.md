xmltodjangomodel
================

Convert a Cidoc XML file to a Django model Python module.

# Usage

```
./convert sourcefile.xml
```

It prints the resulting output to stdout. You can specify a file as second parameter, to directly write to it.
There is a convenience switch `--json` or `-j` to print the information as json (mostly for debugging).
