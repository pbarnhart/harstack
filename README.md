# HARstack

**Audit your stack. Start with the HAR.**

A free, open-source HAR file analyzer for martech engineers, privacy professionals, and compliance teams.

[![License: MIT](https://img.shields.io/badge/License-MIT-red.svg)](LICENSE)

---

## What It Does

The HARstack reads an HTTP Archive (HAR) file from your browser and identifies tracking technologies, PII transmission patterns, consent signal gaps, and regulatory exposure across your live web stack.

It produces:

- **Outcome bucket** -- Escalate, Needs Review, or Likely OK
- **Per-finding analysis** -- plain-language description, applicable regulations, and recommended action
- **Confidence levels** -- Observed, Likely, Heuristic, or Needs Legal Review
- **Owner routing** -- which team should handle each finding
- **GPC verification** -- checks Sec-GPC header in actual request data, not just self-reported state
- **POST body PII scan** -- detects raw and hashed PII transmitted to first-party and third-party endpoints
- **sGTM detection** -- identifies server-side GTM deployments and consent bypass risk
- **Sanitized HAR export** -- PII-stripped for safe sharing with counsel
- **Analysis JSON export** -- structured findings with legal citations for downstream review
- **Audit questions** -- targeted questions derived from what was observed

## Why This Exists

In August 2025, a federal judge ruled that a company's own privacy policy could serve as the predicate tort for a federal wiretapping claim under the ECPA crime-tort exception. The gap between what the policy promised and what the tracking stack actually did was sufficient to state a claim.

Plaintiffs' attorneys build these cases from HAR files. This tool lets you run the same analysis on your own site before they do.

## How to Use It

1. Download `harstack.html` from [Releases](https://github.com/pbarnhart/harstack/releases)
2. Open it in Chrome or Firefox (no install required)
3. Record a HAR file from your site using browser DevTools (Network tab, export HAR)
4. Drop the HAR file into the tool
5. Answer two context questions (consent state, GPC usage)
6. Review findings and export the analysis JSON or sanitized HAR

**Nothing is transmitted. The analysis runs entirely in your browser.**

## Regulatory Coverage

Findings include citations to specific regulations and enforcement actions:

- ECPA (18 U.S.C. § 2511) -- federal wiretapping, crime-tort exception
- CIPA (Cal. Pen. Code § 631(a)) -- California wiretapping
- CCPA/CPRA -- sale, sharing, and GPC compliance
- GLBA Safeguards Rule (16 CFR § 313) -- financial services NPI
- VPPA (18 U.S.C. § 2710) -- video viewing data
- CAN-SPAM Act -- email opt-out compliance
- FTC enforcement precedents (BetterHelp, COPPA)

## Tracker Registry

The tool includes 155+ URL signature entries across:

- Advertising (Meta, Google, TikTok, Reddit, Microsoft, DoubleClick)
- Session Replay (Clarity, Hotjar, FullStory, LogRocket, Mouseflow)
- Analytics (GA4, Mixpanel, Heap, Comscore)
- CDP (RudderStack, Segment)
- Consent Management (Osano, Cookiebot, OneTrust, Cookie-Script)
- Tag Management (GTM, server-side GTM detection)
- Affiliate (Awin, Impact, CJ)
- Call Tracking (Invoca, CallRail)
- Identity Resolution (LiveRamp, Tapad)

## Limitations

This is a first-pass screening instrument. It does not:

- Determine legal compliance
- See server-side data flows (by definition absent from the HAR)
- Replace qualified privacy counsel

Findings flagged as "Needs Legal Review" require attorney review before action.

## Contributing

Pull requests are welcome. If you add a tracker entry, include:

- Specific URL substring or path pattern
- Category and class code
- Risk level
- Applicable regulations
- Plain-language description with legal framing
- Recommended action

Follow the existing TR entry shape documented in the source comments.

## License

MIT -- see [LICENSE](LICENSE)



## Need Help With What You Found?

HARstack surfaces the issues. Remediating them is a different conversation. If you need help interpreting findings, closing policy disclosure gaps, or building a remediation plan, reach out via [Pixel and Policy](https://pixelsandpolicy.substack.com) or [LinkedIn](https://linkedin.com/in/pbarnhart).

---

**Built by Phil Barnhart, CIPP/US**  
Newsletter: [Pixel and Policy](https://pixelsandpolicy.substack.com) -- Martech, Privacy, and Risky Stacks
