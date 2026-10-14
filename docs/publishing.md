# 分发与发布

## 仓库与入口

- 公开仓库：[`hzqedison/website-trust-audit`](https://github.com/hzqedison/website-trust-audit)
- 源码与阅读入口：GitHub 仓库 README
- 固定预发布版本：[`v0.1.0-draft`](https://github.com/hzqedison/website-trust-audit/releases/tag/v0.1.0-draft)
- 独立 GitHub Pages：未启用；没有 `github.io` 站点

GitHub 公开仓库已创建。源码可由仓库页面查看；固定版本链接用于查看该预发布版本。只有收到并核对 GitHub 推送及 Release 操作结果后，才记录相应操作已完成；此文件不替代发布 receipt。

## 发布约定

1. 本地检查变更、提交边界、Git 身份、测试与包内容。
2. 推送初版到 `main`，记录远端提交 SHA 和操作结果。
3. 创建固定 tag `v0.1.0-draft` 并推送；核对 tag 指向的 commit。
4. 通过该 tag 发布预发布版本，附带从 tag 生成的 ZIP 与说明；记录 Release URL、附件 SHA256 和操作结果。
5. 后续团队安装固定 tag 或 commit，不跟随可变分支。

GitHub Pages 可选用于公开阅读文档，但不是权限隔离的数据仓库。不得将项目审计记录、客户信息或私有附件发布到仓库或 Pages。Pages 目前未启用，只有另行明确批准并配置后才更新此状态。GitHub 官方说明：[GitHub Pages 是什么](https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages)、[配置发布来源](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site)。

本仓库不附带外部 CI/action、License、自定义域名或 Pages 配置；如未来需要，须另行评审授权。
