# 新闻联播文字稿

爬取自 [cctv央视网](https://tv.cctv.com/), 包准确!

每次 GitHub Actions workflow 执行时，现在会自动完成这条链路：

1. 抓取当天《新闻联播》文字稿
2. 落盘 Markdown 和结构化 JSON
3. 调用 AI 生成“新闻解读 + 公考主题归纳”分析稿
4. 保存分析 Markdown 到 `analysis/`
5. 上传分析结果到飞书知识库

如果 workflow 检测到当天 `news/YYYYMMDD.json` 或 `news/YYYYMMDD.md` 已存在，会跳过抓取，直接进入 AI 分析和飞书上传。

## 分析与飞书配置

首次使用前需要：

```bash
cp config/config.example.yaml config/config.yaml
pip install -r requirements.txt
```

需要手动修改config中的 wiki_space_id 和 source_parent_node_tokens

需要提供这些环境变量：

- `AI_API_KEY`
- `FEISHU_APP_ID`
- `FEISHU_APP_SECRET`


本地手动运行：

```bash
npm run index
python -m src.main
```


## 文字稿目录: 

<!-- INSERT -->
- [20260629](./news/20260629.md)
- [20260626](./news/20260626.md)
- [20260625](./news/20260625.md)
- [20260624](./news/20260624.md)
- [20260623](./news/20260623.md)
- [20260622](./news/20260622.md)
- [20260621](./news/20260621.md)
- [20260620](./news/20260620.md)
- [20260619](./news/20260619.md)
- [20260618](./news/20260618.md)
- [20260617](./news/20260617.md)
- [20260616](./news/20260616.md)
- [20260615](./news/20260615.md)
- [20260614](./news/20260614.md)
- [20260613](./news/20260613.md)
- [20260612](./news/20260612.md)
- [20260611](./news/20260611.md)
- [20260610](./news/20260610.md)
- [20260609](./news/20260609.md)
- [20260608](./news/20260608.md)
- [20260607](./news/20260607.md)
- [20260606](./news/20260606.md)
- [20260605](./news/20260605.md)
- [20260604](./news/20260604.md)
- [20260603](./news/20260603.md)
- [20260602](./news/20260602.md)
- [20260601](./news/20260601.md)
