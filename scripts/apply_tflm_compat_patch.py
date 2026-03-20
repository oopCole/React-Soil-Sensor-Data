# pre: patch pio-tflite-lib after lib install — gcc 12+ placement new vs private delete (tflite-micro#2576)

from __future__ import annotations

import sys
from pathlib import Path

Import("env")  # noqa: F821  — provided by platformio / scons

MARKER = "gcc 12+: placement new"
UPGRADE_MARKER = "trailing public: keeps following members public"

NEW_PATCHED_BLOCK = """#ifdef TF_LITE_STATIC_MEMORY
// """ + MARKER + """ — placement delete public; global delete private; """ + UPGRADE_MARKER + """
#define TF_LITE_REMOVE_VIRTUAL_DELETE \\
 public: \\
 void operator delete(void* ptr, void* place) noexcept {} \\
 private: \\
 void operator delete(void* p) {} \\
 public:
#else
#define TF_LITE_REMOVE_VIRTUAL_DELETE
#endif
"""

ORIGINAL_BLOCK = """#ifdef TF_LITE_STATIC_MEMORY
#define TF_LITE_REMOVE_VIRTUAL_DELETE \\
  void operator delete(void* p) {}
#else
#define TF_LITE_REMOVE_VIRTUAL_DELETE
#endif
"""

# first revision of our patch (ended with private: — broke MicroMutableOpResolver public methods)
OLD_PATCHED_BLOCK = """#ifdef TF_LITE_STATIC_MEMORY
// """ + MARKER + """ — public placement delete so placement new is valid (private global delete stays)
#define TF_LITE_REMOVE_VIRTUAL_DELETE \\
 public: \\
 void operator delete(void* ptr, void* place) noexcept {} \\
 private: \\
 void operator delete(void* p) {}
#else
#define TF_LITE_REMOVE_VIRTUAL_DELETE
#endif
"""


def patch_file(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    if UPGRADE_MARKER in text:
        return False
    if OLD_PATCHED_BLOCK in text:
        path.write_text(text.replace(OLD_PATCHED_BLOCK, NEW_PATCHED_BLOCK, 1), encoding="utf-8")
        print(f"tflm patch: upgraded macro in {path}")
        return True
    if ORIGINAL_BLOCK in text:
        path.write_text(text.replace(ORIGINAL_BLOCK, NEW_PATCHED_BLOCK, 1), encoding="utf-8")
        print(f"tflm patch: updated {path}")
        return True
    print(f"tflm patch: no known block to replace in {path}", file=sys.stderr)
    return False


def find_compat_header(project_dir: Path) -> Path | None:
    deps = project_dir / ".pio" / "libdeps" / "embedded_rising_falling"
    if not deps.is_dir():
        return None
    for p in deps.rglob("compatibility.h"):
        parts = {x.lower() for x in p.parts}
        if "tensorflow" in parts and "lite" in parts and "micro" in parts:
            return p
    return None


def run_patch(project_dir: Path) -> None:
    target = find_compat_header(project_dir)
    if target is None:
        print(
            "tflm patch: skip (lib not under .pio/libdeps/embedded_rising_falling yet)",
            file=sys.stderr,
        )
        return
    patch_file(target)


if env.get("PIOENV") == "embedded_rising_falling":
    run_patch(Path(env["PROJECT_DIR"]))
