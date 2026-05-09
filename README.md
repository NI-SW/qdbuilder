# qdbuilder
insert the dataset from easy-dataset to qdrant-vector database

## usage
```angular2html
usage: main.py [-h] [--json-path JSON_PATH] [--qdrant-url QDRANT_URL] [--qdrant-api-key QDRANT_API_KEY] [--collection-name COLLECTION_NAME] [--model-name MODEL_NAME] [--distance {cosine,dot,euclid}] [--batch-size BATCH_SIZE]
               [--max-items MAX_ITEMS] [--recreate-collection] [--wait]
               project_id
从 Easy Dataset 导出数据集并写入 Qdrant 向量库

positional arguments:
  project_id            Easy Dataset 项目 ID

options:
  -h, --help            show this help message and exit
  --json-path JSON_PATH
                        导出文件保存路径（默认自动生成）
  --qdrant-url QDRANT_URL
                        Qdrant 服务地址
  --qdrant-api-key QDRANT_API_KEY
                        Qdrant API Key
  --collection-name COLLECTION_NAME
                        目标集合名
  --model-name MODEL_NAME
                        SentenceTransformer 模型名
  --distance {cosine,dot,euclid}
                        向量距离类型
  --batch-size BATCH_SIZE
                        单次 upsert 的点数量
  --max-items MAX_ITEMS
                        仅处理前 N 条
  --recreate-collection
                        是否先重建集合
  --wait                upsert 后等待落盘
```

## example
```angular2html
uv run python main.py --qdrant-url http://192.168.34.65:6333 --collection-name mytestcc --wait bnWkABymSsor
```