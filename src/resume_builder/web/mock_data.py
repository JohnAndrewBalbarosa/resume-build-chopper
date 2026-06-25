"""Mock data for the CareerLens AI prototype UI.

The data mirrors the hackathon concept document without enabling live scraping,
AI calls, or storage yet.
"""

from __future__ import annotations


PROTOTYPE_DATA = {
    "student": {
        "name": "Juan Dela Cruz",
        "program": "4th Year BS Computer Science",
        "school": "FEU Tech",
        "target_role": "Full-Stack Development Internship",
        "readiness_score": 82,
        "resume_version": "ATS Internship Resume",
    },
    "sources": [
        {
            "name": "GitHub",
            "count": 12,
            "status": "Imported",
            "signal": "Projects, tech stack, README evidence",
        },
        {
            "name": "LinkedIn",
            "count": 18,
            "status": "Reviewed",
            "signal": "Achievements, roles, event participation",
        },
        {
            "name": "Certificates",
            "count": 6,
            "status": "Verified",
            "signal": "Coursework and digital badges",
        },
        {
            "name": "Previous Resume",
            "count": 1,
            "status": "Parsed",
            "signal": "Education and contact baseline",
        },
    ],
    "career_nodes": [
        {"label": "Hackathon Finalist", "type": "Achievement", "confidence": 96},
        {"label": "Campus Event Platform", "type": "Project", "confidence": 91},
        {"label": "React + FastAPI", "type": "Skill Cluster", "confidence": 89},
        {"label": "Student Org Tech Lead", "type": "Leadership", "confidence": 84},
        {"label": "Cloud Fundamentals", "type": "Certification", "confidence": 78},
    ],
    "resume_sections": [
        {
            "name": "Profile Summary",
            "status": "Ready",
            "detail": "Positioned for internships with software delivery and leadership evidence.",
        },
        {
            "name": "Projects",
            "status": "Strong",
            "detail": "4 projects selected from 12 repositories based on role relevance.",
        },
        {
            "name": "Experience",
            "status": "Needs numbers",
            "detail": "Add metrics for event attendance, user count, or delivery timeline.",
        },
        {
            "name": "Skills",
            "status": "Ready",
            "detail": "Grouped by frontend, backend, database, and developer tooling.",
        },
    ],
    "recommendations": [
        {
            "title": "Add measurable project outcomes",
            "priority": "High",
            "detail": "Use deployment count, active users, performance gains, or team size.",
        },
        {
            "title": "Close the cloud deployment gap",
            "priority": "Medium",
            "detail": "Complete one cloud-hosted project and document CI/CD steps.",
        },
        {
            "title": "Prepare interview stories",
            "priority": "Medium",
            "detail": "Convert hackathon and org work into STAR-format examples.",
        },
    ],
    "cdo": {
        "advisor": "Maria Santos",
        "queue": 36,
        "ready": 21,
        "needs_review": 9,
        "at_risk": 6,
        "insight": "Most students have project evidence but weak quantified impact statements.",
    },
}
