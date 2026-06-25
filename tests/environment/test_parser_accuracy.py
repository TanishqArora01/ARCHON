import pytest
from pathlib import Path
from src.environment.parser.engine import ParserEngine
from src.environment.parser.schemas import SymbolType

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "control_repo"

@pytest.mark.asyncio
async def test_python_parsing_accuracy():
    engine = ParserEngine()
    
    core_py = FIXTURES_DIR / "py_repo" / "core.py"
    result = await engine.parse_repository_file(core_py, "python")
    
    assert result.language == "python"
    
    classes = [t for t in result.tokens if t.symbol_type == SymbolType.CLASS]
    assert len(classes) == 3
    
    base_class = classes[0]
    assert base_class.name == "BaseController"
    
    concrete_class = classes[1]
    assert concrete_class.name == "ConcreteController"
    
    assert len(concrete_class.children) == 1
    method = concrete_class.children[0]
    assert method.name == "handle_request"
    assert method.symbol_type == SymbolType.FUNCTION
    
    assert len(method.children) == 1
    nested_func = method.children[0]
    assert nested_func.name == "validate"
    assert nested_func.symbol_type == SymbolType.FUNCTION
    
    init_py = FIXTURES_DIR / "py_repo" / "__init__.py"
    result_init = await engine.parse_repository_file(init_py, "python")
    assert result_init.language == "python"
    
    imports = [t for t in result_init.tokens if t.symbol_type == SymbolType.IMPORT]
    assert len(imports) == 1
    assert "BaseController" in imports[0].name

@pytest.mark.asyncio
async def test_typescript_parsing_accuracy():
    engine = ParserEngine()
    
    ts_module = FIXTURES_DIR / "ts_repo" / "module.ts"
    result = await engine.parse_repository_file(ts_module, "typescript")
    
    assert result.language == "typescript"
    
    export_interface = [t for t in result.tokens if t.symbol_type == SymbolType.EXPORT and "Payload" in t.name][0]
    interface = export_interface.children[0]
    assert interface.symbol_type == SymbolType.INTERFACE
    assert interface.name == "Payload"
    
    export_base = [t for t in result.tokens if t.symbol_type == SymbolType.EXPORT and "BaseService" in t.name][0]
    base_class = export_base.children[0]
    assert base_class.symbol_type == SymbolType.CLASS
    assert base_class.name == "BaseService"
    
    export_concrete = [t for t in result.tokens if t.symbol_type == SymbolType.EXPORT and "ConcreteService" in t.name][0]
    concrete_class = export_concrete.children[0]
    assert concrete_class.symbol_type == SymbolType.CLASS
    assert concrete_class.name == "ConcreteService"
    
    assert len(concrete_class.children) == 1
    method = concrete_class.children[0]
    assert method.name == "process"
    assert method.symbol_type == SymbolType.METHOD
    
    assert len(method.children) == 1
    nested_arrow = method.children[0]
    assert nested_arrow.name == "validate"
    assert nested_arrow.symbol_type == SymbolType.FUNCTION
