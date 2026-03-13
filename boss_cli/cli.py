"""CLI entry point for Boss CLI."""

from __future__ import annotations

import asyncio
import json
import logging
import sys

import click
from rich.console import Console
from rich.table import Table

from boss_cli.auth import clear_credential, get_credential, qr_login
from boss_cli.client import BossClient, list_cities, resolve_city
from boss_cli.constants import DEGREE_CODES, EXP_CODES, SALARY_CODES

console = Console()


@click.group()
@click.option("-v", "--verbose", is_flag=True, help="Enable debug logging")
def cli(verbose: bool) -> None:
    """Boss CLI — 在终端使用 BOSS 直聘 🤝"""
    level = logging.DEBUG if verbose else logging.WARNING
    logging.basicConfig(level=level, format="%(name)s: %(message)s")


# ── Auth commands ───────────────────────────────────────────────────

@cli.command()
def login() -> None:
    """扫码登录 Boss 直聘 APP"""
    try:
        asyncio.run(qr_login())
    except RuntimeError as e:
        console.print(f"[red]❌ {e}[/red]")
        sys.exit(1)


@cli.command()
def logout() -> None:
    """清除已保存的登录凭证"""
    clear_credential()
    console.print("[green]✅ 已退出登录[/green]")


@cli.command()
def status() -> None:
    """查看当前登录状态"""
    cred = get_credential()
    if cred:
        n = len(cred.cookies)
        console.print(f"[green]✅ 已登录[/green] ({n} cookies)")
    else:
        console.print("[yellow]⚠️  未登录[/yellow]，使用 [bold]boss login[/bold] 扫码登录")


# ── Job Search ──────────────────────────────────────────────────────

@cli.command()
@click.argument("keyword")
@click.option("-c", "--city", default="全国", help="城市名称或代码 (默认: 全国)")
@click.option("-p", "--page", default=1, type=int, help="页码 (默认: 1)")
@click.option("--salary", type=click.Choice(list(SALARY_CODES.keys())), help="薪资筛选")
@click.option("--exp", type=click.Choice(list(EXP_CODES.keys())), help="工作经验筛选")
@click.option("--degree", type=click.Choice(list(DEGREE_CODES.keys())), help="学历筛选")
@click.option("--json-output", "as_json", is_flag=True, help="输出原始 JSON")
def search(keyword: str, city: str, page: int, salary: str | None, exp: str | None, degree: str | None, as_json: bool) -> None:
    """搜索职位 (例: boss search Python --city 北京)"""
    cred = get_credential()
    asyncio.run(_search(keyword, city, page, salary, exp, degree, as_json, cred))


async def _search(
    keyword: str,
    city: str,
    page: int,
    salary: str | None,
    exp: str | None,
    degree: str | None,
    as_json: bool,
    cred: object | None,
) -> None:
    city_code = resolve_city(city)
    salary_code = SALARY_CODES.get(salary) if salary else None
    exp_code = EXP_CODES.get(exp) if exp else None
    degree_code = DEGREE_CODES.get(degree) if degree else None

    async with BossClient(cred) as client:
        try:
            data = await client.search_jobs(
                query=keyword,
                city=city_code,
                page=page,
                experience=exp_code,
                degree=degree_code,
                salary=salary_code,
            )
        except Exception as e:
            console.print(f"[red]❌ 搜索失败: {e}[/red]")
            return

    job_list = data.get("jobList", [])

    if as_json:
        click.echo(json.dumps(data, indent=2, ensure_ascii=False))
        return

    if not job_list:
        console.print("[yellow]没有找到匹配的职位[/yellow]")
        return

    # Build filter description
    filters = [city]
    if salary:
        filters.append(salary)
    if exp:
        filters.append(exp)
    if degree:
        filters.append(degree)
    filter_str = " · ".join(filters)

    table = Table(
        title=f"🔍 搜索: {keyword} ({filter_str}) — {len(job_list)} 个结果",
        show_lines=True,
    )
    table.add_column("#", style="dim", width=3)
    table.add_column("职位", style="bold cyan", max_width=30)
    table.add_column("公司", style="green", max_width=20)
    table.add_column("薪资", style="yellow", max_width=12)
    table.add_column("经验", max_width=10)
    table.add_column("学历", max_width=8)
    table.add_column("地区", style="blue", max_width=15)
    table.add_column("技能", style="dim", max_width=20)

    for i, job in enumerate(job_list, 1):
        # Extract skills
        skills = job.get("skills", [])
        skill_str = ", ".join(skills[:3]) if skills else "-"

        # Build location
        area = job.get("areaDistrict", "")
        biz = job.get("businessDistrict", "")
        location = f"{area} {biz}".strip() if area else job.get("cityName", "-")

        table.add_row(
            str(i),
            job.get("jobName", "-"),
            job.get("brandName", "-"),
            job.get("salaryDesc", "-"),
            job.get("jobExperience", "-"),
            job.get("jobDegree", "-"),
            location,
            skill_str,
        )

    console.print(table)

    # Show pagination info
    has_more = data.get("hasMore", False)
    if has_more:
        console.print(f"\n  [dim]▸ 更多结果: boss search \"{keyword}\" --city {city} -p {page + 1}[/dim]")


