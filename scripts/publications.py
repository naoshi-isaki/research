#!/usr/bin/env python3
"""Import verified bibliographic metadata and generate the site's publication list.

Uses only Python's standard library. Missing or ambiguous metadata stops the import;
existing records and user-corrected spellings are never replaced by an import.
"""
import argparse
import html
import json
import os
from pathlib import Path
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
NS = {
    "dc": "http://purl.org/dc/elements/1.1/",
    "dct": "http://purl.org/dc/terms/",
    "dcndl": "http://ndl.go.jp/dcndl/terms/",
    "foaf": "http://xmlns.com/foaf/0.1/",
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
}
LABELS = {"article": ("論文", "Article"), "translation": ("訳書", "Translation"), "book": ("著書", "Book")}
# User-specified display form, 2026-11-26. Do not guess Japanese transliterations.
NAME_FORMS = {"アダム・プシェヴォスキ": "プシェヴォスキ, A.", "Przeworski, A.": "プシェヴォスキ, A."}


def text(value):
    if isinstance(value, list):
        value = value[0] if value else ""
    if isinstance(value, dict):
        value = value.get("content", "")
    return html.unescape(re.sub(r"<[^>]*>", "", str(value or ""))).strip()


def japanese(value):
    return bool(re.search(r"[\u3040-\u30ff\u3400-\u9fff\uf900-\ufaff]", value))


def title_text(value):
    value = text(value)
    return re.sub(r"\s+:\s+", "―", value) if japanese(value) else value


def normalize_identifier(raw):
    raw = unicodedata.normalize("NFKC", raw).strip()
    raw = re.sub(r"^(?:https?://(?:dx\.)?doi\.org/|doi\s*:\s*)", "", raw, flags=re.I)
    raw = urllib.parse.unquote(raw)
    if re.fullmatch(r"10\.\d{4,9}/\S+", raw, flags=re.I) and len(raw) <= 300:
        return "doi", raw.lower()
    isbn = re.sub(r"^ISBN(?:-1[03])?\s*:?\s*", "", raw, flags=re.I)
    isbn = re.sub(r"[\s\-–—]", "", isbn).upper()
    if re.fullmatch(r"\d{9}[\dX]", isbn):
        digits = [10 if c == "X" else int(c) for c in isbn]
        if sum((10-i)*v for i, v in enumerate(digits)) % 11:
            raise ValueError("ISBNのチェック桁が一致しません。")
        prefix = "978" + isbn[:9]
        isbn = prefix + str((-sum(int(c)*(1 if i % 2 == 0 else 3) for i, c in enumerate(prefix))) % 10)
    if re.fullmatch(r"97[89]\d{10}", isbn):
        if sum(int(c)*(1 if i % 2 == 0 else 3) for i, c in enumerate(isbn)) % 10 == 0:
            return "isbn", isbn
    raise ValueError("有効なDOI（URL可）またはISBN-10 / ISBN-13を入力してください。")


def get(url, accept="application/json"):
    request = urllib.request.Request(url, headers={
        "Accept": accept,
        "User-Agent": "NaoshiIsakiPublicationImporter/1.0 (https://github.com/naoshi-isaki/research)",
    })
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=25) as response:
                return response.read(5_000_001).decode("utf-8-sig")
        except urllib.error.HTTPError as error:
            if error.code not in (429, 500, 502, 503, 504) or attempt == 2:
                raise
            time.sleep(2 ** attempt)


def person_name(person):
    if person.get("literal"):
        return text(person["literal"])
    family, given = text(person.get("family")), text(person.get("given"))
    if japanese(family + given):
        return family + given
    initials = " ".join(part[0] + "." for part in re.findall(r"[^\W\d_]+", given, re.UNICODE))
    return NAME_FORMS.get(f"{family}, {initials}", f"{family}, {initials}".strip(", "))


