import pathlib

class PathNormalizer:
    @staticmethod
    def to_relative_posix(absolute_path: str | pathlib.Path, repo_root: str | pathlib.Path) -> str:
        """
        Converts an absolute path to a repository-relative POSIX path (forward slashes).
        If the path is not relative to repo_root, returns the normalized absolute path.
        """
        abs_p = pathlib.Path(absolute_path).resolve()
        root_p = pathlib.Path(repo_root).resolve()
        try:
            return abs_p.relative_to(root_p).as_posix()
        except ValueError:
            return abs_p.as_posix()

    @staticmethod
    def normalize_git_path(git_path: str) -> str:
        """
        Ensures a git path uses standard POSIX forward slashes.
        """
        return pathlib.Path(git_path).as_posix()
