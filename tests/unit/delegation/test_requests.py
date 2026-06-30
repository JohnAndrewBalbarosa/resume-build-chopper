from __future__ import annotations

from org_ops.delegation.models import DelegationNode, DelegationTree, Level
from org_ops.delegation.requests import ChangeControlBoard, submit_drill_up


def _tree():
    t = DelegationTree(event="E")
    t.add(DelegationNode(id="root", level=Level.ROOT, children=["root.A"]))
    t.add(DelegationNode(id="root.A", level=Level.EXEC, responsibilities=["old"]))
    return t


def test_drill_up_request_records_idea():
    r = submit_drill_up("root.A.x", "root.A", "idea", "let's add a sponsor track")
    assert r.kind == "idea" and r.to_id == "root.A"


def test_ccb_approve_change_mutates_tree():
    ccb = ChangeControlBoard(_tree())
    req = ccb.submit("root.A", "root", "change", {"responsibilities": ["new"]})
    done = ccb.decide(req, approve=True)
    assert done.status == "approved"
    assert ccb.tree.nodes["root.A"].responsibilities == ["new"]


def test_ccb_reject_does_not_mutate():
    ccb = ChangeControlBoard(_tree())
    req = ccb.submit("root.A", "root", "change", {"responsibilities": ["new"]})
    done = ccb.decide(req, approve=False, reason="out of scope")
    assert done.status == "rejected" and done.reason == "out of scope"
    assert ccb.tree.nodes["root.A"].responsibilities == ["old"]  # unchanged