def from_csl(data, doi):
    if text(data.get("DOI")).lower() != doi.lower():
        raise ValueError("取得されたDOIが入力と一致しません。")
    journal = text(data.get("container-title"))
    kind = text(data.get("type"))
    if kind in ("book-chapter", "chapter", "dataset", "proceedings-article"):
        raise ValueError("この資料種別は自動登録の対象外です。書誌データを個別に確認してください。")
    if kind in ("book", "monograph", "edited-book"):
        kind = "book"
    elif journal or kind in ("article-journal", "journal-article"):
        kind = "article"
    else:
        raise ValueError("論文・書籍の種別を取得できませんでした。")
    year = ""
    for key in ("issued", "published-print", "published"):
        parts = data.get(key, {}).get("date-parts", [])
        if parts and parts[0]:
            year = str(parts[0][0])
            break
    translators = [person_name(p) for p in data.get("translator", [])]
    record = {
        "id": "doi-" + doi, "type": "translation" if translators and kind == "book" else kind,
        "year": year, "authors": [person_name(p) for p in data.get("author", [])],
        "title": title_text(data.get("title")), "doi": doi, "url": "https://doi.org/" + doi,
        "source": "https://citation.doi.org/metadata?" + urllib.parse.urlencode({"doi": doi}),
    }
    if translators:
        record["translators"] = translators
    if kind == "article":
        record.update(journal=journal, volume=text(data.get("volume")),
                      issue=text(data.get("issue") or data.get("number")), pages=text(data.get("page")))
    else:
        record["publisher"] = text(data.get("publisher"))
    validate(record)
    return record


def from_ndl(xml, isbn):
    root = ET.fromstring(xml)
    matches = []
    for bib in root.findall(".//dcndl:BibResource", NS):
        identifiers = bib.findall("dct:identifier", NS)
        if not any(n.get("{" + NS["rdf"] + "}datatype", "").endswith("/ISBN")
                   and re.sub(r"\D", "", n.text or "") == isbn for n in identifiers):
            continue
        if bib.find("dct:title", NS) is not None:
            matches.append(bib)
    # Prefer the National Diet Library's own catalogue if aggregators return duplicates.
    own = [b for b in matches if "/R100000002-" in b.get("{" + NS["rdf"] + "}about", "")]
    matches = own or matches
    if len(matches) != 1:
        raise ValueError("ISBNに対応する書誌を一意に特定できませんでした。")
    bib = matches[0]
    authors, translators = [], []
    for creator in bib.findall("dc:creator", NS):
        value = text(creator.text)
        match = re.fullmatch(r"(.+?)\s+(共著|著|共訳|訳|翻訳)", value)
        if not match:
            raise ValueError("著者と訳者の役割を判定できませんでした。自動登録を中止します。")
        names = re.split(r"[、，]|,\s*(?=[\u3040-\u30ff\u3400-\u9fff\uf900-\ufaff])", match[1])
        names = [NAME_FORMS.get(name.strip(), name.strip()) for name in names]
        (translators if "訳" in match[2] else authors).extend(names)
    year = text(bib.findtext("dct:issued", "", NS)) or text(bib.findtext("dct:date", "", NS))
    year_match = re.match(r"\d{4}", year)
    record = {
        "id": "isbn-" + isbn, "type": "translation" if translators else "book",
        "year": year_match.group() if year_match else "", "authors": authors,
        "title": title_text(bib.findtext("dct:title", "", NS)),
        "publisher": text(bib.findtext("dct:publisher/foaf:Agent/foaf:name", "", NS)),
        "isbn": isbn, "url": bib.get("{" + NS["rdf"] + "}about", "").split("#")[0],
        "source": "NDL Search SRU",
    }
    if translators:
        record["translators"] = translators
    validate(record)
    return record


def from_openbd(data, isbn):
    if not data or not data[0] or data[0].get("summary", {}).get("isbn") != isbn:
        raise ValueError("openBDに該当書誌がありません。")
    item = data[0]
    summary = item.get("summary", {})
    contributors = item.get("onix", {}).get("DescriptiveDetail", {}).get("Contributor", [])
    authors, translators = [], []
    for person in contributors:
        roles = person.get("ContributorRole", [])
        if isinstance(roles, str):
            roles = [roles]
        if not roles or not set(roles).issubset({"A01", "B06"}):
            raise ValueError("openBDの著者・訳者区分が不明です。役割を推測せず登録を中止します。")
        name = text(person.get("PersonName"))
        (translators if "B06" in roles else authors).append(NAME_FORMS.get(name, name))
    year = re.match(r"\d{4}", text(summary.get("pubdate")))
    record = {
        "id": "isbn-" + isbn, "type": "translation" if translators else "book",
        "year": year.group() if year else "", "authors": authors,
        "title": title_text(summary.get("title")), "publisher": text(summary.get("publisher")),
        "isbn": isbn, "url": "https://ndlsearch.ndl.go.jp/api/openurl?isbn=" + isbn,
        "source": "https://api.openbd.jp/v1/get?isbn=" + isbn,
    }
    if translators:
        record["translators"] = translators
    validate(record)
    return record