# ── Recommend ───────────────────────────────────────────────────────

@cli.command()
@click.option("-p", "--page", default=1, type=int, help="页码 (默认: 1)")
@click.option("--json-output", "as_json", is_flag=True, help="输出原始 JSON")
def recommend(page: int, as_json: bool) -> None:
    """查看推荐职位 (基于求职期望)"""
    cred = get_credential()
    if not cred:
        console.print("[yellow]⚠️  未登录[/yellow]，使用 [bold]boss login[/bold] 扫码登录")
        sys.exit(1)
    asyncio.run(_recommend(page, as_json, cred))


async def _recommend(page: int, as_json: bool, cred: object) -> None:
    async with BossClient(cred) as client:
        try:
            data = await client.get_recommend_jobs(page=page)
        except Exception as e:
            console.print(f"[red]❌ 获取推荐失败: {e}[/red]")
            return

    job_list = data.get("jobList", [])

    if as_json:
        click.echo(json.dumps(data, indent=2, ensure_ascii=False))
        return

    if not job_list:
        console.print("[yellow]暂无推荐职位，请先设置求职期望[/yellow]")
        return

    table = Table(
        title=f"⭐ 推荐职位 (第 {page} 页 · {len(job_list)} 个)",
        show_lines=True,
    )
    table.add_column("#", style="dim", width=3)
    table.add_column("职位", style="bold cyan", max_width=30)
    table.add_column("公司", style="green", max_width=20)
    table.add_column("薪资", style="yellow", max_width=12)
    table.add_column("经验", max_width=10)
    table.add_column("学历", max_width=8)
    table.add_column("地区", style="blue", max_width=15)

    for i, job in enumerate(job_list, 1):
        area = job.get("areaDistrict", "")
        biz = job.get("businessDistrict", "")
        location = f"{area} {biz}".strip() if area else job.get("cityName", "-")

        table.add_row(
            str(i),
            job.get("jobName", "-"),
            job.get("brandName", "-"),
            job.get("salaryDesc", "-"),
            job.get("jobExperience", "-"),
            job.get("jobDegree", "-"),
            location,
        )

    console.print(table)

    has_more = data.get("hasMore", False)
    if has_more:
        console.print(f"\n  [dim]▸ 更多推荐: boss recommend -p {page + 1}[/dim]")


# ── Cities ──────────────────────────────────────────────────────────

@cli.command()
def cities() -> None:
    """列出支持的城市代码"""
    codes = list_cities()
    table = Table(title="🏙️ 支持的城市", show_lines=False)
    table.add_column("城市", style="cyan", width=10)
    table.add_column("代码", style="dim", width=12)

    for name, code in codes.items():
        table.add_row(name, code)

    console.print(table)
    console.print(f"\n  [dim]共 {len(codes)} 个城市。使用: boss search \"Python\" --city 杭州[/dim]")


# ── Entry ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    cli()
