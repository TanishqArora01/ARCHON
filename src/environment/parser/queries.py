PYTHON_QUERY = """
(class_definition
    name: (identifier) @class.name
) @class.def

(function_definition
    name: (identifier) @function.name
) @function.def

(import_statement) @import.stmt
(import_from_statement) @import.stmt
"""

TS_QUERY = """
(class_declaration
    name: (type_identifier) @class.name
) @class.def

(interface_declaration
    name: (type_identifier) @interface.name
) @interface.def

(method_definition
    name: (property_identifier) @method.name
) @method.def

(lexical_declaration
    (variable_declarator
        name: (identifier) @arrow.name
        value: (arrow_function)
    ) @arrow.def
)

(export_statement) @export.stmt
"""
