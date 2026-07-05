"""Deduplicate citizen submissions into Issues (Phase 2 step 4).

Submissions are first bucketed by (theme, resolved_lgd_code) — two reports about
different themes, or in different villages, are never the same issue regardless of
text similarity. Within each bucket, a greedy single-pass clustering merges submissions
whose sentence-embedding cosine similarity to a cluster's running centroid exceeds
COSINE_THRESHOLD. Each resulting cluster becomes one Issue with corroboration_count =
number of submissions in it.
"""

from __future__ import annotations

from collections import defaultdict

import numpy as np

COSINE_THRESHOLD = 0.72


def _cosine(a: np.ndarray, b: np.ndarray) -> float:
    denom = np.linalg.norm(a) * np.linalg.norm(b)
    return float(np.dot(a, b) / denom) if denom else 0.0


def cluster_submissions(submissions: list[dict]) -> list[dict]:
    """submissions: list of {"id", "theme", "resolved_lgd_code", "text", "embedding"}.
    Returns a list of clusters: {"theme", "village_code", "member_ids", "representative_text"}.
    """
    buckets: dict[tuple, list[dict]] = defaultdict(list)
    for s in submissions:
        buckets[(s["theme"], s["resolved_lgd_code"])].append(s)

    clusters: list[dict] = []
    for (theme, village_code), items in buckets.items():
        cluster_vecs: list[np.ndarray] = []
        cluster_members: list[list[dict]] = []

        for item in items:
            vec = np.array(item["embedding"], dtype=float)
            best_idx, best_sim = None, 0.0
            for i, centroid in enumerate(cluster_vecs):
                sim = _cosine(vec, centroid)
                if sim > best_sim:
                    best_idx, best_sim = i, sim
            if best_idx is not None and best_sim >= COSINE_THRESHOLD:
                members = cluster_members[best_idx]
                members.append(item)
                # running centroid = mean of member embeddings
                cluster_vecs[best_idx] = np.mean([np.array(m["embedding"], dtype=float) for m in members], axis=0)
            else:
                cluster_vecs.append(vec)
                cluster_members.append([item])

        for members in cluster_members:
            representative = max(members, key=lambda m: len(m["text"]))
            clusters.append(
                {
                    "theme": theme,
                    "village_code": village_code,
                    "member_ids": [m["id"] for m in members],
                    "representative_text": representative["text"],
                }
            )
    return clusters
