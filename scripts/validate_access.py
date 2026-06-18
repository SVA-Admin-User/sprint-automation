from github_common import *

cfg = settings()
print(f"Validating access to org: {cfg['org']}")
org_data = rest("GET", f"/orgs/{cfg['org']}")
print(f"Org OK: {org_data['login']}")

print(f"Validating team access: {cfg['team_slug']}")
members = get_team_members(cfg['org'], cfg['team_slug'])
print(f"Team members found: {len(members)}")
print(", ".join(members[:20]))

print(f"Validating project access: project #{cfg['project_number']}")
project = get_project(cfg)
print(f"Project OK: {project['title']} ({project['id']})")

status_field = get_field(project, cfg['project_fields']['status'])
print("Status options:", ", ".join([o['name'] for o in status_field.get('options', [])]))
