"""Repositories the signed-in user has granted to the CryptoAudit GitHub App."""

from pathlib import PurePosixPath
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends

from cryptoaudit.api.dependencies import current_session, get_services
from cryptoaudit.api.schemas import RepoOut, RepoTreeOut, TreeNode
from cryptoaudit.api.services import Services
from cryptoaudit.ingest.github_client import TreeEntry
from cryptoaudit.storage.web_store import SessionInfo

router = APIRouter(prefix="/repos", tags=["repositories"])
MAX_TREE_ENTRIES = 5000


@router.get("", response_model=List[RepoOut])
def list_repos(session: SessionInfo = Depends(current_session), services: Services = Depends(get_services)) -> List[RepoOut]:
    with services.github(session.access_token) as client:
        return [RepoOut(**repo.model_dump(exclude={"html_url"})) for repo in client.list_installation_repos()]


@router.get("/{owner}/{name}/tree", response_model=RepoTreeOut)
def repo_tree(
    owner: str,
    name: str,
    ref: Optional[str] = None,
    session: SessionInfo = Depends(current_session),
    services: Services = Depends(get_services),
) -> RepoTreeOut:
    with services.github(session.access_token) as client:
        repo = client.get_repo(owner, name)
        branch = ref or repo.default_branch
        entries, truncated = client.get_tree(owner, name, branch)
    if len(entries) > MAX_TREE_ENTRIES:
        entries, truncated = entries[:MAX_TREE_ENTRIES], True
    blobs = [e for e in entries if e.type == "blob"]
    return RepoTreeOut(
        repository=repo.full_name,
        ref=branch,
        tree=build_tree(repo.name, entries),
        files=len(blobs),
        python_files=sum(1 for e in blobs if e.path.endswith(".py")),
        total_size=sum(e.size or 0 for e in blobs),
        truncated=truncated,
    )


def build_tree(root_name: str, entries: List[TreeEntry]) -> TreeNode:
    """Nest GitHub's flat tree listing into folders and files (folders first, then alphabetical)."""
    root = TreeNode(name=root_name, type="folder")
    folders: Dict[str, TreeNode] = {"": root}
    for entry in sorted(entries, key=lambda e: e.path):
        path = PurePosixPath(entry.path)
        parent_key = str(path.parent) if str(path.parent) != "." else ""
        parent = folders.get(parent_key)
        if parent is None:
            continue
        if entry.type == "tree":
            node = TreeNode(name=path.name, type="folder")
            folders[entry.path] = node
        elif entry.type == "blob":
            node = TreeNode(name=path.name, type="file", size=entry.size, ext=path.suffix or None)
        else:
            continue
        parent.children.append(node)

    def order(node: TreeNode) -> None:
        node.children.sort(key=lambda child: (child.type != "folder", child.name.lower()))
        for child in node.children:
            order(child)

    order(root)
    return root