def lookup(kind, identifier):
    errors = []
    if kind == "doi":
        endpoints = [
            ("https://citation.doi.org/metadata?" + urllib.parse.urlencode({"doi": identifier}), "application/json"),
            ("https://doi.org/" + urllib.parse.quote(identifier, safe="/"), "application/vnd.citationstyles.csl+json"),
        ]
        for url, accept in endpoints:
            try:
                return from_csl(json.loads(get(url, accept)), identifier)
            except (ValueError, OSError, KeyError, TypeError) as error:
                errors.append(str(error))
    else:
        query = urllib.parse.urlencode({"operation": "searchRetrieve", "version": "1.2", "recordSchema": "dcndl",
                                      "recordPacking": "xml", "maximumRecords": "5", "query": f'isbn="{identifier}"'})
        try:
            return from_ndl(get("https://ndlsearch.ndl.go.jp/api/sru?" + query, "application/xml"), identifier)
        except (ValueError, OSError, ET.ParseError) as error:
            errors.append(str(error))
        try:
            return from_openbd(json.loads(get("https://api.openbd.jp/v1/get?isbn=" + identifier)), identifier)
        except (ValueError, OSError, KeyError, TypeError) as error:
            errors.append(str(error))
    raise ValueError("書誌情報を取得できませんでした。サイトは変更していません。\n" + "\n".join(errors))


def validate(record):
    required = ["id", "type", "year", "title", "authors", "url"]
    required += ["journal"] if record.get("type") == "article" else ["publisher"]
    if record.get("type") == "translation":
        required += ["translators"]
    missing = [key for key in required if not record.get(key)]
    if missing:
        raise ValueError("書誌情報が不足しています：" + "、".join(missing))
    if record["type"] not in LABELS or not re.fullmatch(r"\d{4}", str(record["year"])):
        raise ValueError("資料種別または出版年が不正です。")
    if not isinstance(record["authors"], list) or not all(isinstance(x, str) and x.strip() for x in record["authors"]):
        raise ValueError("著者情報が不正です。")
    if record.get("translators") and (not isinstance(record["translators"], list) or not all(isinstance(x, str) and x.strip() for x in record["translators"])):
        raise ValueError("訳者情報が不正です。")
    if urllib.parse.urlsplit(record["url"]).scheme != "https":
        raise ValueError("書誌リンクにはHTTPSのURLが必要です。")


def citation(record):
    validate(record)
    names = "・".join(record["authors"])
    if record.get("translators"):
        names += "、" + "・".join(record["translators"]) + "（訳）"
    start = names + "（" + str(record["year"]) + "）"
    if record["type"] == "article":
        title = record["title"].replace("「", "『").replace("」", "』")
        volume = str(record.get("volume", ""))
        issue = str(record.get("issue", ""))
        pages = re.sub(r"(?<=\d)\s*[-–—]\s*(?=\d)", "–", str(record.get("pages", "")))
        return start + "「" + title + "」『" + record["journal"] + "』" + volume + ("（"+issue+"）" if issue else "") + ("、"+pages if pages else "") + "。"
    return start + "『" + record["title"] + "』" + record["publisher"] + "。"


def display_metadata(record):
    names = "・".join(record.get("display_authors", record["authors"]))
    if record["type"] == "article":
        details = "『" + record["journal"] + "』" + str(record.get("volume", ""))
        if record.get("issue"):
            details += "（" + str(record["issue"]) + "）"
        if record.get("pages"):
            details += "、" + re.sub(r"(?<=\d)\s*[-–—]\s*(?=\d)", "–", str(record["pages"]))
        return names + "｜" + details + "。"
    if record.get("translators"):
        names += " 著／" + "・".join(record["translators"]) + " 訳"
    return names + "｜" + record["publisher"] + "。"


