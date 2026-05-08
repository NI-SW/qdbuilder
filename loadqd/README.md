# 待插入向量库的数据集格式, jsonl格式，每个json是一行
## example format
{
    "instruction": "",
    "content": "",
    "chunk": "",
    "complexCOT": "",
    "label": ""
}

## export origin format
{
    "data": [
        {
            "question": "",
            "answer": "",
            "cot": "",
            "questionLabel": "1 基准数据集",
            "chunkName": "Distilled Content"
        }
    ],
    "hasMore": false,
    "offset": 1
}

## export get chunk
{
    "chunkNames":["i2Stream 9.1.4 Beta软件使用指引-part-3"]
}