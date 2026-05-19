from __future__ import annotations

from resume_builder.extractors import StaticExtractor
from resume_builder.models import Repo, RoleSpec


def _role() -> RoleSpec:
    return RoleSpec(
        id="cybersecurity-blueteam",
        label="Cybersecurity Blue Team",
        keywords=["SIEM", "incident response", "Splunk"],
        must_have_skills=["log analysis"],
        nice_to_have=["YARA"],
    )


def test_extractor_filters_irrelevant_repos(config_dir):
    extractor = StaticExtractor(config_dir / "regex_patterns.json", min_score=1.0)
    repos = [
        Repo(
            name="cooking-blog",
            full_name="me/cooking-blog",
            url="https://github.com/me/cooking-blog",
            description="Recipes and food photography.",
            languages=["JavaScript"],
            topics=["food"],
            readme="A blog about pasta.",
        ),
        Repo(
            name="soc-playbook",
            full_name="me/soc-playbook",
            url="https://github.com/me/soc-playbook",
            description="SOC analyst Splunk detection playbook for incident response.",
            languages=["Python"],
            topics=["security", "siem"],
            readme="Includes Suricata, Sigma rules, log analysis automation.",
        ),
    ]
    evidence = extractor.extract(repos, _role())
    assert len(evidence) == 1
    assert evidence[0].source_id == "me/soc-playbook"
    assert evidence[0].score > 1.0
    assert "Splunk" in evidence[0].matched_terms or "SIEM" in evidence[0].matched_terms


def test_extractor_archived_skipped(config_dir):
    extractor = StaticExtractor(config_dir / "regex_patterns.json", min_score=0.1)
    repos = [
        Repo(
            name="soc-playbook",
            full_name="me/soc-playbook",
            url="https://github.com/me/soc-playbook",
            description="SIEM Splunk",
            archived=True,
        ),
    ]
    assert extractor.extract(repos, _role()) == []
