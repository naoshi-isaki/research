# 伊﨑直志の研究サイト

URL: https://naoshi-isaki.github.io/research/

研究サイト専用のリポジトリです。R・R Markdown・授業用データは `naoshi-isaki/naoshi-isaki.github.io` に分離して管理しています。

## DOI・ISBNで業績を追加

1. [管理者用の業績追加画面](https://github.com/naoshi-isaki/research/actions/workflows/pages.yml) を開きます。
2. **Run workflow** を押し、ブランチは **main** のまま、DOIかISBNを入力します。DOIのURL、ハイフン付きISBN、ISBN-10も利用できます。
3. **Run workflow** を実行します。書誌情報の取得、引用の整形、業績一覧への追加、保存、サイト更新まで自動で行います。結果はその実行のログで確認できます。

入力例：`10.14988/0002001265`、`978-4-560-09358-0`。この2件は登録済みなので、入力しても重複しません。空欄で実行するとサイトの再配信だけを行います。実行にはこのリポジトリへの書き込み権限が必要です。

DOIはDOI財団のメタデータ取得サービス（JaLCを含む）を使い、取得できない場合はDOI content negotiationを試します。ISBNは国立国会図書館サーチを優先し、openBDを補助として使います。外部サービスに必要な書誌情報がない場合、取得できない情報を推測して登録することはありません。訳書は著者・訳者の区別が確認できる場合に登録します。刊行年、著者名、訳者名、題名、掲載誌／出版社などが不足・不明な場合は、既存のサイトを変えずにエラーで停止します。巻号・頁が未登録なら、その項目は省略します。

既存の書誌情報は再取得で上書きしません。著者の日本語表記、原題の訳、査読の有無などを推測することもありません。原著者名の指定表記は `scripts/publications.py` の `NAME_FORMS` で管理します。

## 書誌表記

閲覧ページは「題名＋著者・掲載誌」の表示です。「引用をコピー」は同じ書誌データから以下の完全な引用を生成します。業績追加の入口は閲覧ページに表示しません。

> 伊﨑直志（2026）「イギリス労働党における『危機』言説の展開（1975–1984年）」『同志社政策科学研究』28（1）、47–58。
>
> プシェヴォスキ, A.、吉田徹・伊﨑直志（訳）（2023）『民主主義の危機―比較分析が示す変容』白水社。

DOIは書誌データとリンクに保持し、コピー本文は上の形式で句点までを出力します。

## その他の更新方法

| 内容 | 編集するファイル |
| --- | --- |
| 業績・書誌情報の修正 | `docs/publications.json` |
| 所属・研究・経歴・教育 | `docs/index.html` |
| 授業構成・画面の操作 | `docs/app.js` |
| デザイン | `docs/styles.css` |
| フォント・アイコン | `docs/assets/` |
| 内容の出典 | `SITE_SOURCES.md` |

`publications.json` 内の `citation` と `meta_ja` は自動生成されます。修正する場合は `authors`、`translators`、`title`、`year`、`journal`、`volume`、`issue`、`pages`、`publisher` 等の元の項目を編集してください。DOI・ISBNのない業績も、このファイルへ直接追加できます。

`main` にコミットすると GitHub Actions が書誌情報を整形し、`docs/` をGitHub Pagesへ配信します。表示用HTMLも生成するため、JavaScriptが無効な場合でも業績を読めます。業績以外の日本語は `data-ja`、英語は `data-en` の要素内を編集します。

手元で確認する場合（Python 3、外部パッケージ不要）：

```sh
python3 scripts/publications.py lookup 10.14988/0002001265
python3 scripts/publications.py add 9784560093580
python3 scripts/publications.py build
python3 scripts/publications.py check
python3 -m unittest discover -s tests -v
```

`lookup` は取得結果を表示するだけで保存しません。Sites版も、このリポジトリの書誌データをページ表示時に取得します。取得できない場合は同梱済みの一覧を表示します。

## 検索除外

全HTMLページの `<head>` に `robots` と `googlebot` の `noindex, nofollow` を設定しています。新しいページもこの設定を引き継いでください。配信処理は `noindex` のないHTMLを検出すると停止します。

GitHub Pagesの検索除外はアクセス制限ではありません。URLからの閲覧と公開リポジトリの閲覧は可能です。Sites版の閲覧範囲は本人のみの設定を維持します。

旧Hugo版は `archive/hugo-before-separation-2026-11-25` ブランチに保存しています。以前のトップURL `https://naoshi-isaki.github.io/` はこのサイトへ転送します。
