#!/usr/bin/env python3
"""Descriptive analysis of the DependenSee discussion corpus.

The script is intentionally dependency-light: Python standard library, numpy and
matplotlib only.  It reads ../discussions.csv, writes tables to ./tables,
figures to ./figures and a machine-readable summary to ./metrics.json.

Run from anywhere:
    python3 research_data/analysis/analyze.py
"""

from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import BoundaryNorm, LinearSegmentedColormap
from matplotlib.patches import Patch
from matplotlib.ticker import FuncFormatter

# ---------------------------------------------------------------------------
# Paths and constants
# ---------------------------------------------------------------------------

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
INPUT = ROOT / "research_data" / "discussions.csv"
FIG_DIR = HERE / "figures"
TABLE_DIR = HERE / "tables"

for directory in (FIG_DIR, TABLE_DIR):
    directory.mkdir(parents=True, exist_ok=True)

TOTAL_EXPECTED = 134

CATEGORIES = [
    "removal_safety",
    "unused_packages",
    "cleanup_disk_space",
    "package_tool_usability",
    "dependency_opacity",
    "orphaned_packages",
    "visualization_request",
    "package_inventory",
    "remote_server_analysis",
]

CATEGORY_RU = {
    "removal_safety": "Безопасность удаления",
    "unused_packages": "Неиспользуемые пакеты",
    "cleanup_disk_space": "Очистка и место на диске",
    "package_tool_usability": "Удобство инструментов",
    "dependency_opacity": "Непрозрачность зависимостей",
    "orphaned_packages": "Orphan-пакеты",
    "visualization_request": "Запрос визуализации",
    "package_inventory": "Инвентаризация пакетов",
    "remote_server_analysis": "Удалённый сервер",
}

CATEGORY_SHORT = {
    "removal_safety": "Безопасность",
    "unused_packages": "Неиспользуемые",
    "cleanup_disk_space": "Очистка",
    "package_tool_usability": "Удобство",
    "dependency_opacity": "Непрозрачность",
    "orphaned_packages": "Orphan",
    "visualization_request": "Визуализация",
    "package_inventory": "Инвентаризация",
    "remote_server_analysis": "Сервер",
}

FLAGS = [
    "mentions_dependencies",
    "mentions_cleanup",
    "mentions_safety",
    "mentions_disk_space",
    "mentions_visualization",
]

FLAG_RU = {
    "mentions_dependencies": "Зависимости",
    "mentions_cleanup": "Очистка",
    "mentions_safety": "Безопасность",
    "mentions_disk_space": "Место на диске",
    "mentions_visualization": "Визуализация",
}

FLAG_SHORT = {
    "mentions_dependencies": "Зависимости",
    "mentions_cleanup": "Очистка",
    "mentions_safety": "Безопасность",
    "mentions_disk_space": "Место",
    "mentions_visualization": "Визуализация",
}

CATEGORY_COLORS = {
    "removal_safety": "#b03a2e",
    "unused_packages": "#d68910",
    "cleanup_disk_space": "#d4ac0d",
    "package_tool_usability": "#2e86c1",
    "dependency_opacity": "#7d3c98",
    "orphaned_packages": "#148f77",
    "visualization_request": "#27ae60",
    "package_inventory": "#7f8c8d",
    "remote_server_analysis": "#34495e",
}

FLAG_COLORS = {
    "mentions_dependencies": "#2e86c1",
    "mentions_cleanup": "#d68910",
    "mentions_safety": "#b03a2e",
    "mentions_disk_space": "#148f77",
    "mentions_visualization": "#7d3c98",
}

PLATFORM_ORDER = [
    "Reddit",
    "Ask Ubuntu",
    "GitHub",
    "Fedora Discussion",
    "Unix & Linux SE",
    "Arch Linux Forums",
]

PLATFORM_COLORS = {
    "Reddit": "#ff6b35",
    "Ask Ubuntu": "#e95420",
    "GitHub": "#24292f",
    "Fedora Discussion": "#3c6eb4",
    "Unix & Linux SE": "#0f7b6c",
    "Arch Linux Forums": "#1793d1",
}

DISTRO_FAMILIES = ["Debian/Ubuntu", "Fedora/RHEL", "Arch", "Не указан"]

DISTRO_FAMILY_RU = {
    "Debian/Ubuntu": "Debian / Ubuntu",
    "Fedora/RHEL": "Fedora / RHEL",
    "Arch": "Arch и производные",
    "Не указан": "Не указан",
}

DISTRO_TO_FAMILY = {
    "Ubuntu": "Debian/Ubuntu",
    "Debian": "Debian/Ubuntu",
    "Linux Mint": "Debian/Ubuntu",
    "Pop!_OS": "Debian/Ubuntu",
    "Lubuntu": "Debian/Ubuntu",
    "Kubuntu": "Debian/Ubuntu",
    "Xubuntu": "Debian/Ubuntu",
    "Ubuntu Studio": "Debian/Ubuntu",
    "Raspbian": "Debian/Ubuntu",
    "Fedora": "Fedora/RHEL",
    "CentOS": "Fedora/RHEL",
    "Arch Linux": "Arch",
    "Manjaro": "Arch",
    "CachyOS": "Arch",
}

# ---------------------------------------------------------------------------
# Analog feature matrix
# ---------------------------------------------------------------------------
# Values are deliberately conservative:
#   1.0  explicitly stated in the reviewed documentation / repository;
#   0.5  partial, indirect or manually assisted capability;
#   0.0  not confirmed in the reviewed sources.
# URPM is not included: its repository returned HTTP 404 on 2026-11-24, so its
# capabilities could not be verified.  GitHub stars are context, not a quality
# or maturity score.

ANALOG_FEATURES = [
    ("graph", "Граф"),
    ("whole_system", "Вся система"),
    ("why_chain", "Why-цепочки"),
    ("multi_manager", "Мульти-менеджер"),
    ("orphan_detection", "Orphan"),
    ("removal_preview", "Предпросмотр\nудаления"),
    ("export", "Экспорт"),
    ("disk_size", "Размеры"),
    ("headless", "Headless/CLI"),
    ("install_modeling", "Моделирование\nустановки"),
]

ANALOG_FEATURE_LONG = {
    "graph": "Визуальный граф зависимостей",
    "whole_system": "Карта всей установленной системы",
    "why_chain": "Обратные зависимости / объяснение why-цепочек",
    "multi_manager": "Несколько пакетных менеджеров или дистрибутивов",
    "orphan_detection": "Поиск orphan / неиспользуемых пакетов",
    "removal_preview": "Предпросмотр удаления до подтверждения",
    "export": "Экспорт инвентаризации или данных",
    "disk_size": "Учёт размера пакетов",
    "headless": "Работа в headless / CLI-режиме",
    "install_modeling": "Моделирование установки ещё не установленного пакета",
}

