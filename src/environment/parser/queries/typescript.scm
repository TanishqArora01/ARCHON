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
(import_statement) @import.stmt
