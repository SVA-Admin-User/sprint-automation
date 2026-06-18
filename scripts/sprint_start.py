from github_common import *


def pick_assignee(cfg, story, members, all_repos):
    users_cfg = cfg.get("users", {})
    max_open = cfg.get("assignment", {}).get("max_open_issues_per_user", 5)
    skip_unavailable = cfg.get("assignment", {}).get("skip_unavailable_users", True)
    story_skills = set(story.get("skills", []))
    candidates = []
    for member in members:
        profile = users_cfg.get(member, {})
        if skip_unavailable and profile.get("unavailable") is True:
            continue
        open_count = count_open_assigned_issues(cfg["org"], all_repos, member)
        if open_count >= max_open:
            continue
        skill_score = len(story_skills.intersection(set(profile.get("skills", []))))
        candidates.append((open_count, -skill_score, member))
    if not candidates:
        raise RuntimeError("No eligible team member found. Check team_slug/users/max_open_issues_per_user.")
    candidates.sort()
    return candidates[0][2]


def main():
    cfg = settings()
    sprint_cfg = load_yaml("config/sprint-config.yml")
    sprint = sprint_cfg["sprint"]
    stories = sprint_cfg.get("stories", [])
    if not stories:
        raise RuntimeError("No stories found in config/sprint-config.yml")

    project = get_project(cfg)
    status_field = get_field(project, cfg["project_fields"]["status"])
    iteration_field = get_optional_iteration_field(project, cfg["project_fields"].get("sprint_candidates", []))
    members = get_team_members(cfg["org"], cfg["team_slug"])
    all_repos = sorted(set([s["repo"] for s in stories]))

    print(f"Project: {project['title']}")
    print(f"Team members found: {len(members)}")

    for story in stories:
        assignee = pick_assignee(cfg, story, members, all_repos)
        body = f"{story.get('body', '')}\n\n---\nSprint: {sprint['name']}\nStory Points: {story.get('points', '')}\nCreated by sprint automation."
        issue = create_issue(cfg["org"], story["repo"], story["title"], body, story.get("labels", []), assignee)
        item_id = add_issue_to_project(project["id"], issue["node_id"])
        set_status(project["id"], item_id, status_field, cfg["statuses"]["todo"])
        if iteration_field:
            set_iteration(project["id"], item_id, iteration_field, sprint["name"])
        print(f"Created: {issue['html_url']} | assignee={assignee} | status={cfg['statuses']['todo']}")


if __name__ == "__main__":
    main()