ANALOGS = [
    {
        "tool": "LDG (Linux Dependency Guide)",
        "short": "LDG",
        "class": "Прямой аналог",
        "url": "https://github.com/RubensRainelli/linux-dependency-guide",
        "values": {
            "graph": 1.0,
            "whole_system": 1.0,
            "why_chain": 0.5,
            "multi_manager": 1.0,
            "orphan_detection": 0.0,
            "removal_preview": 0.0,
            "export": 1.0,
            "disk_size": 0.0,
            "headless": 1.0,
            "install_modeling": 0.0,
        },
        "note": (
            "Интерактивный HTML-граф, JSON-инвентаризация и сравнение экспортов; "
            "перемещение по цепочкам есть, отдельной why-команды нет. Поиск orphan, "
            "размеры пакетов и предпросмотр удаления в просмотренной документации не заявлены."
        ),
    },
    {
        "tool": "Graphite",
        "short": "Graphite",
        "class": "Прямой аналог",
        "url": "https://github.com/CacheUseOnly/graphite",
        "values": {
            "graph": 1.0,
            "whole_system": 1.0,
            "why_chain": 0.5,
            "multi_manager": 0.0,
            "orphan_detection": 0.0,
            "removal_preview": 0.0,
            "export": 0.0,
            "disk_size": 0.0,
            "headless": 0.0,
            "install_modeling": 0.0,
        },
        "note": (
            "Интерактивный направленный граф установленной APT-системы и подсветка "
            "подграфа выбранного пакета; экспорт, orphan-поиск и удаление не заявлены."
        ),
    },
    {
        "tool": "Starfish",
        "short": "Starfish",
        "class": "Прямой аналог",
        "url": "https://github.com/Seafoam-Labs/Starfish",
        "values": {
            "graph": 1.0,
            "whole_system": 0.5,
            "why_chain": 0.5,
            "multi_manager": 0.0,
            "orphan_detection": 0.0,
            "removal_preview": 0.0,
            "export": 0.0,
            "disk_size": 0.0,
            "headless": 0.0,
            "install_modeling": 0.0,
        },
        "note": (
            "Интерактивный граф прямых зависимостей и Required By для Arch/ALPM; "
            "общесистемная карта, экспорт и сценарий удаления не подтверждены."
        ),
    },
    {
        "tool": "debtree",
        "short": "debtree",
        "class": "Специализированный инструмент",
        "url": "https://manpages.debian.org/trixie/debtree/debtree.1.en.html",
        "values": {
            "graph": 1.0,
            "whole_system": 0.0,
            "why_chain": 1.0,
            "multi_manager": 0.0,
            "orphan_detection": 0.0,
            "removal_preview": 0.0,
            "export": 0.5,
            "disk_size": 0.0,
            "headless": 1.0,
            "install_modeling": 0.0,
        },
        "note": (
            "Генерирует DOT для выбранного Debian-пакета: прямые, обратные и "
            "build-зависимости; визуализация требует Graphviz. Это не карта всей системы."
        ),
    },
    {
        "tool": "apt-rdepends",
        "short": "apt-rdepends",
        "class": "Специализированный инструмент",
        "url": "https://manpages.debian.org/bookworm/apt-rdepends/apt-rdepends.1.en.html",
        "values": {
            "graph": 0.5,
            "whole_system": 0.0,
            "why_chain": 1.0,
            "multi_manager": 0.0,
            "orphan_detection": 0.0,
            "removal_preview": 0.0,
            "export": 0.5,
            "disk_size": 0.0,
            "headless": 1.0,
            "install_modeling": 0.0,
        },
        "note": (
            "Рекурсивные прямые и обратные зависимости, DOT-подобный вывод; "
            "нет GUI, ограничения по глубине и виртуальным пакетам."
        ),
    },
    {
        "tool": "pacwall",
        "short": "pacwall",
        "class": "Специализированный инструмент",
        "url": "https://github.com/Kharacternyk/pacwall",
        "values": {
            "graph": 1.0,
            "whole_system": 1.0,
            "why_chain": 0.0,
            "multi_manager": 0.0,
            "orphan_detection": 1.0,
            "removal_preview": 0.0,
            "export": 0.5,
            "disk_size": 1.0,
            "headless": 0.0,
            "install_modeling": 0.0,
        },
        "note": (
            "Граф-обои всей pacman-системы: площадь узла связана с размером, "
            "подсвечены orphan/unneeded. Не интерактивен, не управляет удалением, pacman-only."
        ),
    },
    {
        "tool": "mpm (Meta Package Manager)",
        "short": "mpm",
        "class": "Смежное решение",
        "url": "https://github.com/kdeldycke/meta-package-manager",
        "values": {
            "graph": 0.0,
            "whole_system": 0.0,
            "why_chain": 0.0,
            "multi_manager": 1.0,
            "orphan_detection": 1.0,
            "removal_preview": 0.0,
            "export": 1.0,
            "disk_size": 0.0,
            "headless": 1.0,
            "install_modeling": 0.0,
        },
        "note": (
            "Мультименеджерный CLI: inventory, dump/restore, список orphan-пакетов, "
            "SBOM/JSON/TOML. Графа зависимостей и предпросмотра удаления нет; "
            "отчёт об изменениях появляется после выполнения команды."
        ),
    },
    {
        "tool": "aptitude",
        "short": "aptitude",
        "class": "Смежное решение",
        "url": "https://www.debian.org/doc/manuals/aptitude/rn01re01.en.html",
        "values": {
            "graph": 0.0,
            "whole_system": 0.0,
            "why_chain": 1.0,
            "multi_manager": 0.0,
            "orphan_detection": 1.0,
            "removal_preview": 1.0,
            "export": 0.5,
            "disk_size": 0.5,
            "headless": 1.0,
            "install_modeling": 1.0,
        },
        "note": (
            "TUI/CLI с why/why-not, автоматически установленными пакетами и "
            "предпросмотром планируемых действий, включая установку и размеры. "
            "Не строит визуальный граф и работает только с APT."
        ),
    },
]

