#!/usr/bin/env python3
"""Validate structure and references in a website-trust-audit evidence JSON package."""

import json
import sys
from datetime import date, datetime
from pathlib import Path
from urllib.parse import urlparse

KINDS = {"observation", "official_claim", "third_party", "reviewer_inference", "user_requirement"}
STATUSES = {"historical", "current", "unverified"}
COVERAGE_STATUSES = {"verified", "partial", "blocked", "not_tested"}
REQUIRED_SCOPE = ("site", "locale", "page", "device")
COVERAGE_SCOPE = REQUIRED_SCOPE + ("check",)
REQUIRED_EVIDENCE_KEYS = ("id", "claim", "kind", "status", "source", "observed_at", "method", "scope", "artifact", "derived_from")


def nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def parse_time(value, label, errors, nullable=False, allow_date=False):
    if value is None and nullable:
        return None
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{label}: 需要带时区的 ISO-8601 时间")
        return None
    if allow_date and len(value) == 10:
        try:
            return date.fromisoformat(value)
        except ValueError:
            pass
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, OverflowError):
        errors.append(f"{label}: 无效的 ISO-8601 时间")
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        errors.append(f"{label}: 必须包含时区")
        return None
    return parsed


def valid_source(value):
    if not nonempty(value):
        return False
    try:
        parsed = urlparse(value)
    except ValueError:
        return False
    if parsed.scheme:
        return parsed.scheme in {"http", "https"} and bool(parsed.netloc)
    path = Path(value)
    return not path.is_absolute() and ".." not in path.parts


def safe_file(base, relative):
    if not nonempty(relative):
        return None
    path = Path(relative)
    if path.is_absolute() or ".." in path.parts:
        return None
    try:
        root = base.resolve(strict=True)
        target = (root / path).resolve(strict=True)
        target.relative_to(root)
        return target if target.is_file() else None
    except (OSError, ValueError, RuntimeError):
        return None


def check_scope(scope, required, label, errors):
    if not isinstance(scope, dict):
        errors.append(f"{label}: 必须是对象")
        return False
    valid = True
    for key in required:
        if not nonempty(scope.get(key)):
            errors.append(f"{label}.{key}: 需要非空字符串")
            valid = False
    return valid


