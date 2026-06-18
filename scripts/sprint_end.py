from github_common import *
from datetime import datetime, timezone


def main():
    cfg = settings()
    sprint_cfg = load_yaml("config/sprint-config.yml")
    sprint_name = sprint_cfg["sprint"]["name"]
    project = get_project(cfg)
    statuses = cfg["statuses"]

    done = []
    unfinished = []
    for item in project_items(project["id"]):
        issue = item.get("content")
        if not issue:
            continue
        status = item_status(item)
        row = f"- [{status}] {issue['repository']['nameWithOwner']}#{issue['number']} - {issue['title']} ({issue['url']})"
        if status == statuses["done"] or issue.get("closed"):
            done.append(row)
        else:
            unfinished.append(row)

    report = []
    report.append(f"# Sprint Report - {sprint_name}")
    report.append("")
    report.append(f"Generated: {datetime.now(timezone.utc).isoformat()}")
    report.append("")
    report.append(f"## Done ({len(done)})")
    report.extend(done or ["- None"])
    report.append("")
    report.append(f"## Not Done / Carryover ({len(unfinished)})")
    report.extend(unfinished or ["- None"])
    report.append("")

    with open("sprint-report.md", "w", encoding="utf-8") as f:
        f.write("\n".join(report))
    print("Created sprint-report.md")


if __name__ == "__main__":
    main()