ANALOG_SOURCES = [
    {
        "tool": "LDG (Linux Dependency Guide)",
        "class": "Прямой аналог",
        "source_type": "GitHub API",
        "url": "https://github.com/RubensRainelli/linux-dependency-guide",
        "http_status": "200",
        "stars": "20",
        "forks": "0",
        "open_issues": "0",
        "last_push": "2026-06-18",
        "license": "NOASSERTION (PEFL 1.0)",
        "included": "да",
        "comment": "Метрики GitHub перепроверены 2026-11-24.",
    },
    {
        "tool": "Graphite",
        "class": "Прямой аналог",
        "source_type": "GitHub API",
        "url": "https://github.com/CacheUseOnly/graphite",
        "http_status": "200",
        "stars": "11",
        "forks": "0",
        "open_issues": "1",
        "last_push": "2026-05-08",
        "license": "GPL-3.0",
        "included": "да",
        "comment": "Публичных релизов на странице проекта не указано.",
    },
    {
        "tool": "Starfish",
        "class": "Прямой аналог",
        "source_type": "GitHub API",
        "url": "https://github.com/Seafoam-Labs/Starfish",
        "http_status": "200",
        "stars": "21",
        "forks": "1",
        "open_issues": "0",
        "last_push": "2026-09-25",
        "license": "GPL-3.0",
        "included": "да",
        "comment": "Ориентирован на Arch/ALPM.",
    },
    {
        "tool": "debtree",
        "class": "Специализированный инструмент",
        "source_type": "Debian man page",
        "url": "https://manpages.debian.org/trixie/debtree/debtree.1.en.html",
        "http_status": "200",
        "stars": "",
        "forks": "",
        "open_issues": "",
        "last_push": "",
        "license": "См. debian/copyright",
        "included": "да",
        "comment": "Не GitHub-проект; звёзды неприменимы.",
    },
    {
        "tool": "apt-rdepends",
        "class": "Специализированный инструмент",
        "source_type": "Debian man page",
        "url": "https://manpages.debian.org/bookworm/apt-rdepends/apt-rdepends.1.en.html",
        "http_status": "200",
        "stars": "",
        "forks": "",
        "open_issues": "",
        "last_push": "",
        "license": "См. debian/copyright",
        "included": "да",
        "comment": "Не GitHub-проект; звёзды неприменимы.",
    },
    {
        "tool": "pacwall",
        "class": "Специализированный инструмент",
        "source_type": "GitHub API",
        "url": "https://github.com/Kharacternyk/pacwall",
        "http_status": "200",
        "stars": "583",
        "forks": "34",
        "open_issues": "7",
        "last_push": "2026-02-20",
        "license": "GPL-3.0",
        "included": "да",
        "comment": "Метрики GitHub перепроверены 2026-11-24.",
    },
    {
        "tool": "mpm (Meta Package Manager)",
        "class": "Смежное решение",
        "source_type": "GitHub API",
        "url": "https://github.com/kdeldycke/meta-package-manager",
        "http_status": "200",
        "stars": "632",
        "forks": "53",
        "open_issues": "16",
        "last_push": "2026-11-24",
        "license": "GPL-2.0",
        "included": "да",
        "comment": "Метрики GitHub перепроверены 2026-11-24.",
    },
    {
        "tool": "aptitude",
        "class": "Смежное решение",
        "source_type": "Debian manual",
        "url": "https://www.debian.org/doc/manuals/aptitude/rn01re01.en.html",
        "http_status": "200",
        "stars": "",
        "forks": "",
        "open_issues": "",
        "last_push": "",
        "license": "См. copyright пакета",
        "included": "да",
        "comment": "Не GitHub-проект; звёзды неприменимы.",
    },
    {
        "tool": "URPM",
        "class": "Смежное решение",
        "source_type": "GitHub API",
        "url": "https://github.com/MrNaji1/URPM",
        "http_status": "404",
        "stars": "",
        "forks": "",
        "open_issues": "",
        "last_push": "",
        "license": "",
        "included": "нет",
        "comment": (
            "Репозиторий недоступен (404) на 2026-11-24. Функции из старого описания "
            "не подтверждены и исключены из количественной матрицы."
        ),
    },
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def platform_of(source: str) -> str:
    if source.startswith("Reddit"):
        return "Reddit"
    if source.startswith("GitHub"):
        return "GitHub"
    if source == "Unix & Linux Stack Exchange":
        return "Unix & Linux SE"
    return source


def distro_family_of(distro: str) -> str:
    if not distro:
        return "Не указан"
    return DISTRO_TO_FAMILY.get(distro, distro)


def pct(part: float, total: float) -> float:
    return round(100.0 * part / total, 1) if total else 0.0


def load_rows() -> list[dict]:
    with INPUT.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    for row in rows:
        row["date_obj"] = date.fromisoformat(row["date"])
        row["year"] = row["date_obj"].year
        row["platform"] = platform_of(row["source"])
        row["distro_family"] = distro_family_of(row["distro"])
        row["score_num"] = int(row["score"]) if row["score"].strip() else None
        row["comments_num"] = (
            int(row["comments_count"]) if row["comments_count"].strip() else None
        )
        for flag in FLAGS:
            row[flag] = row[flag].strip().lower() == "true"

    if len(rows) != TOTAL_EXPECTED:
        raise SystemExit(
            f"Expected {TOTAL_EXPECTED} rows in {INPUT}, got {len(rows)}. "
            "Update the analysis or the input deliberately."
        )
    return rows


def write_csv(path: Path, header: list[str], rows: list[list]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        writer.writerows(rows)


def ordered_counts(counter: Counter, order: list[str]) -> list[tuple[str, int]]:
    return [(key, counter.get(key, 0)) for key in order]


def describe(values: list[float]) -> dict:
    if not values:
        return {"n": 0}
    arr = np.asarray(values, dtype=float)
    return {
        "n": int(arr.size),
        "mean": round(float(arr.mean()), 2),
        "median": round(float(np.median(arr)), 2),
        "q1": round(float(np.percentile(arr, 25)), 2),
        "q3": round(float(np.percentile(arr, 75)), 2),
        "min": float(arr.min()),
        "max": float(arr.max()),
    }


def finish(
    fig: plt.Figure,
    ax: plt.Axes,
    path: Path,
    title: str,
    subtitle: str = "",
) -> None:
    ax.set_title(title, loc="left", fontsize=15, fontweight="bold", pad=24)
    if subtitle:
        ax.text(
            0.0,
            1.035,
            subtitle,
            transform=ax.transAxes,
            fontsize=9,
            color="#5d6d7e",
            va="bottom",
            ha="left",
        )
    fig.savefig(path, dpi=180, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def style_axes(ax: plt.Axes) -> None:
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#b0b0b0")
    ax.spines["bottom"].set_color("#b0b0b0")
    ax.tick_params(colors="#333333", labelsize=9)
    ax.grid(axis="x", color="#e6e6e6", linewidth=0.8)
    ax.set_axisbelow(True)


def hbar(
    ax: plt.Axes,
    labels: list[str],
    values: list[float],
    colors,
    total: float | None = None,
    value_fmt: str = "{v:g} ({p:.1f}%)",
    xlabel: str = "Публикаций",
) -> None:
    y = np.arange(len(labels))
    bars = ax.barh(
        y,
        values,
        color=colors,
        height=0.68,
        edgecolor="white",
        linewidth=0.6,
    )
    ax.set_yticks(y)
    ax.set_yticklabels(labels)
    ax.invert_yaxis()
    max_value = max(values) if values else 1
    for bar, value in zip(bars, values):
        if total is not None:
            label = value_fmt.format(v=value, p=pct(value, total))
        else:
            label = value_fmt.format(v=value, p=0)
        ax.text(
            value + max_value * 0.015,
            bar.get_y() + bar.get_height() / 2,
            label,
            va="center",
            fontsize=9,
            color="#222222",
        )
    ax.set_xlim(0, max_value * 1.22)
    ax.set_xlabel(xlabel, fontsize=9, color="#444444")
    style_axes(ax)


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------


def build_metrics(rows: list[dict]) -> dict:
    total = len(rows)
    platform_counts = Counter(row["platform"] for row in rows)
    source_counts = Counter(row["source"] for row in rows)
    distro_counts = Counter(row["distro"] or "Не указан" for row in rows)
    family_counts = Counter(row["distro_family"] for row in rows)
    category_counts = Counter(row["problem_category"] for row in rows)
    flag_counts = Counter(flag for row in rows for flag in FLAGS if row[flag])
    year_counts = Counter(row["year"] for row in rows)

    platform_category = Counter(
        (row["platform"], row["problem_category"]) for row in rows
    )
    platform_flag = Counter(
        (row["platform"], flag)
        for row in rows
        for flag in FLAGS
        if row[flag]
    )
    family_category = Counter(
        (row["distro_family"], row["problem_category"]) for row in rows
    )
    category_flag = Counter(
        (row["problem_category"], flag)
        for row in rows
        for flag in FLAGS
        if row[flag]
    )

    flag_presence = {
        flag: [row for row in rows if row[flag]] for flag in FLAGS
    }
    jaccard = {}
    for i, first in enumerate(FLAGS):
        for second in FLAGS[i:]:
            union = set(id(row) for row in flag_presence[first]) | set(
                id(row) for row in flag_presence[second]
            )
            intersection = set(id(row) for row in flag_presence[first]) & set(
                id(row) for row in flag_presence[second]
            )
            value = len(intersection) / len(union) if union else 0.0
            jaccard[f"{first}|{second}"] = round(value, 3)
            jaccard[f"{second}|{first}"] = round(value, 3)

    # Engagement.  Semantics differ by platform and are not comparable.
    engagement = {}
    for platform in PLATFORM_ORDER:
        subset = [row for row in rows if row["platform"] == platform]
        comments = [row["comments_num"] for row in subset if row["comments_num"] is not None]
        scores = [row["score_num"] for row in subset if row["score_num"] is not None]
        engagement[platform] = {
            "n": len(subset),
            "comments": describe(comments),
            "score": describe(scores),
        }

    # Visualization slice.
    visual = [row for row in rows if row["mentions_visualization"]]
    visual_category = Counter(row["problem_category"] for row in visual)
    visual_platform = Counter(row["platform"] for row in visual)
    visualization_request = [
        row for row in rows if row["problem_category"] == "visualization_request"
    ]

    # Year x category.
    year_category = Counter((row["year"], row["problem_category"]) for row in rows)

    # Top discussions by comments, then score, then id for determinism.
    ranked = sorted(
        rows,
        key=lambda row: (
            -(row["comments_num"] or 0),
            -(row["score_num"] or 0),
            row["id"],
        ),
    )

    dates = [row["date_obj"] for row in rows]
    since_2021 = sum(1 for value in dates if value.year >= 2021)

    metrics = {
        "generated_on": date.today().isoformat(),
        "input": {
            "file": str(INPUT.relative_to(ROOT)),
            "rows": total,
            "unique_urls": len(set(row["url"] for row in rows)),
            "date_min": min(dates).isoformat(),
            "date_max": max(dates).isoformat(),
            "since_2021": since_2021,
            "since_2021_pct": pct(since_2021, total),
        },
        "platforms": {
            "order": PLATFORM_ORDER,
            "counts": {key: platform_counts.get(key, 0) for key in PLATFORM_ORDER},
            "shares_pct": {
                key: pct(platform_counts.get(key, 0), total) for key in PLATFORM_ORDER
            },
        },
        "sources": {
            "counts": dict(source_counts.most_common()),
            "shares_pct": {
                key: pct(value, total) for key, value in source_counts.most_common()
            },
        },
        "distros": {
            "counts": dict(distro_counts.most_common()),
            "shares_pct": {
                key: pct(value, total) for key, value in distro_counts.most_common()
            },
            "families": {
                key: family_counts.get(key, 0) for key in DISTRO_FAMILIES
            },
            "family_shares_pct": {
                key: pct(family_counts.get(key, 0), total) for key in DISTRO_FAMILIES
            },
        },
        "categories": {
            "order": CATEGORIES,
            "counts": {key: category_counts.get(key, 0) for key in CATEGORIES},
            "shares_pct": {
                key: pct(category_counts.get(key, 0), total) for key in CATEGORIES
            },
            "top3": sum(value for _, value in category_counts.most_common(3)),
            "top3_pct": pct(sum(value for _, value in category_counts.most_common(3)), total),
        },
        "flags": {
            "order": FLAGS,
            "counts": {key: flag_counts.get(key, 0) for key in FLAGS},
            "shares_pct": {
                key: pct(flag_counts.get(key, 0), total) for key in FLAGS
            },
            "both_dependencies_and_cleanup": sum(
                1
                for row in rows
                if row["mentions_dependencies"] and row["mentions_cleanup"]
            ),
            "both_dependencies_and_cleanup_pct": pct(
                sum(
                    1
                    for row in rows
                    if row["mentions_dependencies"] and row["mentions_cleanup"]
                ),
                total,
            ),
            "flag_count_distribution": dict(
                Counter(
                    sum(1 for flag in FLAGS if row[flag])
                    for row in rows
                )
            ),
            "jaccard": jaccard,
        },
        "cross_tabs": {
            "platform_category_counts": {
                platform: {
                    category: platform_category.get((platform, category), 0)
                    for category in CATEGORIES
                }
                for platform in PLATFORM_ORDER
            },
            "platform_category_row_pct": {
                platform: {
                    category: pct(
                        platform_category.get((platform, category), 0),
                        platform_counts.get(platform, 0),
                    )
                    for category in CATEGORIES
                }
                for platform in PLATFORM_ORDER
            },
            "platform_flag_counts": {
                platform: {
                    flag: platform_flag.get((platform, flag), 0) for flag in FLAGS
                }
                for platform in PLATFORM_ORDER
            },
            "platform_flag_prevalence_pct": {
                platform: {
                    flag: pct(
                        platform_flag.get((platform, flag), 0),
                        platform_counts.get(platform, 0),
                    )
                    for flag in FLAGS
                }
                for platform in PLATFORM_ORDER
            },
            "family_category_counts": {
                family: {
                    category: family_category.get((family, category), 0)
                    for category in CATEGORIES
                }
                for family in DISTRO_FAMILIES
            },
            "category_flag_counts": {
                category: {
                    flag: category_flag.get((category, flag), 0) for flag in FLAGS
                }
                for category in CATEGORIES
            },
            "category_flag_prevalence_pct": {
                category: {
                    flag: pct(
                        category_flag.get((category, flag), 0),
                        category_counts.get(category, 0),
                    )
                    for flag in FLAGS
                }
                for category in CATEGORIES
            },
        },
        "years": {
            "counts": {str(year): year_counts.get(year, 0) for year in sorted(year_counts)},
            "shares_pct": {
                str(year): pct(year_counts.get(year, 0), total)
                for year in sorted(year_counts)
            },
            "category_counts": {
                str(year): {
                    category: year_category.get((year, category), 0)
                    for category in CATEGORIES
                }
                for year in sorted(year_counts)
            },
        },
        "engagement": engagement,
        "visualization": {
            "mentions_count": len(visual),
            "mentions_pct": pct(len(visual), total),
            "category_request_count": len(visualization_request),
            "category_request_pct": pct(len(visualization_request), total),
            "mentions_with_category_request": sum(
                1 for row in visual if row["problem_category"] == "visualization_request"
            ),
            "category_request_with_safety": sum(
                1
                for row in visualization_request
                if row["mentions_safety"]
            ),
            "mentions_with_safety": sum(1 for row in visual if row["mentions_safety"]),
            "mentions_with_dependencies": sum(
                1 for row in visual if row["mentions_dependencies"]
            ),
            "mentions_with_cleanup": sum(
                1 for row in visual if row["mentions_cleanup"]
            ),
            "mentions_with_disk_space": sum(
                1 for row in visual if row["mentions_disk_space"]
            ),
            "by_platform": dict(visual_platform.most_common()),
            "by_category": dict(visual_category.most_common()),
            "ids": [row["id"] for row in visual],
        },
        "analogs": {
            "checked_on": "2026-11-24",
            "features": [
                {"key": key, "label": label} for key, label in ANALOG_FEATURES
            ],
            "tools": [
                {
                    "tool": item["tool"],
                    "short": item["short"],
                    "class": item["class"],
                    "url": item["url"],
                    "values": item["values"],
                    "coverage_score": sum(item["values"].values()),
                    "coverage_pct": round(
                        100.0 * sum(item["values"].values()) / len(ANALOG_FEATURES), 1
                    ),
                    "note": item["note"],
                }
                for item in ANALOGS
            ],
            "sources_status": ANALOG_SOURCES,
            "urpm_excluded": True,
            "urpm_status": "HTTP 404 on 2026-11-24",
        },
    }
    return metrics


# ---------------------------------------------------------------------------
# Figures
# ---------------------------------------------------------------------------


def figure_platform_distribution(rows: list[dict]) -> None:
    total = len(rows)
    counts = Counter(row["platform"] for row in rows)
    labels = PLATFORM_ORDER
    values = [counts.get(label, 0) for label in labels]
    colors = [PLATFORM_COLORS[label] for label in labels]

    fig, ax = plt.subplots(figsize=(9.2, 4.8))
    hbar(ax, labels, values, colors, total=total)
    finish(
        fig,
        ax,
        FIG_DIR / "01_platform_distribution.png",
        "Публикации по площадкам",
        f"N = {total}; доли считаются от всего корпуса",
    )


def figure_source_distribution(rows: list[dict]) -> None:
    total = len(rows)
    counts = Counter(row["source"] for row in rows).most_common()
    labels = [item[0] for item in counts]
    values = [item[1] for item in counts]
    colors = []
    for label in labels:
        platform = platform_of(label)
        colors.append(PLATFORM_COLORS.get(platform, "#7f8c8d"))

    fig, ax = plt.subplots(figsize=(10.2, 6.2))
    hbar(ax, labels, values, colors, total=total)
    finish(
        fig,
        ax,
        FIG_DIR / "02_source_distribution.png",
        "Публикации по конкретным источникам",
        f"N = {total}; цвет соответствует площадке",
    )


def figure_distro_distribution(rows: list[dict]) -> None:
    total = len(rows)
    counts = Counter(row["distro"] or "Не указан" for row in rows).most_common()
    labels = [item[0] for item in counts]
    values = [item[1] for item in counts]
    colors = []
    for label in labels:
        family = distro_family_of("" if label == "Не указан" else label)
        colors.append(
            {
                "Debian/Ubuntu": "#e67e22",
                "Fedora/RHEL": "#2e86c1",
                "Arch": "#1793d1",
                "Не указан": "#95a5a6",
            }.get(family, "#7f8c8d")
        )

    fig, ax = plt.subplots(figsize=(10.2, 6.0))
    hbar(ax, labels, values, colors, total=total)
    finish(
        fig,
        ax,
        FIG_DIR / "03_distro_distribution.png",
        "Дистрибутивы, указанные в публикациях",
        f"N = {total}; «Не указан» — 21 публикация без однозначного дистрибутива",
    )


def figure_category_distribution(rows: list[dict]) -> None:
    total = len(rows)
    counts = Counter(row["problem_category"] for row in rows).most_common()
    labels = [CATEGORY_RU[item[0]] for item in counts]
    values = [item[1] for item in counts]
    colors = [CATEGORY_COLORS[item[0]] for item in counts]

    fig, ax = plt.subplots(figsize=(10.2, 5.8))
    hbar(ax, labels, values, colors, total=total)
    finish(
        fig,
        ax,
        FIG_DIR / "04_category_distribution.png",
        "Основная проблема публикации",
        f"N = {total}; одна категория на публикацию",
    )


def figure_yearly_dynamics(rows: list[dict]) -> None:
    years = sorted(set(row["year"] for row in rows))
    category_order = [
        category
        for category, _ in Counter(
            row["problem_category"] for row in rows
        ).most_common()
    ]
    category_counts = Counter(
        (row["year"], row["problem_category"]) for row in rows
    )
    year_totals = Counter(row["year"] for row in rows)

    fig, axes = plt.subplots(
        1, 2, figsize=(13.6, 6.2), gridspec_kw={"width_ratios": [1.05, 1]}
    )

    bottoms = np.zeros(len(years))
    for category in category_order:
        values = np.array(
            [category_counts.get((year, category), 0) for year in years],
            dtype=float,
        )
        axes[0].bar(
            years,
            values,
            bottom=bottoms,
            width=0.72,
            color=CATEGORY_COLORS[category],
            edgecolor="white",
            linewidth=0.5,
            label=CATEGORY_RU[category],
        )
        bottoms += values

    for year, total in zip(years, bottoms):
        axes[0].text(
            year,
            total + 0.5,
            f"{int(total)}",
            ha="center",
            va="bottom",
            fontsize=9,
            color="#333333",
        )

    axes[0].set_xticks(years)
    axes[0].set_ylim(0, max(bottoms) * 1.16)
    axes[0].set_ylabel("Публикаций", fontsize=9)
    axes[0].set_xlabel("Год публикации", fontsize=9)
    axes[0].set_title("Абсолютное число", loc="left", fontsize=11, fontweight="bold")
    axes[0].grid(axis="y", color="#e6e6e6", linewidth=0.8)
    axes[0].set_axisbelow(True)
    axes[0].spines["top"].set_visible(False)
    axes[0].spines["right"].set_visible(False)

    year_shares = np.array([year_totals[year] for year in years], dtype=float)
    bottoms = np.zeros(len(years))
    for category in category_order:
        values = np.array(
            [category_counts.get((year, category), 0) for year in years],
            dtype=float,
        )
        shares = np.divide(
            values,
            year_shares,
            out=np.zeros_like(values),
            where=year_shares > 0,
        ) * 100
        axes[1].bar(
            years,
            shares,
            bottom=bottoms,
            width=0.72,
            color=CATEGORY_COLORS[category],
            edgecolor="white",
            linewidth=0.5,
        )
        for x, share, value, bottom in zip(years, shares, values, bottoms):
            if share >= 12:
                axes[1].text(
                    x,
                    bottom + share / 2,
                    f"{int(value)}",
                    ha="center",
                    va="center",
                    fontsize=8,
                    color="white" if category not in {"cleanup_disk_space"} else "#333333",
                )
        bottoms += shares

    axes[1].set_xticks(years)
    axes[1].set_ylim(0, 100)
    axes[1].set_ylabel("Доля внутри года, %", fontsize=9)
    axes[1].set_xlabel("Год публикации", fontsize=9)
    axes[1].set_title("Состав внутри года", loc="left", fontsize=11, fontweight="bold")
    axes[1].grid(axis="y", color="#e6e6e6", linewidth=0.8)
    axes[1].set_axisbelow(True)
    axes[1].spines["top"].set_visible(False)
    axes[1].spines["right"].set_visible(False)

    handles = [
        Patch(facecolor=CATEGORY_COLORS[category], label=CATEGORY_RU[category])
        for category in category_order
    ]
    fig.legend(
        handles=handles,
        loc="lower center",
        ncol=3,
        frameon=False,
        fontsize=9,
        bbox_to_anchor=(0.5, -0.035),
    )
    fig.suptitle(
        "Динамика корпуса по годам",
        x=0.012,
        y=1.015,
        ha="left",
        fontsize=15,
        fontweight="bold",
    )
    fig.text(
        0.012,
        0.965,
        "N = 134; 2026 год неполный — публикации по 2 ноября",
        ha="left",
        fontsize=9,
        color="#5d6d7e",
    )
    fig.subplots_adjust(top=0.86, bottom=0.20, wspace=0.22)
    fig.savefig(
        FIG_DIR / "05_yearly_dynamics.png",
        dpi=180,
        bbox_inches="tight",
        facecolor="white",
    )
    plt.close(fig)


def figure_platform_category_heatmap(rows: list[dict]) -> None:
    platform_counts = Counter(row["platform"] for row in rows)
    platform_category = Counter(
        (row["platform"], row["problem_category"]) for row in rows
    )
    matrix = np.array(
        [
            [platform_category.get((platform, category), 0) for category in CATEGORIES]
            for platform in PLATFORM_ORDER
        ]
    )

    fig, ax = plt.subplots(figsize=(12.2, 5.6))
    im = ax.imshow(matrix, cmap="Blues", aspect="auto", vmin=0, vmax=matrix.max())
    ax.set_xticks(np.arange(len(CATEGORIES)))
    ax.set_xticklabels(
        [CATEGORY_SHORT[category] for category in CATEGORIES],
        rotation=32,
        ha="right",
        fontsize=9,
    )
    ax.set_yticks(np.arange(len(PLATFORM_ORDER)))
    ax.set_yticklabels(
        [
            f"{platform} ({platform_counts.get(platform, 0)})"
            for platform in PLATFORM_ORDER
        ],
        fontsize=9,
    )
    for i in range(matrix.shape[0]):
        for j in range(matrix.shape[1]):
            value = int(matrix[i, j])
            ax.text(
                j,
                i,
                str(value),
                ha="center",
                va="center",
                fontsize=9,
                color="white" if value > matrix.max() * 0.55 else "#1b2631",
            )
    ax.set_xticks(np.arange(-0.5, len(CATEGORIES), 1), minor=True)
    ax.set_yticks(np.arange(-0.5, len(PLATFORM_ORDER), 1), minor=True)
    ax.grid(which="minor", color="white", linewidth=1.4)
    ax.tick_params(which="minor", bottom=False, left=False)
    ax.tick_params(axis="both", length=0)
    cbar = fig.colorbar(im, ax=ax, fraction=0.028, pad=0.02)
    cbar.set_label("Публикаций", fontsize=8)
    cbar.ax.tick_params(labelsize=8)
    finish(
        fig,
        ax,
        FIG_DIR / "06_platform_category_heatmap.png",
        "Площадка × категория",
        "Число публикаций; в скобках у площадки — её размер. Ячейки не нормированы.",
    )


def figure_platform_flag_heatmap(rows: list[dict]) -> None:
    platform_counts = Counter(row["platform"] for row in rows)
    platform_flag = Counter(
        (row["platform"], flag)
        for row in rows
        for flag in FLAGS
        if row[flag]
    )
    matrix = np.array(
        [
            [
                pct(platform_flag.get((platform, flag), 0), platform_counts[platform])
                for flag in FLAGS
            ]
            for platform in PLATFORM_ORDER
        ]
    )

    fig, ax = plt.subplots(figsize=(9.6, 5.2))
    im = ax.imshow(matrix, cmap="Blues", aspect="auto", vmin=0, vmax=100)
    ax.set_xticks(np.arange(len(FLAGS)))
    ax.set_xticklabels([FLAG_SHORT[flag] for flag in FLAGS], rotation=28, ha="right")
    ax.set_yticks(np.arange(len(PLATFORM_ORDER)))
    ax.set_yticklabels(
        [
            f"{platform} ({platform_counts[platform]})"
            for platform in PLATFORM_ORDER
        ],
        fontsize=9,
    )
    for i in range(matrix.shape[0]):
        for j in range(matrix.shape[1]):
            value = matrix[i, j]
            ax.text(
                j,
                i,
                f"{value:.0f}%",
                ha="center",
                va="center",
                fontsize=9,
                color="white" if value > 55 else "#1b2631",
            )
    ax.set_xticks(np.arange(-0.5, len(FLAGS), 1), minor=True)
    ax.set_yticks(np.arange(-0.5, len(PLATFORM_ORDER), 1), minor=True)
    ax.grid(which="minor", color="white", linewidth=1.4)
    ax.tick_params(which="minor", bottom=False, left=False)
    ax.tick_params(axis="both", length=0)
    cbar = fig.colorbar(im, ax=ax, fraction=0.03, pad=0.02)
    cbar.set_label("Доля внутри площадки, %", fontsize=8)
    cbar.ax.tick_params(labelsize=8)
    finish(
        fig,
        ax,
        FIG_DIR / "16_platform_flag_heatmap.png",
        "Площадка × флаг",
        "Значение — доля публикаций площадки с данным флагом; в скобках — размер площадки",
    )


def figure_distro_family(rows: list[dict]) -> None:
    family_counts = Counter(row["distro_family"] for row in rows)
    family_category = Counter(
        (row["distro_family"], row["problem_category"]) for row in rows
    )
    families = [family for family in DISTRO_FAMILIES if family_counts.get(family, 0)]
    category_order = [
        category
        for category, _ in Counter(
            row["problem_category"] for row in rows
        ).most_common()
    ]

    fig, ax = plt.subplots(figsize=(11.4, 5.0))
    y = np.arange(len(families))
    left = np.zeros(len(families))
    for category in category_order:
        values = np.array(
            [family_category.get((family, category), 0) for family in families],
            dtype=float,
        )
        totals = np.array([family_counts[family] for family in families], dtype=float)
        shares = np.divide(
            values,
            totals,
            out=np.zeros_like(values),
            where=totals > 0,
        ) * 100
        ax.barh(
            y,
            shares,
            left=left,
            height=0.62,
            color=CATEGORY_COLORS[category],
            edgecolor="white",
            linewidth=0.6,
            label=CATEGORY_RU[category],
        )
        for index, (share, value) in enumerate(zip(shares, values)):
            if share >= 7:
                ax.text(
                    left[index] + share / 2,
                    y[index],
                    f"{int(value)}",
                    ha="center",
                    va="center",
                    fontsize=8,
                    color="white" if category not in {"cleanup_disk_space"} else "#333333",
                )
        left += shares

    ax.set_yticks(y)
    ax.set_yticklabels(
        [
            f"{DISTRO_FAMILY_RU[family]} ({family_counts[family]})"
            for family in families
        ],
        fontsize=9,
    )
    ax.invert_yaxis()
    ax.set_xlim(0, 100)
    ax.set_xlabel("Доля категорий внутри семейства, %", fontsize=9)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="x", color="#e6e6e6", linewidth=0.8)
    ax.set_axisbelow(True)

    handles = [
        Patch(facecolor=CATEGORY_COLORS[category], label=CATEGORY_RU[category])
        for category in category_order
    ]
    ax.legend(
        handles=handles,
        loc="upper center",
        bbox_to_anchor=(0.5, -0.18),
        ncol=3,
        frameon=False,
        fontsize=8.5,
    )
    finish(
        fig,
        ax,
        FIG_DIR / "07_distro_family_category.png",
        "Семейство дистрибутивов × категория",
        "N = 134; внутри полосы — число публикаций (подписи для сегментов ≥7%), в скобках — размер семейства",
    )


def figure_flag_prevalence(rows: list[dict]) -> None:
    total = len(rows)
    counts = Counter(flag for row in rows for flag in FLAGS if row[flag])
    labels = [FLAG_RU[flag] for flag in FLAGS]
    values = [counts.get(flag, 0) for flag in FLAGS]
    colors = [FLAG_COLORS[flag] for flag in FLAGS]

    fig, ax = plt.subplots(figsize=(9.4, 4.5))
    hbar(ax, labels, values, colors, total=total)
    finish(
        fig,
        ax,
        FIG_DIR / "08_flag_prevalence.png",
        "Распространённость флагов",
        f"N = {total}; флаги не взаимоисключающие, поэтому сумма больше 100%",
    )


def figure_category_flag_heatmap(rows: list[dict]) -> None:
    category_counts = Counter(row["problem_category"] for row in rows)
    category_flag = Counter(
        (row["problem_category"], flag)
        for row in rows
        for flag in FLAGS
        if row[flag]
    )
    categories = [
        category for category, _ in category_counts.most_common()
    ]
    matrix = np.array(
        [
            [
                pct(category_flag.get((category, flag), 0), category_counts[category])
                for flag in FLAGS
            ]
            for category in categories
        ]
    )

    fig, ax = plt.subplots(figsize=(9.8, 6.2))
    im = ax.imshow(matrix, cmap="Blues", aspect="auto", vmin=0, vmax=100)
    ax.set_xticks(np.arange(len(FLAGS)))
    ax.set_xticklabels([FLAG_SHORT[flag] for flag in FLAGS], rotation=28, ha="right")
    ax.set_yticks(np.arange(len(categories)))
    ax.set_yticklabels(
        [f"{CATEGORY_RU[category]} ({category_counts[category]})" for category in categories],
        fontsize=9,
    )
    for i in range(matrix.shape[0]):
        for j in range(matrix.shape[1]):
            value = matrix[i, j]
            ax.text(
                j,
                i,
                f"{value:.0f}%",
                ha="center",
                va="center",
                fontsize=8.5,
                color="white" if value > 55 else "#1b2631",
            )
    ax.set_xticks(np.arange(-0.5, len(FLAGS), 1), minor=True)
    ax.set_yticks(np.arange(-0.5, len(categories), 1), minor=True)
    ax.grid(which="minor", color="white", linewidth=1.4)
    ax.tick_params(which="minor", bottom=False, left=False)
    ax.tick_params(axis="both", length=0)
    cbar = fig.colorbar(im, ax=ax, fraction=0.03, pad=0.02)
    cbar.set_label("Доля внутри категории, %", fontsize=8)
    cbar.ax.tick_params(labelsize=8)
    finish(
        fig,
        ax,
        FIG_DIR / "09_category_flag_heatmap.png",
        "Категория × флаг",
        "Значение — доля публикаций категории с данным флагом; в скобках — размер категории",
    )


def figure_flag_cooccurrence(rows: list[dict]) -> None:
    presence = {flag: [row for row in rows if row[flag]] for flag in FLAGS}
    matrix = np.zeros((len(FLAGS), len(FLAGS)))
    for i, first in enumerate(FLAGS):
        for j, second in enumerate(FLAGS):
            union = set(id(row) for row in presence[first]) | set(
                id(row) for row in presence[second]
            )
            intersection = set(id(row) for row in presence[first]) & set(
                id(row) for row in presence[second]
            )
            matrix[i, j] = len(intersection) / len(union) if union else 0.0

    shown = matrix.copy()
    np.fill_diagonal(shown, np.nan)
    cmap = plt.get_cmap("Blues").copy()
    cmap.set_bad("#e5e8e8")

    fig, ax = plt.subplots(figsize=(8.8, 6.6))
    im = ax.imshow(shown, cmap=cmap, aspect="auto", vmin=0, vmax=1)
    ax.set_xticks(np.arange(len(FLAGS)))
    ax.set_xticklabels([FLAG_SHORT[flag] for flag in FLAGS], rotation=28, ha="right")
    ax.set_yticks(np.arange(len(FLAGS)))
    ax.set_yticklabels([FLAG_SHORT[flag] for flag in FLAGS])
    for i in range(len(FLAGS)):
        for j in range(len(FLAGS)):
            if i == j:
                ax.text(j, i, "—", ha="center", va="center", fontsize=10, color="#7f8c8d")
            else:
                value = matrix[i, j]
                ax.text(
                    j,
                    i,
                    f"{value:.2f}",
                    ha="center",
                    va="center",
                    fontsize=9,
                    color="white" if value > 0.55 else "#1b2631",
                )
    ax.set_xticks(np.arange(-0.5, len(FLAGS), 1), minor=True)
    ax.set_yticks(np.arange(-0.5, len(FLAGS), 1), minor=True)
    ax.grid(which="minor", color="white", linewidth=1.6)
    ax.tick_params(which="minor", bottom=False, left=False)
    ax.tick_params(axis="both", length=0)
    cbar = fig.colorbar(im, ax=ax, fraction=0.035, pad=0.02)
    cbar.set_label("Jaccard", fontsize=8)
    cbar.ax.tick_params(labelsize=8)
    finish(
        fig,
        ax,
        FIG_DIR / "10_flag_cooccurrence.png",
        "Пересечение флагов",
        "Jaccard = |A∩B| / |A∪B|; диагональ не показана. Значение 1 означает полное совпадение множеств.",
    )


def figure_comments(rows: list[dict]) -> None:
    data = []
    labels = []
    for platform in PLATFORM_ORDER:
        values = [
            row["comments_num"]
            for row in rows
            if row["platform"] == platform and row["comments_num"] is not None
        ]
        data.append(values)
        labels.append(f"{platform}\n(n={len(values)})")

    fig, ax = plt.subplots(figsize=(10.4, 5.8))
    positions = np.arange(len(data))
    box = ax.boxplot(
        data,
        positions=positions,
        widths=0.52,
        patch_artist=True,
        showfliers=False,
        medianprops={"color": "#111111", "linewidth": 1.8},
        whiskerprops={"color": "#7f8c8d", "linewidth": 1.0},
        capprops={"color": "#7f8c8d", "linewidth": 1.0},
    )
    for patch, platform in zip(box["boxes"], PLATFORM_ORDER):
        color = PLATFORM_COLORS[platform]
        patch.set_facecolor(color)
        patch.set_alpha(0.28)
        patch.set_edgecolor(color)
        patch.set_linewidth(1.2)

    rng = np.random.default_rng(42)
    for index, (platform, values) in enumerate(zip(PLATFORM_ORDER, data)):
        jitter = rng.uniform(-0.15, 0.15, len(values))
        ax.scatter(
            index + jitter,
            values,
            s=14,
            color=PLATFORM_COLORS[platform],
            alpha=0.55,
            edgecolor="none",
            zorder=3,
        )
        median = float(np.median(values))
        ax.text(
            index + 0.30,
            median,
            f"мед. {median:g}",
            ha="left",
            va="center",
            fontsize=8.5,
            color="#333333",
        )

    ax.set_xticks(positions)
    ax.set_xticklabels(labels, fontsize=8.5)
    ax.set_ylabel("Комментарии / ответы / реплики", fontsize=9)
    ax.set_ylim(0, max(max(values) for values in data) * 1.15)
    ax.grid(axis="y", color="#e6e6e6", linewidth=0.8)
    ax.set_axisbelow(True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    finish(
        fig,
        ax,
        FIG_DIR / "11_comments_by_platform.png",
        "Вовлечённость: комментарии по площадкам",
        "Ящики — квартили, точки — публикации; для Stack Exchange это число ответов, а не комментариев",
    )


def figure_scores(rows: list[dict]) -> None:
    platforms = ["Reddit", "Ask Ubuntu", "Unix & Linux SE"]
    data = [
        [
            row["score_num"]
            for row in rows
            if row["platform"] == platform and row["score_num"] is not None
        ]
        for platform in platforms
    ]

    fig, ax = plt.subplots(figsize=(9.6, 5.0))
    rng = np.random.default_rng(7)
    for index, (platform, values) in enumerate(zip(platforms, data)):
        jitter = rng.uniform(-0.16, 0.16, len(values))
        ax.scatter(
            index + jitter,
            values,
            s=22,
            color=PLATFORM_COLORS[platform],
            alpha=0.55,
            edgecolor="none",
            zorder=3,
        )
        median = float(np.median(values))
        ax.plot(
            [index - 0.28, index + 0.28],
            [median, median],
            color="#111111",
            linewidth=3,
            zorder=4,
        )
        ax.text(
            index + 0.33,
            median,
            f"медиана {median:g}",
            va="center",
            fontsize=8.5,
            color="#333333",
        )

    ax.set_xticks(np.arange(len(platforms)))
    ax.set_xticklabels(
        [f"{platform}\n(n={len(values)})" for platform, values in zip(platforms, data)]
    )
    ax.set_yscale("symlog", linthresh=1)
    ax.set_yticks([-1, 0, 1, 2, 5, 10, 20, 50, 80])
    ax.yaxis.set_major_formatter(FuncFormatter(lambda value, _: f"{value:g}"))
    ax.set_ylabel("Рейтинг публикации", fontsize=9)
    ax.grid(axis="y", color="#e6e6e6", linewidth=0.8)
    ax.set_axisbelow(True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    finish(
        fig,
        ax,
        FIG_DIR / "12_score_by_platform.png",
        "Вовлечённость: рейтинг по площадкам",
        "Symlog-шкала; score есть только у Reddit и Stack Exchange (n = 88). GitHub, Fedora и Arch не имеют сопоставимого рейтинга",
    )


def figure_visualization_gap(rows: list[dict]) -> None:
    visual = [row for row in rows if row["mentions_visualization"]]
    category_counts = Counter(row["problem_category"] for row in visual)
    categories = [category for category, _ in category_counts.most_common()]
    labels_left = [CATEGORY_RU[category] for category in categories]
    values_left = [category_counts[category] for category in categories]
    colors_left = [CATEGORY_COLORS[category] for category in categories]
    flags = [
        "mentions_dependencies",
        "mentions_cleanup",
        "mentions_disk_space",
        "mentions_safety",
    ]
    values_right = [
        sum(1 for row in visual if row[flag]) for flag in flags
    ]
    colors_right = [FLAG_COLORS[flag] for flag in flags]
    labels_right = [FLAG_RU[flag] for flag in flags]

    fig, axes = plt.subplots(
        1, 2, figsize=(12.8, 4.9), gridspec_kw={"width_ratios": [1, 1.05]}
    )
    hbar(
        axes[0],
        labels_left,
        values_left,
        colors_left,
        total=len(visual),
        xlabel="Публикаций",
    )
    axes[0].set_title(
        "Категория публикаций с упоминанием визуализации",
        loc="left",
        fontsize=11,
        fontweight="bold",
    )
    hbar(
        axes[1],
        labels_right,
        values_right,
        colors_right,
        total=len(visual),
        xlabel="Публикаций",
    )
    axes[1].set_title(
        "Какие флаги есть у этих публикаций",
        loc="left",
        fontsize=11,
        fontweight="bold",
    )
    fig.suptitle(
        "Визуализация зависимостей: 8 из 134 публикаций (6,0%)",
        x=0.012,
        y=1.035,
        ha="left",
        fontsize=15,
        fontweight="bold",
    )
    fig.text(
        0.012,
        0.975,
        "7 из 8 — прямая категория visualization_request, 1 — unused_packages (DS-009). Только 1 из 8 упоминает безопасность.",
        ha="left",
        fontsize=9,
        color="#5d6d7e",
    )
    fig.subplots_adjust(top=0.83, wspace=0.45)
    fig.savefig(
        FIG_DIR / "13_visualization_gap.png",
        dpi=180,
        bbox_inches="tight",
        facecolor="white",
    )
    plt.close(fig)


def figure_analog_heatmap() -> None:
    matrix = np.array(
        [[item["values"][key] for key, _ in ANALOG_FEATURES] for item in ANALOGS]
    )
    labels = [
        f"{item['short']} ({item['class'].split()[0].lower()})" for item in ANALOGS
    ]

    cmap = LinearSegmentedColormap.from_list(
        "feature_scale", ["#f4f6f7", "#aed6f1", "#1f618d"]
    )
    norm = BoundaryNorm([-0.25, 0.25, 0.75, 1.25], cmap.N)

    fig, ax = plt.subplots(figsize=(14.4, 7.0))
    im = ax.imshow(matrix, cmap=cmap, norm=norm, aspect="auto")
    ax.set_xticks(np.arange(len(ANALOG_FEATURES)))
    ax.set_xticklabels(
        [label for _, label in ANALOG_FEATURES], rotation=30, ha="right", fontsize=9
    )
    ax.set_yticks(np.arange(len(ANALOGS)))
    ax.set_yticklabels(labels, fontsize=9)
    for i in range(matrix.shape[0]):
        for j in range(matrix.shape[1]):
            value = matrix[i, j]
            text = "да" if value == 1.0 else ("част." if value == 0.5 else "нет")
            ax.text(
                j,
                i,
                text,
                ha="center",
                va="center",
                fontsize=8.5,
                color="white" if value == 1.0 else "#1b2631",
            )
    for boundary in (2.5, 5.5):
        ax.axhline(boundary, color="white", linewidth=2.2)
    ax.set_xticks(np.arange(-0.5, len(ANALOG_FEATURES), 1), minor=True)
    ax.set_yticks(np.arange(-0.5, len(ANALOGS), 1), minor=True)
    ax.grid(which="minor", color="white", linewidth=1.2)
    ax.tick_params(which="minor", bottom=False, left=False)
    ax.tick_params(axis="both", length=0)
    cbar = fig.colorbar(im, ax=ax, fraction=0.025, pad=0.02, ticks=[0, 0.5, 1])
    cbar.ax.set_yticklabels(["нет", "частично", "да"], fontsize=8)
    cbar.set_label("Подтверждено документацией", fontsize=8)
    finish(
        fig,
        ax,
        FIG_DIR / "14_analog_feature_heatmap.png",
        "Матрица подтверждённых функций аналогов",
        "8 инструментов; 0 — не заявлено/не подтверждено, 0,5 — частично, 1 — явно заявлено. URPM исключён (HTTP 404).",
    )


def figure_analog_coverage() -> None:
    ordered = sorted(
        ANALOGS, key=lambda item: sum(item["values"].values()), reverse=True
    )
    labels = [
        f"{item['short']} — {item['class'].split()[0].lower()}" for item in ordered
    ]
    values = [sum(item["values"].values()) for item in ordered]
    colors = [
        {
            "Прямой аналог": "#2e86ab",
            "Специализированный инструмент": "#f18f01",
            "Смежное решение": "#6a994e",
        }[item["class"]]
        for item in ordered
    ]

    fig, ax = plt.subplots(figsize=(10.0, 5.4))
    y = np.arange(len(labels))
    bars = ax.barh(
        y,
        values,
        color=colors,
        height=0.64,
        edgecolor="white",
        linewidth=0.6,
    )
    ax.set_yticks(y)
    ax.set_yticklabels(labels)
    ax.invert_yaxis()
    for bar, value in zip(bars, values):
        ax.text(
            value + 0.08,
            bar.get_y() + bar.get_height() / 2,
            f"{value:g}/10 ({value * 10:.0f}%)",
            va="center",
            fontsize=9,
            color="#222222",
        )
    ax.set_xlim(0, 11.4)
    ax.set_xlabel("Сумма подтверждённых признаков (из 10)", fontsize=9)
    ax.grid(axis="x", color="#e6e6e6", linewidth=0.8)
    ax.set_axisbelow(True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    handles = [
        Patch(facecolor="#2e86ab", label="Прямой аналог"),
        Patch(facecolor="#f18f01", label="Специализированный"),
        Patch(facecolor="#6a994e", label="Смежное решение"),
    ]
    ax.legend(handles=handles, loc="lower right", frameon=False, fontsize=8.5)
    finish(
        fig,
        ax,
        FIG_DIR / "15_analog_coverage.png",
        "Индекс покрытия функций аналогов",
        "Описательная сумма 10 признаков, а не оценка качества, зрелости или востребованности",
    )


# ---------------------------------------------------------------------------
# Tables
# ---------------------------------------------------------------------------


def write_tables(rows: list[dict], metrics: dict) -> None:
    total = len(rows)

    overview_rows = [
        ["Всего публикаций", total, "Одна строка — одна публикация"],
        ["Уникальных URL", metrics["input"]["unique_urls"], "Проверено"],
        ["Начало диапазона", metrics["input"]["date_min"], "Самая ранняя публикация"],
        ["Конец диапазона", metrics["input"]["date_max"], "Самая поздняя публикация"],
        ["Опубликовано в 2021+", metrics["input"]["since_2021"], f"{metrics['input']['since_2021_pct']}%"],
        ["Площадок", len(PLATFORM_ORDER), "Reddit, Ask Ubuntu, GitHub, Fedora, Unix & Linux SE, Arch"],
        ["Категорий", len(CATEGORIES), "Одна основная категория на публикацию"],
        ["Топ-3 категории", metrics["categories"]["top3"], f"{metrics['categories']['top3_pct']}% корпуса"],
        ["Зависимости (флаг)", metrics["flags"]["counts"]["mentions_dependencies"], f"{metrics['flags']['shares_pct']['mentions_dependencies']}%"],
        ["Очистка (флаг)", metrics["flags"]["counts"]["mentions_cleanup"], f"{metrics['flags']['shares_pct']['mentions_cleanup']}%"],
        ["Безопасность (флаг)", metrics["flags"]["counts"]["mentions_safety"], f"{metrics['flags']['shares_pct']['mentions_safety']}%"],
        ["Место на диске (флаг)", metrics["flags"]["counts"]["mentions_disk_space"], f"{metrics['flags']['shares_pct']['mentions_disk_space']}%"],
        ["Визуализация (флаг)", metrics["flags"]["counts"]["mentions_visualization"], f"{metrics['flags']['shares_pct']['mentions_visualization']}%"],
        ["Зависимости + очистка", metrics["flags"]["both_dependencies_and_cleanup"], f"{metrics['flags']['both_dependencies_and_cleanup_pct']}%"],
        ["Запрос визуализации (категория)", metrics["visualization"]["category_request_count"], f"{metrics['visualization']['category_request_pct']}%"],
        ["Визуализация + безопасность", metrics["visualization"]["mentions_with_safety"], "Из 8 публикаций с флагом визуализации"],
        ["Score заполнен", sum(1 for row in rows if row["score_num"] is not None), "Reddit 46 + Stack Exchange 42"],
        ["Аналогов в матрице", len(ANALOGS), "URPM исключён: HTTP 404"],
    ]
    write_csv(TABLE_DIR / "01_overview.csv", ["metric", "value", "note"], overview_rows)

    platform_rows = []
    for platform in PLATFORM_ORDER:
        subset = [row for row in rows if row["platform"] == platform]
        comments = [row["comments_num"] for row in subset if row["comments_num"] is not None]
        scores = [row["score_num"] for row in subset if row["score_num"] is not None]
        platform_rows.append(
            [
                platform,
                len(subset),
                pct(len(subset), total),
                len(comments),
                round(float(np.median(comments)), 2) if comments else "",
                round(float(np.mean(comments)), 2) if comments else "",
                len(scores),
                round(float(np.median(scores)), 2) if scores else "",
                round(float(np.mean(scores)), 2) if scores else "",
            ]
        )
    write_csv(
        TABLE_DIR / "02_platform_counts.csv",
        [
            "platform",
            "count",
            "share_pct",
            "comments_n",
            "comments_median",
            "comments_mean",
            "score_n",
            "score_median",
            "score_mean",
        ],
        platform_rows,
    )

    source_rows = [
        [source, platform_of(source), count, pct(count, total)]
        for source, count in Counter(row["source"] for row in rows).most_common()
    ]
    write_csv(
        TABLE_DIR / "03_source_counts.csv",
        ["source", "platform", "count", "share_pct"],
        source_rows,
    )

    distro_rows = [
        [distro, distro_family_of("" if distro == "Не указан" else distro), count, pct(count, total)]
        for distro, count in Counter(row["distro"] or "Не указан" for row in rows).most_common()
    ]
    write_csv(
        TABLE_DIR / "04_distro_counts.csv",
        ["distro", "family", "count", "share_pct"],
        distro_rows,
    )

    family_rows = []
    for family in DISTRO_FAMILIES:
        subset = [row for row in rows if row["distro_family"] == family]
        if not subset:
            continue
        top_category, top_count = Counter(
            row["problem_category"] for row in subset
        ).most_common(1)[0]
        family_rows.append(
            [
                family,
                len(subset),
                pct(len(subset), total),
                top_category,
                top_count,
                pct(top_count, len(subset)),
            ]
        )
    write_csv(
        TABLE_DIR / "05_distro_family_counts.csv",
        ["family", "count", "share_pct", "top_category", "top_category_count", "top_category_share_pct"],
        family_rows,
    )

    category_rows = [
        [
            category,
            CATEGORY_RU[category],
            metrics["categories"]["counts"][category],
            metrics["categories"]["shares_pct"][category],
        ]
        for category in CATEGORIES
    ]
    write_csv(
        TABLE_DIR / "06_category_counts.csv",
        ["category", "label_ru", "count", "share_pct"],
        category_rows,
    )

    year_rows = []
    for year in sorted(metrics["years"]["counts"]):
        subset = [row for row in rows if row["year"] == int(year)]
        top_category, top_count = Counter(
            row["problem_category"] for row in subset
        ).most_common(1)[0]
        year_rows.append(
            [
                year,
                len(subset),
                pct(len(subset), total),
                top_category,
                top_count,
                sum(1 for row in subset if row["mentions_safety"]),
                sum(1 for row in subset if row["mentions_visualization"]),
            ]
        )
    write_csv(
        TABLE_DIR / "07_year_counts.csv",
        ["year", "count", "share_pct", "top_category", "top_category_count", "safety_count", "visualization_count"],
        year_rows,
    )

    platform_category_rows = []
    for platform in PLATFORM_ORDER:
        subset = [row for row in rows if row["platform"] == platform]
        row = [platform, len(subset)]
        row += [
            metrics["cross_tabs"]["platform_category_counts"][platform][category]
            for category in CATEGORIES
        ]
        platform_category_rows.append(row)
    platform_category_rows.append(
        ["Всего", total]
        + [metrics["categories"]["counts"][category] for category in CATEGORIES]
    )
    write_csv(
        TABLE_DIR / "08_platform_category_counts.csv",
        ["platform", "total"] + [CATEGORY_SHORT[category] for category in CATEGORIES],
        platform_category_rows,
    )

    category_flag_rows = []
    for category in CATEGORIES:
        row = [category, metrics["categories"]["counts"][category]]
        for flag in FLAGS:
            row.append(metrics["cross_tabs"]["category_flag_counts"][category][flag])
            row.append(metrics["cross_tabs"]["category_flag_prevalence_pct"][category][flag])
        category_flag_rows.append(row)
    header = ["category", "n"]
    for flag in FLAGS:
        header += [f"{flag}_count", f"{flag}_pct"]
    write_csv(
        TABLE_DIR / "09_category_flag_prevalence.csv",
        header,
        category_flag_rows,
    )

    jaccard_rows = []
    jaccard = metrics["flags"]["jaccard"]
    for first in FLAGS:
        row = [FLAG_RU[first]]
        for second in FLAGS:
            row.append(jaccard[f"{first}|{second}"])
        jaccard_rows.append(row)
    write_csv(
        TABLE_DIR / "10_flag_cooccurrence_jaccard.csv",
        ["flag"] + [FLAG_RU[flag] for flag in FLAGS],
        jaccard_rows,
    )

    engagement_rows = []
    for platform in PLATFORM_ORDER:
        item = metrics["engagement"][platform]
        comments = item["comments"]
        score = item["score"]
        engagement_rows.append(
            [
                platform,
                item["n"],
                comments.get("n", 0),
                comments.get("mean", ""),
                comments.get("median", ""),
                comments.get("q1", ""),
                comments.get("q3", ""),
                comments.get("min", ""),
                comments.get("max", ""),
                score.get("n", 0),
                score.get("mean", ""),
                score.get("median", ""),
                score.get("q1", ""),
                score.get("q3", ""),
                score.get("min", ""),
                score.get("max", ""),
            ]
        )
    write_csv(
        TABLE_DIR / "11_engagement_by_platform.csv",
        [
            "platform",
            "n",
            "comments_n",
            "comments_mean",
            "comments_median",
            "comments_q1",
            "comments_q3",
            "comments_min",
            "comments_max",
            "score_n",
            "score_mean",
            "score_median",
            "score_q1",
            "score_q3",
            "score_min",
            "score_max",
        ],
        engagement_rows,
    )

    visual_rows = [
        [
            row["id"],
            row["platform"],
            row["date"],
            row["problem_category"],
            "да" if row["mentions_safety"] else "нет",
            row["title"],
            row["url"],
        ]
        for row in rows
        if row["mentions_visualization"]
    ]
    write_csv(
        TABLE_DIR / "12_visualization_discussions.csv",
        ["id", "platform", "date", "category", "mentions_safety", "title", "url"],
        visual_rows,
    )

    ranked = sorted(
        rows,
        key=lambda row: (
            -(row["comments_num"] or 0),
            -(row["score_num"] or 0),
            row["id"],
        ),
    )[:15]
    write_csv(
        TABLE_DIR / "13_top_discussions.csv",
        ["id", "platform", "category", "comments", "score", "title", "url"],
        [
            [
                row["id"],
                row["platform"],
                row["problem_category"],
                row["comments_num"],
                row["score_num"] if row["score_num"] is not None else "",
                row["title"],
                row["url"],
            ]
            for row in ranked
        ],
    )

    feature_header = ["tool", "class", "url"] + [key for key, _ in ANALOG_FEATURES] + [
        "coverage_score",
        "coverage_pct",
        "note",
    ]
    feature_rows = []
    for item in ANALOGS:
        feature_rows.append(
            [item["tool"], item["class"], item["url"]]
            + [item["values"][key] for key, _ in ANALOG_FEATURES]
            + [
                sum(item["values"].values()),
                round(100.0 * sum(item["values"].values()) / len(ANALOG_FEATURES), 1),
                item["note"],
            ]
        )
    write_csv(TABLE_DIR / "14_analog_feature_matrix.csv", feature_header, feature_rows)

    coverage_rows = []
    for rank, item in enumerate(
        sorted(
            ANALOGS, key=lambda candidate: sum(candidate["values"].values()), reverse=True
        ),
        start=1,
    ):
        coverage_rows.append(
            [
                rank,
                item["tool"],
                item["class"],
                sum(item["values"].values()),
                round(100.0 * sum(item["values"].values()) / len(ANALOG_FEATURES), 1),
            ]
        )
    write_csv(
        TABLE_DIR / "15_analog_coverage.csv",
        ["rank", "tool", "class", "coverage_score", "coverage_pct"],
        coverage_rows,
    )

    source_header = [
        "tool",
        "class",
        "source_type",
        "url",
        "http_status",
        "stars",
        "forks",
        "open_issues",
        "last_push",
        "license",
        "included_in_matrix",
        "comment",
    ]
    write_csv(
        TABLE_DIR / "16_analog_sources_status.csv",
        source_header,
        [
            [
                item[key]
                for key in [
                    "tool",
                    "class",
                    "source_type",
                    "url",
                    "http_status",
                    "stars",
                    "forks",
                    "open_issues",
                    "last_push",
                    "license",
                    "included",
                    "comment",
                ]
            ]
            for item in ANALOG_SOURCES
        ],
    )

    family_category_rows = []
    for family in DISTRO_FAMILIES:
        subset = [row for row in rows if row["distro_family"] == family]
        if not subset:
            continue
        family_category_rows.append(
            [family, len(subset)]
            + [
                metrics["cross_tabs"]["family_category_counts"][family][category]
                for category in CATEGORIES
            ]
        )
    write_csv(
        TABLE_DIR / "17_distro_family_category.csv",
        ["family", "total"] + [CATEGORY_SHORT[category] for category in CATEGORIES],
        family_category_rows,
    )

    platform_flag_rows = []
    for platform in PLATFORM_ORDER:
        row = [platform, metrics["platforms"]["counts"][platform]]
        for flag in FLAGS:
            row.append(metrics["cross_tabs"]["platform_flag_counts"][platform][flag])
            row.append(
                metrics["cross_tabs"]["platform_flag_prevalence_pct"][platform][flag]
            )
        platform_flag_rows.append(row)
    platform_flag_header = ["platform", "n"]
    for flag in FLAGS:
        platform_flag_header += [f"{flag}_count", f"{flag}_pct"]
    write_csv(
        TABLE_DIR / "18_platform_flag_prevalence.csv",
        platform_flag_header,
        platform_flag_rows,
    )


def write_metrics(metrics: dict) -> None:
    with (HERE / "metrics.json").open("w", encoding="utf-8") as handle:
        json.dump(metrics, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 10,
            "axes.titlesize": 14,
            "axes.titleweight": "bold",
            "axes.edgecolor": "#b0b0b0",
            "axes.labelcolor": "#333333",
            "xtick.color": "#333333",
            "ytick.color": "#333333",
            "figure.facecolor": "white",
            "savefig.facecolor": "white",
            "savefig.pad_inches": 0.18,
        }
    )

    rows = load_rows()
    metrics = build_metrics(rows)

    figure_platform_distribution(rows)
    figure_source_distribution(rows)
    figure_distro_distribution(rows)
    figure_category_distribution(rows)
    figure_yearly_dynamics(rows)
    figure_platform_category_heatmap(rows)
    figure_platform_flag_heatmap(rows)
    figure_distro_family(rows)
    figure_flag_prevalence(rows)
    figure_category_flag_heatmap(rows)
    figure_flag_cooccurrence(rows)
    figure_comments(rows)
    figure_scores(rows)
    figure_visualization_gap(rows)
    figure_analog_heatmap()
    figure_analog_coverage()

    write_tables(rows, metrics)
    write_metrics(metrics)

    print(f"Rows analysed: {len(rows)}")
    print(f"Figures: {len(list(FIG_DIR.glob('*.png')))}")
    print(f"Tables: {len(list(TABLE_DIR.glob('*.csv')))}")
    print(f"Metrics: {HERE / 'metrics.json'}")


if __name__ == "__main__":
    main()
