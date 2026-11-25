# 伊﨑直志の研究サイト

URL: https://naoshi-isaki.github.io/research/

研究サイト専用のリポジトリです。R・R Markdown・授業用データは `naoshi-isaki/naoshi-isaki.github.io` に分離して管理しています。

## 更新方法

| 内容 | 編集するファイル |
| --- | --- |
| 所属・研究・業績・経歴・教育 | `docs/index.html` |
| 引用情報・授業構成 | `docs/app.js` |
| デザイン | `docs/styles.css` |
| フォント・アイコン | `docs/assets/` |
| 内容の出典 | `SITE_SOURCES.md` |

`main` にコミットすると GitHub Actions が `docs/` を GitHub Pages へ配信します。Hugo、R、Node.jsのビルドは不要です。日本語は `data-ja`、英語は `data-en` の要素内を編集します。

## 検索除外

全HTMLページの `<head>` に `robots` と `googlebot` の `noindex, nofollow` を設定しています。新しいページを追加するときも必ず引き継いでください。公開ワークフローはこの設定が欠けたHTMLを検出すると配信を止めます。

この設定は検索結果への掲載を拒否するもので、アクセス制限ではありません。URLからの閲覧と公開リポジトリの閲覧は可能です。既に検索結果にあるページは、検索エンジンが再クロールした後に除外されます。`robots.txt` でクロールを拒否すると `noindex` が読み取られないため、クロール禁止は設定しません。

旧Hugo版は `archive/hugo-before-separation-2026-11-25` ブランチに保存しています。以前のトップURL `https://naoshi-isaki.github.io/` はこのサイトへ転送します。
