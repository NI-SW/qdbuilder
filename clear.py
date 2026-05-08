"""删除 export 导出产生的数据集文件，并清理项目缓存。"""

import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent


def clean_exported_datasets() -> int:
    """删除 export/ 下由 export_datasets 产生的 datasets-*.jsonl 文件。"""
    export_dir = PROJECT_ROOT / "export"
    removed = 0
    for f in export_dir.glob("datasets-*.jsonl"):
        f.unlink()
        print(f"  已删除: {f}")
        removed += 1
    return removed


def clean_pycache() -> int:
    """删除项目目录下的 __pycache__（不进入 .venv）。"""
    removed = 0
    for d in PROJECT_ROOT.rglob("__pycache__"):
        if ".venv" in d.parts:
            continue
        shutil.rmtree(d)
        print(f"  已删除: {d}")
        removed += 1
    return removed


def main() -> None:
    print("清理导出的数据集文件 ...")
    n1 = clean_exported_datasets()
    print(f"  共删除 {n1} 个文件\n")

    print("清理 __pycache__ 缓存 ...")
    n2 = clean_pycache()
    print(f"  共删除 {n2} 个目录")

    print("\n清理完成。")


if __name__ == "__main__":
    main()
