import tree_sitter_python
from tree_sitter import Language, Parser, Query, QueryCursor

PY_LANG = Language(tree_sitter_python.language())
parser = Parser(PY_LANG)
tree = parser.parse(b"class Foo: pass")
query = Query(PY_LANG, "(class_definition name: (identifier) @name) @def")

print("dir(query):", [a for a in dir(query) if not a.startswith("_")])
print("dir(tree.root_node):", [a for a in dir(tree.root_node) if not a.startswith("_")])

# Maybe query doesn't execute itself. Maybe it's query.matches(node)
# Wait, let's try tree_sitter.QueryCursor
cursor = QueryCursor() # we saw this needs args. Let's look at help(QueryCursor).
