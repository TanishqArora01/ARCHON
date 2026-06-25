import tree_sitter_typescript as tstypescript
from tree_sitter import Language, Parser

ts_lang = Language(tstypescript.language_typescript())
ts_code = b"export class ConcreteService extends BaseService implements IService {}"
ts_tree = Parser(ts_lang).parse(ts_code)
print(ts_tree.root_node)
