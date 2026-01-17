#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gap Rescue Mechanism Demo

This script demonstrates the three-tier judgment logic for speaker recognition.
"""

def judge_speaker_recognition(top1_score: float, top2_score: float) -> tuple[str, str]:
    """
    Simulate the gap rescue mechanism
    
    Returns:
        (decision, reason)
    """
    # Thresholds
    score_threshold = 0.58  # High confidence threshold
    min_accept_score = 0.40  # Minimum tolerable score
    gap_threshold = 0.15  # Gap rescue threshold
    
    score_gap = top1_score - top2_score
    
    # Situation A: High confidence
    if top1_score >= score_threshold:
        return "✅ ACCEPT", f"High confidence (score={top1_score:.3f} >= {score_threshold})"
    
    # Situation B: Gap rescue
    if top1_score >= min_accept_score and score_gap >= gap_threshold:
        return "✅ ACCEPT", f"Gap rescue (score={top1_score:.3f} >= {min_accept_score}, gap={score_gap:.3f} >= {gap_threshold})"
    
    # Situation C: Complete rejection
    if top1_score < min_accept_score:
        return "❌ REJECT", f"Score too low (score={top1_score:.3f} < {min_accept_score})"
    else:
        return "❌ REJECT", f"Gap too small (gap={score_gap:.3f} < {gap_threshold})"


if __name__ == "__main__":
    print("=" * 80)
    print("Gap Rescue Mechanism Demo")
    print("=" * 80)
    print()
    print("Thresholds:")
    print("  - High confidence: >= 0.58")
    print("  - Minimum accept: >= 0.40")
    print("  - Gap threshold: >= 0.15")
    print()
    print("=" * 80)
    print()
    
    # Test cases
    test_cases = [
        # (top1_score, top2_score, description)
        (0.66, 0.30, "Case 1: High confidence (should accept)"),
        (0.59, 0.30, "Case 2: User's 0.59 case (should accept via gap rescue)"),
        (0.50, 0.25, "Case 3: Gap rescue success (should accept)"),
        (0.50, 0.45, "Case 4: Gap too small (should reject)"),
        (0.35, 0.15, "Case 5: Score too low (should reject)"),
        (0.270, 0.240, "Case 6: User's test result (should reject)"),
        (0.45, 0.20, "Case 7: Good gap but medium score (should accept)"),
        (0.40, 0.20, "Case 8: Minimum score with good gap (should accept)"),
        (0.39, 0.10, "Case 9: Just below minimum (should reject)"),
    ]
    
    for top1, top2, description in test_cases:
        decision, reason = judge_speaker_recognition(top1, top2)
        gap = top1 - top2
        
        print(f"{description}")
        print(f"  Top-1: {top1:.3f}, Top-2: {top2:.3f}, Gap: {gap:.3f}")
        print(f"  {decision}: {reason}")
        print()
    
    print("=" * 80)
    print("Summary:")
    print("  ✅ Accept if: score >= 0.58 (high confidence)")
    print("  ✅ Accept if: 0.40 <= score < 0.58 AND gap >= 0.15 (gap rescue)")
    print("  ❌ Reject if: score < 0.40 OR gap < 0.15")
    print("=" * 80)
