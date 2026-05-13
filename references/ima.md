# IMA Integration Guide

## 集成边界

本项目先保证微信公众号文章已成功保存到本地，再与 ima 做联动。不要在本地保存失败时尝试导入 ima；本地归档是可审计的事实来源。

当前集成提供：

- IMA 凭证预检：`scripts/ima_check.py`
- 本地文章导入清单：`scripts/ima_manifest.py`
- 面向智能体的 ima 操作路由：将清单交给用户环境中已安装的 ima-skills，并按 `knowledge-base/SKILL.md` 执行。

本项目不重新实现 ima-skills。真正调用 IMA OpenAPI 时，必须使用 ima-skills 的 `ima_api.cjs` 和 `knowledge-base/SKILL.md`，所有请求都是 `HTTP POST + JSON Body`，且只发往 `https://ima.qq.com`。

## 必须遵守的 ima-skills 规则

- 上传文件到知识库必须走 `knowledge-base/SKILL.md`。
- 文件上传流程是 `create_media → COS → add_knowledge`。
- `title` 必须等于 `file_name`，包含扩展名；不要把文章标题当作上传 title。
- 上传文件内容必须保持原样；不要对 PDF、图片、Excel 等二进制文件做编码转换。
- 不支持视频文件、Bilibili/YouTube URL 和 `file://` URL；遇到这些输入要直接拒绝，并提示用户使用 IMA 桌面客户端。
- API 错误要分两层处理：先处理 `ima_api.cjs` 非 0 退出时 stderr 中的 `code=-100|-200`，再处理 stdout 中 IMA 后端返回的 `code!=0`。

## 凭证准备

打开：

```text
https://ima.qq.com/agent-interface
```

获取 Client ID 和 API Key，然后二选一配置。

方式 A：配置文件：

```bash
mkdir -p ~/.config/ima
printf '%s' "your_client_id" > ~/.config/ima/client_id
printf '%s' "your_api_key" > ~/.config/ima/api_key
```

方式 B：环境变量：

```bash
export IMA_OPENAPI_CLIENTID="your_client_id"
export IMA_OPENAPI_APIKEY="your_api_key"
```

检查凭证：

```bash
scripts/ima_check.py
```

脚本只报告是否存在凭证，不打印凭证值。

## 本地文章到 IMA 的推荐流程

1. 先运行本地同步：

```bash
uv run wx-article-sync --config config.json
```

2. 生成 ima 导入清单：

```bash
scripts/ima_manifest.py data/articles --output data/ima-manifest.jsonl
```

3. 使用已安装的 ima-skills，读取 `knowledge-base/SKILL.md`，把清单中的 `content_path` 对应文件导入目标知识库。每行清单已经把 `title` 设置为文件名，符合 ima-skills 的文件上传命名规则。

4. 如果用户要保留原文链接，可在本地安全环境中显式生成带 URL 的清单：

```bash
scripts/ima_manifest.py data/articles --include-url --output data/ima-manifest-with-url.jsonl
```

默认不输出 `source_url`，避免在终端或日志里泄露微信公众号原文链接 token。

## 定时同步到 IMA 知识库

用外部调度器串行执行：

```bash
cd /path/to/wx-article-sync
uv run wx-article-sync --config config.json
scripts/ima_manifest.py data/articles --output data/ima-manifest.jsonl
# Then read ima-skills knowledge-base/SKILL.md and import each file via create_media → COS → add_knowledge.
```

如果导入 ima 的步骤失败，不要删除本地文章目录和 `state_path`。下次可以基于本地清单重试 ima 导入。

## 查询已经同步的文章

本地侧：

```bash
scripts/ima_manifest.py data/articles
scripts/inspect_state.py data/state.json
```

ima 侧必须走 ima-skills 的 `knowledge-base/SKILL.md`：

- 搜索标题、公众号名、同步日期或文章关键词。
- 如果用户问“已经同步过哪些文章”，先用本地清单给出可审计结果；如果用户问“ima 知识库里有没有某篇文章”，再调用 ima 知识库搜索。

## 结合 ima 询问文章内容

推荐顺序：

1. 确认文章已经本地保存。
2. 确认文章已经导入 ima 知识库。
3. 使用 ima 知识库搜索或问答能力提问。
4. 如果 ima 搜索不到，回到本地 `content_path` 检查文章是否存在，再判断是否需要重新导入。
