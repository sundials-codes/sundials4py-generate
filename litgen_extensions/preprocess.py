import re


def strip_sundials_export(code):
    return code.replace("SUNDIALS_EXPORT", "")


def change_long_int_to_long(code):
    return code.replace("long int", "long")


def preprocess_header(code):
    code = strip_sundials_export(code)
    code = change_long_int_to_long(code)
    return code
