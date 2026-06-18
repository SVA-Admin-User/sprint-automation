import os
import sys
import yaml
import requests
from typing import Any, Dict, List, Optional

API = "https://api.github.com"
GRAPHQL = "https://api.github.com/graphql"

TOKEN = os.environ.get("GH_AUTOMATION_TOKEN")
if not TOKEN:
    print("ERROR: Missing GH_AUTOMATION_TOKEN repository secret.", file=sys.stderr)
    sys.exit(1)

REST_HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}
GQL_HEADERS = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}


def load_yaml(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def settings() -> Dict[str, Any]:
    return load_yaml("config/settings.yml")


def rest(method: str, path: str, **kwargs) -> Any:
    response = requests.request(method, f"{API}{path}", headers=REST_HEADERS, timeout=45, **kwargs)
    if response.status_code >= 300:
        raise RuntimeError(f"REST {method} {path} failed: {response.status_code} {response.text}")
    return response.json() if response.text else None


def gql(query: str, variables: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    response = requests.post(GRAPHQL, headers=GQL_HEADERS, json={"query": query, "variables": variables or {}}, timeout=45)
    if response.status_code >= 300:
        raise RuntimeError(f"GraphQL failed: {response.status_code} {response.text}")
    data = response.json()
    if data.get("errors"):
        raise RuntimeError(f"GraphQL errors: {data['errors']}")
    return data["data"]


def get_project(cfg: Dict[str, Any]) -> Dict[str, Any]:
    query = """
    query($org: String!, $number: Int!) {
      organization(login: $org) {
        projectV2(number: $number) {
          id
          title
          fields(first: 100) {
            nodes {
              ... on ProjectV2FieldCommon { id name dataType }
              ... on ProjectV2SingleSelectField { id name dataType options { id name } }
              ... on ProjectV2IterationField { id name dataType configuration { iterations { id title startDate duration } } }
            }
          }
        }
      }
    }
    """
    data = gql(query, {"org": cfg["org"], "number": int(cfg["project_number"])})
    project = data["organization"]["projectV2"]
    if not project:
        raise RuntimeError("Project not found. Check config/settings.yml project_number.")
    return project


def get_field(project: Dict[str, Any], field_name: str) -> Dict[str, Any]:
    for field in project["fields"]["nodes"]:
        if field and field.get("name") == field_name:
            return field
    raise RuntimeError(f"Project field not found: {field_name}")


def get_optional_iteration_field(project: Dict[str, Any], candidates: List[str]) -> Optional[Dict[str, Any]]:
    for name in candidates:
        for field in project["fields"]["nodes"]:
            if field and field.get("name") == name and field.get("dataType") == "ITERATION":
                return field
    return None


def set_status(project_id: str, item_id: str, status_field: Dict[str, Any], status_name: str) -> None:
    option = next((o for o in status_field.get("options", []) if o["name"] == status_name), None)
    if not option:
        raise RuntimeError(f"Status option not found: {status_name}. Check board status values.")
    mutation = """
    mutation($projectId: ID!, $itemId: ID!, $fieldId: ID!, $optionId: String!) {
      updateProjectV2ItemFieldValue(input: {
        projectId: $projectId,
        itemId: $itemId,
        fieldId: $fieldId,
        value: { singleSelectOptionId: $optionId }
      }) { projectV2Item { id } }
    }
    """
    gql(mutation, {"projectId": project_id, "itemId": item_id, "fieldId": status_field["id"], "optionId": option["id"]})


def set_iteration(project_id: str, item_id: str, iteration_field: Dict[str, Any], sprint_name: str) -> None:
    iterations = iteration_field.get("configuration", {}).get("iterations", [])
    selected = next((i for i in iterations if i["title"] == sprint_name), None)
    if not selected:
        print(f"WARN: Sprint/Iteration '{sprint_name}' not found on project. Skipping iteration update.")
        return
    mutation = """
    mutation($projectId: ID!, $itemId: ID!, $fieldId: ID!, $iterationId: String!) {
      updateProjectV2ItemFieldValue(input: {
        projectId: $projectId,
        itemId: $itemId,
        fieldId: $fieldId,
        value: { iterationId: $iterationId }
      }) { projectV2Item { id } }
    }
    """
    gql(mutation, {"projectId": project_id, "itemId": item_id, "fieldId": iteration_field["id"], "iterationId": selected["id"]})


def add_issue_to_project(project_id: str, issue_node_id: str) -> str:
    mutation = """
    mutation($projectId: ID!, $contentId: ID!) {
      addProjectV2ItemById(input: {projectId: $projectId, contentId: $contentId}) { item { id } }
    }
    """
    data = gql(mutation, {"projectId": project_id, "contentId": issue_node_id})
    return data["addProjectV2ItemById"]["item"]["id"]


def get_team_members(org: str, team_slug: str) -> List[str]:
    members: List[str] = []
    page = 1
    while True:
        page_data = rest("GET", f"/orgs/{org}/teams/{team_slug}/members", params={"per_page": 100, "page": page})
        if not page_data:
            break
        members.extend([member["login"] for member in page_data])
        if len(page_data) < 100:
            break
        page += 1
    return members


def count_open_assigned_issues(org: str, repos: List[str], assignee: str) -> int:
    total = 0
    for repo in repos:
        try:
            issues = rest("GET", f"/repos/{org}/{repo}/issues", params={"state": "open", "assignee": assignee, "per_page": 100})
            total += len([i for i in issues if "pull_request" not in i])
        except Exception as exc:
            print(f"WARN: Could not count issues for {assignee} in {repo}: {exc}")
    return total


def create_issue(org: str, repo: str, title: str, body: str, labels: List[str], assignee: str) -> Dict[str, Any]:
    payload = {"title": title, "body": body, "labels": labels, "assignees": [assignee] if assignee else []}
    return rest("POST", f"/repos/{org}/{repo}/issues", json=payload)


def project_items(project_id: str) -> List[Dict[str, Any]]:
    query = """
    query($projectId: ID!, $cursor: String) {
      node(id: $projectId) {
        ... on ProjectV2 {
          items(first: 100, after: $cursor) {
            pageInfo { hasNextPage endCursor }
            nodes {
              id
              content {
                ... on Issue {
                  id
                  number
                  title
                  state
                  closed
                  url
                  repository { name nameWithOwner }
                }
              }
              fieldValues(first: 50) {
                nodes {
                  ... on ProjectV2ItemFieldSingleSelectValue { name field { ... on ProjectV2FieldCommon { name } } }
                  ... on ProjectV2ItemFieldPullRequestValue {
                    field { ... on ProjectV2FieldCommon { name } }
                    pullRequests(first: 20) { nodes { number state merged url repository { nameWithOwner } } }
                  }
                }
              }
            }
          }
        }
      }
    }
    """
    all_items: List[Dict[str, Any]] = []
    cursor = None
    while True:
        data = gql(query, {"projectId": project_id, "cursor": cursor})
        items = data["node"]["items"]
        all_items.extend(items["nodes"])
        if not items["pageInfo"]["hasNextPage"]:
            return all_items
        cursor = items["pageInfo"]["endCursor"]


def item_status(item: Dict[str, Any]) -> Optional[str]:
    for fv in item.get("fieldValues", {}).get("nodes", []):
        if fv and fv.get("field", {}).get("name") == "Status":
            return fv.get("name")
    return None


def linked_prs(item: Dict[str, Any]) -> List[Dict[str, Any]]:
    prs: List[Dict[str, Any]] = []
    for fv in item.get("fieldValues", {}).get("nodes", []):
        if fv and "pullRequests" in fv:
            prs.extend(fv["pullRequests"]["nodes"])
    return prs