def validate(data, package_path):
    errors = []
    if not isinstance(data, dict):
        return ["顶层 JSON 必须是对象"]
    version = data.get("schema_version")
    if type(version) is not int or version != 1:
        errors.append("schema_version: 必须是整数 1")
    if not nonempty(data.get("run_id")):
        errors.append("run_id: 需要非空字符串")
    as_of = parse_time(data.get("as_of"), "as_of", errors)
    evidence = data.get("evidence")
    coverage = data.get("coverage")
    if not isinstance(evidence, list):
        errors.append("evidence: 必须是数组")
        evidence = []
    if not isinstance(coverage, list):
        errors.append("coverage: 必须是数组")
        coverage = []

    ids = {}
    evidence_times = {}
    valid_evidence_items = {}
    for index, item in enumerate(evidence):
        label = f"evidence[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{label}: 必须是对象")
            continue
        for key in REQUIRED_EVIDENCE_KEYS:
            if key not in item:
                errors.append(f"{label}.{key}: 缺少必需字段")
        ident = item.get("id")
        if not nonempty(ident):
            errors.append(f"{label}.id: 需要非空字符串")
        elif ident in ids:
            errors.append(f"{label}.id: 重复证据 ID {ident!r}")
        else:
            ids[ident] = item
            valid_evidence_items[ident] = item
        if not nonempty(item.get("claim")):
            errors.append(f"{label}.claim: 需要非空字符串")
        kind = item.get("kind")
        if not isinstance(kind, str) or kind not in KINDS:
            errors.append(f"{label}.kind: 无效证据类型")
        status = item.get("status")
        if not isinstance(status, str) or status not in STATUSES:
            errors.append(f"{label}.status: 无效证据状态")
        source = item.get("source")
        if not valid_source(source):
            errors.append(f"{label}.source: 需要非空 URL 或项目相对路径")
        observed = parse_time(item.get("observed_at"), f"{label}.observed_at", errors, nullable=True, allow_date=status in {"historical", "unverified"} if isinstance(status, str) else False)
        if observed is not None:
            evidence_times[label] = observed
            later = observed > as_of.date() if isinstance(observed, date) and not isinstance(observed, datetime) and as_of is not None else (as_of is not None and observed > as_of)
            if later:
                errors.append(f"{label}.observed_at: 晚于 as_of")
        if status == "historical":
            if not valid_source(source):
                errors.append(f"{label}: historical 记录必须有 source")
            if observed is None and not nonempty(item.get("time_note")):
                errors.append(f"{label}: historical observed_at 为 null 时必须用 time_note 说明时间缺失")
        if status == "current":
            if observed is None:
                errors.append(f"{label}: current 记录必须有 observed_at")
            if not safe_file(package_path.parent, item.get("artifact")):
                errors.append(f"{label}: current 记录必须有目录内存在的附件文件")
        elif item.get("artifact") is not None and not safe_file(package_path.parent, item.get("artifact")):
            errors.append(f"{label}.artifact: 必须是目录内存在的相对文件路径或 null")
        if not nonempty(item.get("method")):
            errors.append(f"{label}.method: 需要非空字符串")
        check_scope(item.get("scope"), REQUIRED_SCOPE, f"{label}.scope", errors)
        derived = item.get("derived_from")
        if not isinstance(derived, list) or any(not nonempty(ref) for ref in derived):
            errors.append(f"{label}.derived_from: 必须是证据 ID 字符串数组")
        elif kind == "reviewer_inference" and not derived:
            errors.append(f"{label}: reviewer_inference 必须引用其推断依据")

    graph = {}
    for index, item in enumerate(evidence):
        if not isinstance(item, dict) or not nonempty(item.get("id")):
            continue
        ident = item["id"]
        derived = item.get("derived_from")
        graph[ident] = []
        if not isinstance(derived, list):
            continue
        for ref in derived:
            if not nonempty(ref):
                continue
            if ref == ident:
                errors.append(f"evidence[{index}]: 不允许自引用")
            if ref not in ids:
                errors.append(f"evidence[{index}]: derived_from 引用了未知 ID {ref!r}")
            else:
                graph[ident].append(ref)
    visiting, visited, cycle_nodes = set(), set(), set()

    def visit(node):
        if node in visiting:
            cycle_nodes.add(node)
            return
        if node in visited:
            return
        visiting.add(node)
        for parent in graph.get(node, []):
            visit(parent)
            if parent in cycle_nodes:
                cycle_nodes.add(node)
        visiting.remove(node)
        visited.add(node)

    for node in graph:
        visit(node)
    if cycle_nodes:
        errors.append("derived_from 关系存在循环: " + ", ".join(sorted(cycle_nodes)))

    seen_coverage = set()
    for index, item in enumerate(coverage):
        label = f"coverage[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{label}: 必须是对象")
            continue
        scope = item.get("scope")
        scope_ok = check_scope(scope, COVERAGE_SCOPE, f"{label}.scope", errors)
        if scope_ok:
            key = tuple(scope[field] for field in COVERAGE_SCOPE)
            if key in seen_coverage:
                errors.append(f"{label}: 完全相同的 coverage scope 重复")
            seen_coverage.add(key)
        status = item.get("status")
        if not isinstance(status, str) or status not in COVERAGE_STATUSES:
            errors.append(f"{label}.status: 无效覆盖状态")
        refs = item.get("evidence_ids")
        if not isinstance(refs, list) or any(not nonempty(ref) for ref in refs):
            errors.append(f"{label}.evidence_ids: 必须是证据 ID 字符串数组")
            refs = []
        if not nonempty(item.get("note")):
            errors.append(f"{label}.note: 需要非空字符串")
        for ref in refs:
            if ref not in valid_evidence_items:
                errors.append(f"{label}: 引用了未知 evidence ID {ref!r}")
        if status == "verified":
            if not refs:
                errors.append(f"{label}: verified 覆盖必须引用证据")
            for ref in refs:
                ev = valid_evidence_items.get(ref)
                if ev is None:
                    continue
                escope = ev.get("scope")
                if ev.get("status") != "current":
                    errors.append(f"{label}: verified 的每条引用都必须是 current 证据 ({ref})")
                ev_kind = ev.get("kind")
                if not isinstance(ev_kind, str) or ev_kind not in {"observation", "official_claim", "third_party"}:
                    errors.append(f"{label}: {ref!r} 的证据类型不能单独证明页面检查已执行")
                if not isinstance(scope, dict) or not isinstance(escope, dict) or any(escope.get(key) != scope.get(key) for key in REQUIRED_SCOPE):
                    errors.append(f"{label}: 引用证据 {ref!r} 的站点/语言/页面/设备 scope 不匹配")
    return errors


def main(argv):
    if len(argv) != 2:
        print(f"用法: {Path(argv[0]).name} <evidence.json>", file=sys.stderr)
        return 2
    package_path = Path(argv[1]).resolve()
    try:
        with package_path.open(encoding="utf-8") as stream:
            data = json.load(stream)
    except (OSError, UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        print(f"错误：无法读取或解析 JSON 包：{exc}", file=sys.stderr)
        return 2
    try:
        errors = validate(data, package_path)
    except (TypeError, ValueError, OverflowError, RecursionError) as exc:
        print(f"错误：JSON 包结构无效，无法验证：{exc}", file=sys.stderr)
        return 1
    if errors:
        for error in errors:
            print(f"错误：{error}", file=sys.stderr)
        print(f"结构校验失败，共 {len(errors)} 项错误。", file=sys.stderr)
        return 1
    counts = {status: 0 for status in COVERAGE_STATUSES}
    for row in data["coverage"]:
        counts[row["status"]] += 1
    print(f"结构校验通过：{len(data['evidence'])} 条证据，{len(data['coverage'])} 条覆盖记录。")
    print("覆盖状态统计：" + "；".join(f"{status}={counts[status]}" for status in ("verified", "partial", "blocked", "not_tested")))
    print("覆盖数量不代表审计完成；本工具未验证语义真实性、方法与检查层级匹配或附件真实性。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