def prepare(records):
    seen = set()
    for record in records:
        validate(record)
        keys = [record["id"]] + [k+":"+record[k].lower() for k in ("doi", "isbn") if record.get(k)]
        if seen.intersection(keys):
            raise ValueError("業績ID・DOI・ISBNが重複しています。")
        seen.update(keys)
        record["citation"] = citation(record)
        record["meta_ja"] = display_metadata(record)
        link_ja, link_en = (("論文を読む", "Read article") if record.get("doi") else ("書誌情報", "Publication record")) if record["type"] == "article" else ("書籍情報", "Book details")
        record.setdefault("link_label_ja", link_ja)
        record.setdefault("link_label_en", link_en)
        ja, en = LABELS[record["type"]]
        record.setdefault("label_ja", ja)
        record.setdefault("label_en", en)
    return sorted(records, key=lambda r: int(r["year"]), reverse=True)


def render(records):
    escape = lambda value: html.escape(str(value), quote=True)
    rows = []
    for r in records:
        meta = '<p class="pub-meta"><span data-ja>' + escape(r["meta_ja"]) + '</span><span data-en>' + escape(r.get("meta_en") or r["meta_ja"]) + '</span></p>'
        rows.append(f'''          <article class="publication" data-type="{escape(r['type'])}"><div class="pub-year">{escape(r['year'])}<span data-ja>{escape(r['label_ja'])}</span><span data-en>{escape(r['label_en'])}</span></div><div class="pub-main"><h3>{escape(r['title'])}</h3>{meta}<div class="pub-actions"><a href="{escape(r['url'])}" target="_blank" rel="noopener noreferrer"><span data-ja>{escape(r['link_label_ja'])}</span><span data-en>{escape(r['link_label_en'])}</span></a><button type="button" class="copy-citation" data-citation="{escape(r['citation'])}"><span data-ja>引用をコピー</span><span data-en>Copy citation</span><svg viewBox="0 0 16 16" aria-hidden="true"><path d="M5.5 5.5h8v8h-8zM10.5 5.5v-3h-8v8h3"/></svg></button></div></div></article>''')
    return "\n".join(rows)


def build(records, directory, check=False):
    records = prepare(records)
    data_path, index_path = directory / "publications.json", directory / "index.html"
    data = json.dumps(records, ensure_ascii=False, indent=2) + "\n"
    original = index_path.read_text()
    start, end = "<!-- publications:start -->", "<!-- publications:end -->"
    if original.count(start) != 1 or original.count(end) != 1:
        raise ValueError("業績一覧の生成位置が見つかりません。")
    page = original.split(start)[0] + start + "\n" + render(records) + "\n        " + end + original.split(end)[1]
    if check:
        if data_path.read_text() != data or original != page:
            raise ValueError("書誌データと表示が一致しません。python scripts/publications.py build を実行してください。")
        return
    # Compute and validate both outputs before writing either one.
    data_path.write_text(data, encoding="utf-8")
    index_path.write_text(page, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["add", "build", "check", "lookup"])
    parser.add_argument("identifier", nargs="?", default=os.environ.get("PUBLICATION_IDENTIFIER", ""))
    parser.add_argument("--directory", type=Path, default=ROOT / "docs")
    args = parser.parse_args()
    if args.command == "lookup":
        record = lookup(*normalize_identifier(args.identifier))
        print(json.dumps(prepare([record])[0], ensure_ascii=False, indent=2))
        return
    records = json.loads((args.directory / "publications.json").read_text())
    if args.command == "add":
        kind, identifier = normalize_identifier(args.identifier)
        if any(str(r.get(kind, "")).lower() == identifier.lower() for r in records):
            print("登録済みです。既存の書誌情報を保持しました。")
            return
        record = lookup(kind, identifier)
        records.append(record)
        print("追加：" + citation(record))
    build(records, args.directory, check=args.command == "check")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, ET.ParseError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
