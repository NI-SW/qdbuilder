import argparse
import sys
from pathlib import Path

# Ensure project root is on sys.path so local packages are importable.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from export.export_datasets import export_datasets
from loadqd.vecOperate import (
    load_records,
    normalize_record,
    upsert_records,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="从 Easy Dataset 导出数据集并写入 Qdrant 向量库"
    )
    parser.add_argument("project_id", help="Easy Dataset 项目 ID")
    parser.add_argument("--json-path", type=Path, default=None, help="导出文件保存路径（默认自动生成）")
    parser.add_argument("--qdrant-url", default="http://127.0.0.1:6333", help="Qdrant 服务地址")
    parser.add_argument("--qdrant-api-key", default=None, help="Qdrant API Key")
    parser.add_argument("--collection-name", default="stream_chunks", help="目标集合名")
    parser.add_argument("--model-name", default="BAAI/bge-small-zh-v1.5", help="SentenceTransformer 模型名")
    parser.add_argument("--distance", choices=["cosine", "dot", "euclid"], default="cosine", help="向量距离类型")
    parser.add_argument("--batch-size", type=int, default=64, help="单次 upsert 的点数量")
    parser.add_argument("--max-items", type=int, default=None, help="仅处理前 N 条")
    parser.add_argument("--recreate-collection", action="store_true", help="是否先重建集合")
    parser.add_argument("--wait", action="store_true", help="upsert 后等待落盘")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    # Step 1: export dataset from Easy Dataset
    print(f"正在从 Easy Dataset 导出项目 {args.project_id} 的数据集 ...")
    exported_path = export_datasets(args.project_id)
    print(f"导出完成: {exported_path}")

    # Step 2: load exported records
    json_path = args.json_path if args.json_path else Path(exported_path)
    records = load_records(json_path, args.max_items)
    if not records:
        print("没有可写入的数据记录，退出")
        return

    records = [normalize_record(r) for r in records]
    print(f"共 {len(records)} 条记录，开始写入 Qdrant ...")

    # Step 3: insert into Qdrant
    try:
        from qdrant_client import QdrantClient
    except ImportError:
        sys.exit("缺少依赖 qdrant-client，请先安装: pip install qdrant-client")

    client = QdrantClient(url=args.qdrant_url, api_key=args.qdrant_api_key)

    upsert_records(
        client=client,
        collection_name=args.collection_name,
        records=records,
        model_name=args.model_name,
        distance_name=args.distance,
        recreate_collection=args.recreate_collection,
        batch_size=args.batch_size,
        wait=args.wait,
    )

    info = client.get_collection(args.collection_name)
    print(f"完成，集合 `{args.collection_name}` 当前 points_count={info.points_count}")


if __name__ == "__main__":
    main()
