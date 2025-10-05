from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_upload_and_qa() -> None:
    # 1. 上传一个简单文档（小文本，便于控制）
    file_content = "林冲是水浒传中的人物，绰号豹子头。鲁智深是花和尚，他和林冲是朋友。"
    files = {"file": ("test.txt", file_content.encode("utf-8"), "text/plain")}
    resp = client.post("/api/docs/upload", files=files)
    assert resp.status_code == 200
    doc_info = resp.json()
    assert "doc_id" in doc_info

    # 2. 提交一个问答请求
    payload = {"query": "林冲是谁，和鲁智深是什么关系？"}
    resp = client.post("/api/qa/answer", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    # 3. 检查回答中包含关键词
    answer = data.get("answer", "")
    assert "林冲" in answer or "鲁智深" in answer, f"Unexpected answer: {answer}"
    print("回答结果:", answer)
