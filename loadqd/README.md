# 待插入向量库的数据集格式, jsonl格式，每个json是一行
## example format
```angular2html
&#123;
    "instruction": "",
    "content": "",
    "chunk": "",
    "complexCOT": "",
    "label": ""
}
```

## export origin format
```angular2html
&#123;
    "data": [
        &#123;
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
```


## export get chunk
```angular2html
&#123;
    "chunkNames":["i2Stream 9.1.4 Beta软件使用指引-part-3"]
}
```