"""Assemble the final writeup (deliverable 4) from computed results.

Generated rather than hand-written so the numbers in the prose cannot drift away
from the numbers in the analysis. The interpretation is templated on the sign
and significance of the adjusted lift, so the conclusion follows the data rather
than the other way round.
"""

import argparse
import json
import os


def verdict_for(a2):
    """Turn the adjusted lift + CI on winner_3x into a stated conclusion."""
    w = a2.get("winner_3x") or {}
    lift = w.get("adjusted_lift")
    ci = w.get("ci") or [None, None]
    if lift is None or ci[0] is None:
        return "INCONCLUSIVE", "not enough data to estimate lift."
    lo, hi = ci
    if lo > 1.0:
        return "POSITIVE", (
            f"Conditioning on the subreddit raised the density of 3x winners by "
            f"{lift:.2f}x after adjusting for size, and the 95% interval "
            f"[{lo:.2f}, {hi:.2f}] excludes 1.0. On this evidence the funnel is "
            f"doing real work.")
    if hi < 1.0:
        return "NEGATIVE", (
            f"Adjusted lift is {lift:.2f}x with interval [{lo:.2f}, {hi:.2f}], "
            f"entirely below 1.0 - names the sub discussed produced FEWER 3x "
            f"winners than size-matched controls.")
    return "NULL", (
        f"Adjusted lift is {lift:.2f}x but the 95% interval [{lo:.2f}, {hi:.2f}] "
        f"spans 1.0, so the data cannot distinguish the subreddit from a "
        f"size-matched draw. Per design doc 3.2 the honest conclusion is "
        f"\"just use a screener\".")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("core")
    ap.add_argument("extra")
    ap.add_argument("out")
    ap.add_argument("--horizon", type=int, default=5)
    a = ap.parse_args()

    core = json.load(open(a.core))
    extra = json.load(open(a.extra)) if os.path.exists(a.extra) else {}
    h = a.horizon
    a2 = core.get(f"A2_{h}y", {})
    label, prose = verdict_for(a2)

    L = []
    w = L.append
    w("# Is r/ValueInvesting a useful idea screener?")
    w("")
    w(f"**Headline verdict ({h}-year horizon): {label}.**")
    w("")
    w(prose)
    w("")
    w("Read this alongside `docs/BIAS_REGISTER.md`. The residual bias points")
    w("toward flattering the subreddit, so a positive result is an upper bound")
    w("and a null result is robust.")
    w("")
    w("## A2 - lift")
    w("")
    meta = a2.get("_meta", {})
    w(f"Treated: {meta.get('n_treated','?')} names with >=4 distinct authors, "
      f"formation 2019-2021. Controls: {meta.get('n_control','?')} names drawn "
      f"from the point-in-time listed universe.")
    w("")
    w("| outcome | treated | control (raw) | control (size-adj) | naive lift | adjusted lift | 95% CI |")
    w("|---|---|---|---|---|---|---|")
    for k in ("winner_3x", "outperformer", "wipeout"):
        v = a2.get(k)
        if not v:
            continue
        ci = v.get("ci") or [None, None]
        cis = (f"[{ci[0]:.2f}, {ci[1]:.2f}]" if ci[0] is not None else "n/a")
        w(f"| `{k}` | {v['p_treated']:.1%} | {v['p_control_raw']:.1%} | "
          f"{(v['p_control_adj'] or 0):.1%} | {v['naive_lift']:.2f} | "
          f"**{v['adjusted_lift']:.2f}** | {cis} |")
    w("")
    if meta:
        w(f"Median forward return: treated {meta['median_return_treated']:+.1%} "
          f"vs control {meta['median_return_control']:+.1%}. "
          f"Survived the full horizon: {meta['survival_treated']:.0%} vs "
          f"{meta['survival_control']:.0%}.")
        w("")
    w("The gap between naive and adjusted lift is the size skew: the subreddit")
    w("talks about big liquid names, and those carry their own returns.")
    w("")

    for key, title, note in (
        (f"A3_{h}y", "A3 - recall, winners and losers",
         "Read the GAP between winner recall and loser recall. If they are "
         "similar the sub has measured nothing but its own breadth (1.2)."),
        (f"A8_{h}y", "A8 - dose-response",
         "A flat curve suggests coincidental coverage rather than signal."),
        (f"A7_{h}y", "A7 - portfolio", "Unadjusted; see the factor alpha below."),
    ):
        d = core.get(key)
        if not d:
            continue
        w(f"## {title}")
        w("")
        w("```")
        w(json.dumps(d, indent=1, default=str))
        w("```")
        w(note)
        w("")

    for key, title in ((f"A4_{h}y", "A4 - timing"),
                       (f"A5_{h}y", "A5 - novelty"),
                       (f"A6_{h}y", "A6 - vs a trivial screen"),
                       (f"A7_{h}y", "A7 - factor-adjusted alpha")):
        d = extra.get(key)
        if not d:
            continue
        w(f"## {title}")
        w("")
        w("```")
        w(json.dumps(d, indent=1, default=str))
        w("```")
        w("")

    w("## What this does not establish")
    w("")
    w("- Stance is not classified, so this is all-mentions, not bullish-only.")
    w("  Design doc 5.3 makes bullish-only the headline and this the robustness")
    w("  check; only the robustness check exists.")
    w("- Submissions only. Comments carry most of the volume and most of the")
    w("  bear cases (10).")
    w("- Sector is not controlled for - no free sector source. Size only.")
    w("- The extraction gate passed on 30 self-labelled documents, not 300")
    w("  independently labelled ones.")
    w("- Non-US listings are structurally invisible, so H3 is unanswered.")
    w("")
    open(a.out, "w").write("\n".join(L) + "\n")
    print(f"wrote {a.out}  ({label})")


if __name__ == "__main__":
    main()
