import re
from typing import List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from src.db.models import SymbolNode

class GitDiffAnalyzer:
    def parse_diff_patches(self, diff_text: str) -> List[dict]:
        """
        Parses a unified diff and extracts modified files and their line ranges.
        Returns a list of dicts: {"file_path": str, "line_ranges": List[Tuple[int, int]]}
        """
        patches = []
        current_file = None
        current_ranges: List[Tuple[int, int]] = []

        file_header_re = re.compile(r"^diff --git a/(.*?) b/(.*?)$")
        hunk_header_re = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")

        for line in diff_text.splitlines():
            # Match start of a new file patch
            file_match = file_header_re.match(line)
            if file_match:
                if current_file:
                    patches.append({
                        "file_path": current_file,
                        "line_ranges": current_ranges
                    })
                current_file = file_match.group(2)
                current_ranges = []
                continue

            # Match hunk header
            if current_file:
                hunk_match = hunk_header_re.match(line)
                if hunk_match:
                    start_line = int(hunk_match.group(1))
                    count_str = hunk_match.group(2)
                    count = int(count_str) if count_str else 1
                    
                    if count == 0:
                        continue # no added/modified lines in this hunk
                        
                    # Git unified diffs are 1-indexed.
                    # tree-sitter line ranges are 0-indexed.
                    # Convert to 0-indexed start and end.
                    start_idx = start_line - 1
                    end_idx = start_idx + count - 1
                    
                    current_ranges.append((start_idx, end_idx))

        if current_file:
            patches.append({
                "file_path": current_file,
                "line_ranges": current_ranges
            })

        return patches

    async def map_diff_to_symbols(self, db_session: AsyncSession, snapshot_id: str, diff_text: str) -> List[str]:
        """
        Maps a unified diff text to database SymbolNode IDs based on modified file paths and intersecting line ranges.
        """
        from src.core.utils.path_normalizer import PathNormalizer
        from src.db.models import Snapshot
        
        # Get repository path to resolve absolute paths used during ingestion
        stmt_snap = select(Snapshot).where(Snapshot.id == str(snapshot_id))
        result_snap = await db_session.execute(stmt_snap)
        snapshot = result_snap.scalar_one_or_none()

        patches = self.parse_diff_patches(diff_text)
        impacted_symbol_ids = set()

        for patch in patches:
            rel_file_path = PathNormalizer.normalize_git_path(patch["file_path"])
            line_ranges = patch["line_ranges"]

            if not line_ranges:
                continue

            # Query all symbols in this file for this snapshot
            stmt = select(SymbolNode).where(
                SymbolNode.snapshot_id == str(snapshot_id),
                SymbolNode.file_path == rel_file_path
            )
            result = await db_session.execute(stmt)
            symbols = result.scalars().all()

            for symbol in symbols:
                # meta_data might not exist or might not have line_range
                meta = symbol.meta_data or {}
                s_range = meta.get("line_range")
                if not s_range or len(s_range) != 2:
                    continue

                sym_start, sym_end = s_range

                # Check if any diff hunk overlaps with the symbol's line range
                for hunk_start, hunk_end in line_ranges:
                    # Overlap condition: max(start1, start2) <= min(end1, end2)
                    if max(sym_start, hunk_start) <= min(sym_end, hunk_end):
                        impacted_symbol_ids.add(symbol.id)
                        break

        return list(impacted_symbol_ids)
