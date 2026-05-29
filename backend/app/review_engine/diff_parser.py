from dataclasses import dataclass, field


@dataclass
class FileHunk:
    file_path: str
    start_line: int
    end_line: int
    content: str


@dataclass
class DiffFile:
    file_path: str
    status: str
    hunks: list[FileHunk] = field(default_factory=list)


BINARY_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".svg",
    ".pdf", ".zip", ".gz", ".tar", ".tgz", ".bz2",
    ".mp4", ".mov", ".avi", ".mp3", ".wav",
    ".ttf", ".otf", ".woff", ".woff2", ".eot",
    ".pyc", ".pyo", ".so", ".dll", ".dylib", ".lib",
    ".wasm", ".exe", ".bin", ".class", ".jar",
}


def _is_binary(file_path: str) -> bool:
    import os
    ext = os.path.splitext(file_path)[1].lower()
    return ext in BINARY_EXTENSIONS


def parse_diff(diff_text: str) -> list[DiffFile]:
    files: list[DiffFile] = []
    current_file: DiffFile | None = None
    current_hunk_start = 0
    current_hunk_content: list[str] = []
    current_status = "modified"

    for line in diff_text.split("\n"):
        if line.startswith("diff --git"):
            if current_file and current_hunk_content:
                hunk = FileHunk(
                    file_path=current_file.file_path,
                    start_line=current_hunk_start,
                    end_line=current_hunk_start + len(current_hunk_content),
                    content="\n".join(current_hunk_content),
                )
                current_file.hunks.append(hunk)
                current_hunk_content = []
            if current_file:
                files.append(current_file)
            current_file = DiffFile(file_path="", status=current_status)
            current_status = "modified"
        elif line.startswith("--- a/") and current_file:
            current_file.file_path = line[6:]
            if _is_binary(current_file.file_path):
                current_file.status = "binary"
        elif line.startswith("+++ b/") and current_file:
            if "dev/null" in line and current_file.file_path.startswith("a/"):
                current_file.status = "deleted"
        elif line.startswith("rename from ") and current_file:
            current_file.status = "renamed"
        elif line.startswith("rename to ") and current_file:
            pass
        elif line.startswith("deleted file mode"):
            current_status = "deleted"
            if current_file:
                current_file.status = "deleted"
        elif line.startswith("new file mode"):
            current_status = "new"
            if current_file:
                current_file.status = "new"
        elif line.startswith("Binary files") and current_file:
            current_file.status = "binary"
        elif line.startswith("@@") and current_file:
            if current_hunk_content:
                hunk = FileHunk(
                    file_path=current_file.file_path,
                    start_line=current_hunk_start,
                    end_line=current_hunk_start + len(current_hunk_content),
                    content="\n".join(current_hunk_content),
                )
                current_file.hunks.append(hunk)
                current_hunk_content = []
            try:
                parts = line.split()
                if len(parts) >= 3:
                    new_range = parts[2].lstrip("+")
                    current_hunk_start = int(new_range.split(",")[0])
            except (ValueError, IndexError):
                current_hunk_start = 0
        elif current_file and (line.startswith("+") or line.startswith("-") or line.startswith(" ")):
            current_hunk_content.append(line)

    if current_file and current_hunk_content:
        hunk = FileHunk(
            file_path=current_file.file_path,
            start_line=current_hunk_start,
            end_line=current_hunk_start + len(current_hunk_content),
            content="\n".join(current_hunk_content),
        )
        current_file.hunks.append(hunk)

    if current_file:
        files.append(current_file)

    return files
