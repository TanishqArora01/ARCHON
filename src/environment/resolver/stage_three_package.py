import json
import re
from pathlib import Path
from src.db.models import UnresolvedReference

class PackageResolutionStage:
    def __init__(self):
        self.deps_cache = {}

    def _find_dependencies(self, file_path: str, repository_path: str | None = None) -> set[str]:
        from src.core.config import settings
        import os
        from src.core.utils.path_normalizer import PathNormalizer
        
        if not os.path.isabs(file_path):
            base_dir = repository_path if repository_path else settings.PROJECT_ROOT
            abs_path = os.path.join(base_dir, file_path)
        else:
            abs_path = file_path
            
        current_dir = Path(Path(abs_path).as_posix()).parent
        while current_dir.name and current_dir.parent != current_dir:
            # TypeScript / JavaScript
            pkg_json = current_dir / "package.json"
            if pkg_json.exists():
                if pkg_json not in self.deps_cache:
                    deps = set()
                    try:
                        with open(pkg_json, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            deps.update(data.get("dependencies", {}).keys())
                            deps.update(data.get("devDependencies", {}).keys())
                    except Exception:
                        pass
                    self.deps_cache[pkg_json] = deps
                return self.deps_cache[pkg_json]

            # Python requirements.txt
            req_txt = current_dir / "requirements.txt"
            if req_txt.exists():
                if req_txt not in self.deps_cache:
                    deps = set()
                    try:
                        with open(req_txt, "r", encoding="utf-8") as f:
                            for line in f:
                                line = line.strip()
                                if line and not line.startswith("#"):
                                    match = re.match(r"^([a-zA-Z0-9_\-]+)", line)
                                    if match:
                                        deps.add(match.group(1))
                    except Exception:
                        pass
                    self.deps_cache[req_txt] = deps
                return self.deps_cache[req_txt]

            # Python pyproject.toml
            pyproject = current_dir / "pyproject.toml"
            if pyproject.exists():
                if pyproject not in self.deps_cache:
                    deps = set()
                    try:
                        with open(pyproject, "r", encoding="utf-8") as f:
                            content = f.read()
                            for match in re.finditer(r"^\s*[\"']?([a-zA-Z0-9_\-]+)[\"']?\s*[=><~^]", content, re.MULTILINE):
                                deps.add(match.group(1))
                    except Exception:
                        pass
                    self.deps_cache[pyproject] = deps
                return self.deps_cache[pyproject]

            current_dir = current_dir.parent
            
        return set()

    def resolve(self, unresolved_references: list[UnresolvedReference], repository_path: str | None = None):
        for ref in unresolved_references:
            if ref.failure_category in ["UNRESOLVED_RELATIVE_IMPORT", "UNRESOLVED_ALIAS", "UNRESOLVED_PACKAGE"]:
                deps = self._find_dependencies(ref.file_path, repository_path)
                
                # Check root package name match
                name_parts = ref.name.split("/") if "/" in ref.name else ref.name.split(".")
                root_pkg = name_parts[0]
                
                if root_pkg in deps or ref.name in deps:
                    ref.failure_category = "EXTERNAL_DEPENDENCY"
