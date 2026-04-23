"""Leave-one-out evaluation of the kNN classifier over `pest_embeddings`.

Loads every embedding, and for each doc predicts its `pest_name` by taking
the top-K cosine neighbors (excluding itself), voting weighted by similarity.
Reports:
  - global accuracy
  - per-class accuracy (with support count)
  - histogram of top-1 similarity when correct vs incorrect
  - suggested threshold: similarity at which correct-rate exceeds 0.9

Run:
    .venv/bin/python -m scripts.calibrate_knn [--k 5]
"""
from __future__ import annotations

import argparse
import os
import sys
from collections import Counter, defaultdict

import numpy as np
from dotenv import load_dotenv
from pymongo import MongoClient

from auth.secrets import load_secrets


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--k", type=int, default=5)
    parser.add_argument(
        "--min-correct-rate",
        type=float,
        default=0.9,
        help="Target correct-rate for the suggested threshold.",
    )
    args = parser.parse_args()

    load_dotenv()
    project_id = os.environ.get("GOOGLE_CLOUD_PROJECT", "")
    mode = os.environ.get("MODE", "DEV")
    load_secrets(mode, project_id, ["MONGODB_URI"])

    mongo = MongoClient(os.environ["MONGODB_URI"])
    collection = mongo["agrogem"]["pest_embeddings"]

    docs = list(collection.find({}, {"_id": 1, "pest_name": 1, "embedding": 1}))
    n = len(docs)
    if n == 0:
        print("No docs found.")
        return 1

    labels = [d["pest_name"] for d in docs]
    vectors = np.asarray([d["embedding"] for d in docs], dtype=np.float32)
    print(f"Loaded {n} vectors, dim={vectors.shape[1]}")

    # Normalize once so cosine = dot product.
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    normalized = vectors / norms

    # Full similarity matrix (n x n). For n=5000 this is ~100MB, fine.
    sims = normalized @ normalized.T
    np.fill_diagonal(sims, -np.inf)  # exclude self

    k = args.k
    # top-k indices per row, not necessarily sorted
    top_k_idx = np.argpartition(-sims, kth=k - 1, axis=1)[:, :k]

    correct = 0
    per_class_total: Counter[str] = Counter()
    per_class_correct: Counter[str] = Counter()
    top1_correct_sims: list[float] = []
    top1_wrong_sims: list[float] = []

    for i in range(n):
        neighbors = top_k_idx[i]
        weights: dict[str, float] = defaultdict(float)
        for j in neighbors:
            s = float(sims[i, j])
            if s <= 0:
                continue
            weights[labels[j]] += s
        if not weights:
            predicted = None
        else:
            predicted = max(weights.items(), key=lambda kv: kv[1])[0]

        true_label = labels[i]
        per_class_total[true_label] += 1

        # top-1 raw similarity (highest-similarity neighbor)
        best_j = int(neighbors[np.argmax(sims[i, neighbors])])
        top1_sim = float(sims[i, best_j])

        if predicted == true_label:
            correct += 1
            per_class_correct[true_label] += 1
            top1_correct_sims.append(top1_sim)
        else:
            top1_wrong_sims.append(top1_sim)

    acc = correct / n
    print(f"\nGlobal accuracy (k={k}): {acc:.3f}  ({correct}/{n})")

    print("\nPer-class accuracy:")
    for cls in sorted(per_class_total):
        tot = per_class_total[cls]
        cor = per_class_correct[cls]
        print(f"  {cls:40s} {cor:3d}/{tot:3d}  ({cor / tot:.2f})")

    print("\nTop-1 similarity histogram (bin width 0.05):")
    bins = np.arange(-0.5, 1.05, 0.05)
    correct_hist, _ = np.histogram(top1_correct_sims, bins=bins)
    wrong_hist, _ = np.histogram(top1_wrong_sims, bins=bins)
    print(f"  {'bin':>10}  {'correct':>8}  {'wrong':>8}")
    for i in range(len(bins) - 1):
        if correct_hist[i] == 0 and wrong_hist[i] == 0:
            continue
        lo = bins[i]
        print(f"  {lo:>10.2f}  {correct_hist[i]:>8d}  {wrong_hist[i]:>8d}")

    # Suggested threshold: smallest sim where rolling correct-rate >= target.
    all_points = sorted(
        [(s, True) for s in top1_correct_sims] + [(s, False) for s in top1_wrong_sims],
        key=lambda t: -t[0],
    )
    running_c = 0
    running_w = 0
    suggested: float | None = None
    for s, is_correct in all_points:
        if is_correct:
            running_c += 1
        else:
            running_w += 1
        total = running_c + running_w
        if total >= 20 and running_c / total >= args.min_correct_rate:
            suggested = s
    if suggested is not None:
        print(
            f"\nSuggested min-similarity threshold (>= {args.min_correct_rate:.0%} correct): {suggested:.3f}"
        )
    else:
        print(
            f"\nNo threshold reached target correct-rate {args.min_correct_rate:.0%} — consider re-embedding or more data."
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
