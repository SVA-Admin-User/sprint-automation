from github_common import *


def main():
    cfg = settings()
    project = get_project(cfg)
    status_field = get_field(project, cfg["project_fields"]["status"])
    statuses = cfg["statuses"]

    changed = 0
    for item in project_items(project["id"]):
        issue = item.get("content")
        if not issue:
            continue
        current = item_status(item)
        prs = linked_prs(item)

        desired = None
        if issue.get("closed") or any(pr.get("merged") for pr in prs):
            desired = statuses["done"]
        elif any(pr.get("state") == "OPEN" for pr in prs):
            desired = statuses["in_progress"]

        if desired and desired != current:
            set_status(project["id"], item["id"], status_field, desired)
            changed += 1
            print(f"Updated {issue['repository']['nameWithOwner']}#{issue['number']} from {current} to {desired}")

    print(f"Board sync complete. Items changed: {changed}")


if __name__ == "__main__":
    main()
