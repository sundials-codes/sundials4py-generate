import copy
import re
from typing import Optional
from codemanip import code_utils
from srcmlcpp.cpp_types import CppParameter  # noqa: F401 (used for type hints only)
from litgen.internal.adapt_function_params._lambda_adapter import LambdaAdapter
from litgen.internal.adapted_types import AdaptedFunction
from .utils import is_array_param


def adapt_sundials_types_returns_to_shared_ptr(
    adapted_function: AdaptedFunction,
) -> Optional[LambdaAdapter]:
    """
    Adapts functions that take pointer_type* (pointer to pointer_type) parameters to instead accept
    std::vector<pointer_type> in the Python interface. Handles multiple such parameters in one function.
    """
    options = adapted_function.options
    sundials_pointer_types = options.sundials_pointer_types
    return_type = adapted_function.cpp_adapted_function.return_type

    needs_adapt = False
    is_tuple = False
    return_type_str = return_type.str_return_type()

    # print(f"{adapted_function.cpp_element().function_name}")
    # print(f"    {adapted_function.cpp_element()}")
    # print(f"    {adapted_function.cpp_element().cpp_element_comments}")

    if (
        "nb::rv_policy::reference"
        in adapted_function.cpp_element().cpp_element_comments.comments_as_str()
    ):
        return None

    tuple_args_match = None
    tuple_args_list = None
    if return_type_str.startswith("std::tuple"):
        tuple_args_match = re.match(r"std::tuple\s*<(.+?)>", return_type_str)
        if tuple_args_match:
            tuple_args_list = [arg.strip() for arg in tuple_args_match.group(1).split(",")]
            needs_adapt = any(arg in sundials_pointer_types for arg in tuple_args_list)
        is_tuple = True
    elif return_type_str in sundials_pointer_types:
        needs_adapt = True

    if not needs_adapt:
        return None

    lambda_adapter = LambdaAdapter()
    if is_tuple:
        idx_nurse_list = [
            idx for idx, arg in enumerate(tuple_args_list) if arg in sundials_pointer_types
        ]

        idx_nurse_args = ", ".join(str(idx_nurse) for idx_nurse in idx_nurse_list)
        suncontext_typename = "SUNContext"
        for idx, param in enumerate(adapted_function.adapted_parameters()):
            # Cache attribute lookup
            typenames = param.cpp_element().decl.cpp_type.typenames
            if suncontext_typename in typenames:
                adapted_function.cpp_element().cpp_element_comments.add_eol_comment(
                    f"nb::call_policy<sundials4py::returns_references_to<{idx+1}, {idx_nurse_args}>>()"
                )

        # Only deepcopy if mutation is required
        lambda_adapter.new_function_infos = copy.deepcopy(adapted_function.cpp_adapted_function)
        old_function_params = adapted_function.adapted_parameters()
        new_function_params = old_function_params
        old_return_type = adapted_function.cpp_adapted_function.return_type
        new_return_type = copy.deepcopy(old_return_type)
        new_return_type.modifiers = []
        new_return_type.specifiers = []

        if len(new_return_type.typenames) > 1:
            raise RuntimeError(
                "new_return_type.typenames has length > 1, this is not yet supported"
            )

        # Replace all relevant tuple elements with shared_ptr
        tuple_args = tuple_args_list[:]
        for idx_nurse in idx_nurse_list:
            tuple_args[idx_nurse] = (
                f"std::shared_ptr<std::remove_pointer_t<{tuple_args_list[idx_nurse]}>>"
            )
        tuple_type = f"std::tuple<{', '.join(tuple_args)}>"
        new_return_type.typenames = [tuple_type]
        lambda_adapter.new_function_infos.return_type = new_return_type

        # Build the return statement, wrapping only the relevant tuple elements
        tuple_parts = []
        for i, arg in enumerate(tuple_args_list):
            if i in idx_nurse_list:
                tuple_parts.append(
                    f"our_make_shared<std::remove_pointer_t<{arg}>, {arg}Deleter>"
                    f"(std::get<{i}>(lambda_result))"
                )
            else:
                tuple_parts.append(f"std::get<{i}>(lambda_result)")
        lambda_output_code = "return std::make_tuple(" + ", ".join(tuple_parts) + ");"

        lambda_adapter.lambda_output_code += (
            code_utils.unindent_code(lambda_output_code, flag_strip_empty_lines=True) + "\n"
        )

        lambda_adapter.adapted_cpp_parameter_list.extend(
            param.cpp_element().decl.decl_name for param in new_function_params
        )

        lambda_adapter.lambda_name = f"{adapted_function.cpp_adapted_function.function_name}_adapt_return_type_to_shared_ptr"
    else:
        # Ensure SUNContext is kept alive while this object is alive
        # The easiest way to do this without modifying litgen is to inject the
        # keep_alive statement as a comment.
        suncontext_typename = "SUNContext"
        for idx, param in enumerate(adapted_function.adapted_parameters()):
            typenames = param.cpp_element().decl.cpp_type.typenames
            if suncontext_typename in typenames:
                adapted_function.cpp_element().cpp_element_comments.add_eol_comment(
                    f"nb::keep_alive<0, {idx+1}>()"
                )

        # Only deepcopy if mutation is required
        lambda_adapter = LambdaAdapter()
        lambda_adapter.new_function_infos = copy.deepcopy(adapted_function.cpp_adapted_function)
        old_function_params = adapted_function.adapted_parameters()
        new_function_params = old_function_params
        old_return_type = adapted_function.cpp_adapted_function.return_type

        new_return_type = copy.deepcopy(old_return_type)
        new_return_type.modifiers = []
        new_return_type.specifiers = []
        new_return_type.typenames = [f"std::shared_ptr<std::remove_pointer_t<{old_return_type}>>"]
        lambda_adapter.new_function_infos.return_type = new_return_type

        lambda_output_code = (
            f"return our_make_shared<std::remove_pointer_t<{str(old_return_type)}>, "
            f"{str(old_return_type)}Deleter>(lambda_result);"
        )

        lambda_adapter.lambda_output_code += (
            code_utils.unindent_code(lambda_output_code, flag_strip_empty_lines=True) + "\n"
        )

        lambda_adapter.adapted_cpp_parameter_list.extend(
            param.cpp_element().decl.decl_name for param in new_function_params
        )

        lambda_adapter.lambda_name = f"{adapted_function.cpp_adapted_function.function_name}_adapt_return_type_to_shared_ptr"

    return lambda_adapter
