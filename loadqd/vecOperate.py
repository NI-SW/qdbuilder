#!/usr/bin/env python3
"""将 datasets.jsonl 中的数据向量化后写入 Qdrant。"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="把 JSON 文档批量向量化并插入 Qdrant")
    parser.add_argument(
        "--json-path",
        type=Path,
        default=Path("./datasets.jsonl"),
        help="待入库数据文件路径（默认使用 ./datasets.jsonl）",
    )
    parser.add_argument(
        "--qdrant-url",
        default="http://127.0.0.1:6333",
        help="Qdrant 服务地址",
    )
    parser.add_argument(
        "--qdrant-api-key",
        default=None,
        help="Qdrant API Key（本地无鉴权可不填）",
    )
    parser.add_argument(
        "--collection-name",
        default="stream_chunks",
        help="目标集合名",
    )
    parser.add_argument(
        "--model-name",
        default="BAAI/bge-small-zh-v1.5",
        help="SentenceTransformer 模型名（建议中文向量模型）",
    )
    parser.add_argument(
        "--distance",
        choices=["cosine", "dot", "euclid"],
        default="cosine",
        help="向量距离类型",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=64,
        help="单次 upsert 的点数量",
    )
    parser.add_argument(
        "--max-items",
        type=int,
        default=None,
        help="仅处理前 N 条，用于小样本验证",
    )
    parser.add_argument(
        "--recreate-collection",
        action="store_true",
        help="是否先重建集合（会清空原数据）",
    )
    parser.add_argument(
        "--wait",
        action="store_true",
        help="upsert 后等待服务端落盘再返回（更安全，默认关闭以提高吞吐）",
    )
    return parser.parse_args()


def load_records(json_path: Path, max_items: int | None) -> list[dict[str, Any]]:
    if not json_path.exists():
        raise FileNotFoundError(f"数据文件不存在: {json_path}")

    with json_path.open("r", encoding="utf-8") as f:
        raw_text = f.read().strip()

    if not raw_text:
        return []

    records: list[dict[str, Any]] = []

    # datasets.jsonl 采用 NDJSON（一行一个 JSON 对象）格式；
    # 这里同时兼容标准 JSON 数组，避免后续导出格式变化时脚本失效。
    if raw_text[0] == "[":
        data = json.loads(raw_text)
        if not isinstance(data, list):
            raise ValueError("JSON 顶层必须是数组，或者是 NDJSON 每行一个对象")
        records = [x for x in data if isinstance(x, dict)]
    else:
        for line_no, line in enumerate(raw_text.splitlines(), start=1):
            line = line.strip()
            if not line:
                continue
            item = json.loads(line)
            if not isinstance(item, dict):
                raise ValueError(f"第 {line_no} 行不是 JSON 对象")
            records.append(item)

    if max_items is not None:
        records = records[: max(0, max_items)]
    return records


def _get_text_field(record: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = record.get(key)
        if isinstance(value, str):
            value = value.strip()
            if value:
                return value
    return ""


def normalize_record(record: dict[str, Any]) -> dict[str, Any]:
    instruction = _get_text_field(record, "instruction")
    content = _get_text_field(record, "content")
    chunk = _get_text_field(record, "chunk")
    complex_cot = _get_text_field(record, "complexCOT", "complexCot", "complex_cot")
    label = _get_text_field(record, "label")

    normalized = dict(record)
    # 保留原始字段的同时，补充统一的小写别名，便于后续检索与兼容旧代码。
    normalized.setdefault("instruction", instruction)
    normalized.setdefault("content", content)
    normalized.setdefault("chunk", chunk)
    normalized.setdefault("complexCOT", complex_cot)
    normalized.setdefault("label", label)
    return normalized


def get_embedding_dimension(model: Any) -> int:
    # 通过 getattr 动态兼容新版/旧版 sentence-transformers，避免直接引用已弃用方法名。
    dimension_getter = getattr(model, "get_embedding_dimension", None)
    if callable(dimension_getter):
        dimension = dimension_getter()
        if isinstance(dimension, int):
            return dimension
        if isinstance(dimension, str):
            return int(dimension)

    dimension_getter = getattr(model, "get_sentence_embedding_dimension", None)
    if callable(dimension_getter):
        dimension = dimension_getter()
        if isinstance(dimension, int):
            return dimension
        if isinstance(dimension, str):
            return int(dimension)

    raise RuntimeError("无法从 SentenceTransformer 模型读取 embedding 维度")


def build_embedding_text(record: dict[str, Any]) -> str:
    # 新格式以 instruction + content 为主；chunk 作为补充上下文，避免把 label / complexCOT 引入向量噪声。
    instruction = _get_text_field(record, "instruction")
    content = _get_text_field(record, "content")
    chunk = _get_text_field(record, "chunk")

    parts = []
    if instruction:
        parts.append(f"[instruction]\n{instruction}")
    if content:
        parts.append(f"[content]\n{content}")
    if chunk:
        parts.append(f"[chunk]\n{chunk}")
    return "\n\n".join(parts)


def build_payload(record: dict[str, Any], source_index: int) -> dict[str, Any]:
    normalized = normalize_record(record)

    payload = dict(record)
    payload.pop("instruction", None)
    # 统一补充规范化字段，便于不同版本数据混合检索；保留其他原始元数据字段。
    payload["instruction"] = normalized.get("instruction", "")
    payload["content"] = normalized.get("content", "")
    payload["chunk"] = normalized.get("chunk", "")
    payload["complexCOT"] = normalized.get("complexCOT", "")
    payload["label"] = normalized.get("label", "")
    payload["source_index"] = source_index
    return payload


def make_point_id(raw_text: str, fallback_index: int) -> int:
    if not raw_text.strip():
        return fallback_index
    digest = hashlib.sha1(raw_text.encode("utf-8")).hexdigest()[:16]
    return int(digest, 16)


def ensure_collection(client: Any, collection_name: str, vector_size: int, distance_name: str, recreate: bool) -> None:
    from qdrant_client import models

    collection_exists = client.collection_exists(collection_name)
    if collection_exists and recreate:
        client.delete_collection(collection_name)
        collection_exists = False

    if not collection_exists:
        distance = {
            "cosine": models.Distance.COSINE,
            "dot": models.Distance.DOT,
            "euclid": models.Distance.EUCLID,
        }[distance_name]

        client.create_collection(
            collection_name=collection_name,
            vectors_config=models.VectorParams(
                # size 必须与 embedding 维度严格一致，否则写入会报维度不匹配。
                size=vector_size,
                # 中文语义检索常用 cosine，能更稳定衡量方向相似度；dot/euclid 按业务再切换。
                distance=distance,
            ),
        )


def upsert_records(
    client: Any,
    collection_name: str,
    records: list[dict[str, Any]],
    model_name: str,
    distance_name: str,
    recreate_collection: bool,
    batch_size: int,
    wait: bool,
) -> None:
    from qdrant_client import models
    from sentence_transformers import SentenceTransformer

    if batch_size <= 0:
        raise ValueError("batch-size 必须 > 0")

    model = SentenceTransformer(model_name)
    vector_size = get_embedding_dimension(model)
    ensure_collection(client, collection_name, vector_size, distance_name, recreate_collection)

    inserted = 0
    for start in range(0, len(records), batch_size):
        batch = records[start : start + batch_size]
        texts = [build_embedding_text(r) for r in batch]
        vectors = model.encode(texts, normalize_embeddings=True)

        points: list[models.PointStruct] = []
        for idx, (record, text, vector) in enumerate(zip(batch, texts, vectors), start=start):
            payload = build_payload(record, idx)
            points.append(
                models.PointStruct(
                    id=make_point_id(text, idx),
                    vector=vector.tolist(),
                    payload=payload,
                )
            )

        client.upsert(
            # collection_name 用于隔离不同业务语料，避免多套数据混在同一索引里。
            collection_name=collection_name,
            points=points,
            # wait=True 时接口在写入完成后再返回，便于保证随后检索能立刻看到新数据。
            wait=wait,
        )
        inserted += len(points)
        print(f"已写入 {inserted}/{len(records)}")


def main() -> None:
    args = parse_args()

    try:
        from qdrant_client import QdrantClient
    except ImportError as exc:
        raise SystemExit("缺少依赖 qdrant-client，请先安装: pip install qdrant-client") from exc

    try:
        import sentence_transformers  # noqa: F401
    except ImportError as exc:
        raise SystemExit(
            "缺少依赖 sentence-transformers，请先安装: pip install sentence-transformers"
        ) from exc

    records = load_records(args.json_path, args.max_items)
    if not records:
        raise SystemExit("没有可写入的数据记录")

    records = [normalize_record(record) for record in records]

    client = QdrantClient(url=args.qdrant_url, api_key=args.qdrant_api_key)

    # batch_size 决定吞吐与内存占用平衡：值大更快但更占内存，值小更稳。
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


