#!/usr/bin/env python3
"""
Build both HARstack outputs from a single source file.

Usage (from the build/ directory):
    python build.py

Outputs:
    ../harstack.html       Classic two-pane tool  (universal regulatory fixes)
    ../tool/index.html     Wizard variant          (universal + wizard additions)
"""
from pathlib import Path
import re

BUILD_DIR   = Path(__file__).parent
SRC_PATH    = BUILD_DIR / "source" / "harstack-source.html"
CLASSIC_OUT = (BUILD_DIR / ".." / "harstack.html").resolve()
WIZARD_OUT  = (BUILD_DIR / ".." / "tool" / "index.html").resolve()

SRC = SRC_PATH.read_text(encoding="utf-8")

# ── Structural extraction ────────────────────────────────────────────────────
style_end = SRC.find("</style>")
assert style_end > 0
head_with_style = SRC[:style_end]  # everything up to but not including </style>

script_open  = SRC.find("<script>", style_end)
assert script_open > 0
script_close = SRC.find("</script>", script_open) + len("</script>")
original_script = SRC[script_open:script_close]


# ============================================================
# UNIVERSAL FIXES
# Applied to both classic and wizard outputs.
# Operates on the extracted <script> block text.
# No-ops are safe: fixes that only target wizard-injected content
# (session replay, ID-graph) simply match 0 times for classic input.
# ============================================================
def apply_universal_fixes(text):
    # 1. regs label rewrite
    # 'CCPA/CPRA' -> 'US State Privacy' inside every regs:[...] array.
    # 20 states have active comprehensive privacy laws as of 2026; 12 require
    # GPC honoring. 'CCPA/CPRA' undercounted by 19 states.
    _orig_regs_count = text.count("regs:[") + text.count("regs: [")
    text = re.sub(
        r"(regs: ?\[)([^\]]+)(\])",
        lambda m: m.group(1)
            + m.group(2).replace("'CCPA/CPRA'", "'US State Privacy'")
            + m.group(3),
        text,
    )
    assert text.count("regs:[") + text.count("regs: [") == _orig_regs_count, \
        "regs array count changed during rewrite"
    assert "'US State Privacy'" in text, "regs label rewrite produced no output"

    # 2. regTag CSS class patch
    # Add 'stateprivacy' substring match -> rc2 (green pill) so relabeled
    # pills render correctly. The substring is unique across all our labels.
    _old_rt = ("const cl=rc.includes('ecpa')?'re':rc.includes('ccpa')||"
               "rc.includes('cpra')||rc.includes('cppa')?'rc2':rc.includes('cipa')"
               "?'ri':rc.includes('glba')?'rg':rc.includes('canspam')||"
               "rc.includes('spam')?'rs':'';")
    _new_rt = ("const cl=rc.includes('ecpa')?'re':rc.includes('ccpa')||"
               "rc.includes('cpra')||rc.includes('cppa')||rc.includes('stateprivacy')"
               "?'rc2':rc.includes('cipa')?'ri':rc.includes('glba')?'rg':"
               "rc.includes('canspam')||rc.includes('spam')?'rs':'';")
    assert _old_rt in text, "regTag function not found for patching"
    text = text.replace(_old_rt, _new_rt, 1)

    # 3. GA4 description fix
    # Remove 'legacy' for google-analytics.com (still active), add /mp/collect,
    # correct UA deprecation date to July 1, 2023.
    _old_ga4 = ("Google Analytics 4 collect endpoint on the legacy "
                "google-analytics.com domain. Same exposure analysis as GA4. "
                "The /g/collect path with tid=G- prefix is GA4-specific; the "
                "legacy /collect path with tid=UA- prefix is Universal Analytics.")
    _new_ga4 = ("Google Analytics 4 collection endpoint. GA4 currently uses two "
                "collection domains: google-analytics.com/g/collect and "
                "analytics.google.com/g/collect. Both are active. The /g/collect "
                "path is the GA4 browser-side collection endpoint; the /mp/collect "
                "path on the same domain is the GA4 Measurement Protocol endpoint "
                "for server-side hits (requires an API secret, rarely seen in a "
                "browser HAR). GA4 measurement IDs use the G- prefix. Hits carrying "
                "tid=UA- on the legacy /collect path indicate Universal Analytics, "
                "which Google deprecated on July 1, 2023; UA hits in a current-year "
                "capture warrant a separate remediation note because that data is no "
                "longer being processed.")
    assert _old_ga4 in text, "GA4 description anchor not found"
    text = text.replace(_old_ga4, _new_ga4, 1)

    # 4. Session replay phrase fix
    # No-op for classic (phrase only exists in wizard-injected ADDITIONAL_CMPS).
    # For wizard: replaces the overconfident 'Real-time interception' sentence
    # with accurate 2024-2025 case-law-split framing.
    _old_sr = "Real-time interception of browser interaction triggers ECPA and CIPA analysis."
    _new_sr = (r"Session-replay tools have been the subject of substantial CIPA and "
               r"ECPA litigation in 2024-2025 with mixed appellate outcomes. The Ninth "
               r"Circuit\'s June 2025 Bloomingdale\'s decision lowered the pleading "
               r"threshold for CIPA Section 631(a) claims; the same court\'s Papa "
               r"John\'s decision (also June 2025) reaffirmed the \'party exception\' "
               r"(a website operator using session replay is not itself a third-party "
               r"eavesdropper); and the Northern District of California\'s April 2025 "
               r"Torres v. Prudential decision held session replay does not satisfy the "
               r"real-time interception element. Litigation risk depends on jurisdiction, "
               r"deployment configuration, and whether sensitive fields are masked.")
    text = text.replace(_old_sr, _new_sr)

    # 5. ID-graph claim narrowing
    # No-op for classic (phrase only exists in wizard-injected Magellan AI entry).
    # For wizard: 'most state AGs treat ID-graph sharing as selling regardless of
    # monetary consideration' had no source; replace with narrower accurate version.
    _old_idg = ("(5) verify whether the cross-device matching constitutes selling "
                "under CCPA (most state AGs treat ID-graph sharing as selling "
                "regardless of monetary consideration).")
    _new_idg = (r"(5) evaluate whether the cross-device matching constitutes "
                r"\'selling\' under California\'s CCPA (which defines \'sale\' to "
                r"include disclosure for valuable consideration, a category that "
                r"California courts and the CPPA have interpreted broadly to include "
                r"non-monetary value exchanges) or \'sharing\' / \'targeted "
                r"advertising\' under the comparable terms in other state privacy laws.")
    text = text.replace(_old_idg, _new_idg)

    # 6. BetterHelp citation precision (source file occurrences)
    # Old: 'FTC Docket No. 2023-169' + 'treats hashed identifiers as covered info'
    # New: correct file/docket format, 'Docket C-4796', narrower hashing framing.

    # 6a. Enhanced Conversions tracker description (JS single-quoted string, uses \' escapes)
    _old_ec = (
        r"The FTC\'s BetterHelp consent order (FTC Docket No. 2023-169, final "
        r"July 2023) treats hashed identifiers as covered information for data "
        r"deletion purposes, on the basis that hashing does not conceal the "
        r"consumer\'s identity from a third party that already possesses the "
        r"underlying email or phone value. The California Attorney General has "
        r"applied similar reasoning to CCPA enforcement."
    )
    _new_ec = (
        r"The FTC\'s BetterHelp consent order (FTC File No. 2023-169, In the "
        r"Matter of BetterHelp, Inc., Docket C-4796, final order July 14, 2023) "
        r"established that hashing fails to protect privacy when the receiving "
        r"party can un-hash the data; Google already possesses the underlying "
        r"email and phone values for logged-in users and can match the hashed "
        r"values to identified accounts. Under most US state privacy laws, "
        r"transmission of hashed identifying information to a third-party "
        r"advertising platform constitutes \'sharing,\' \'sale,\' or \'targeted "
        r"advertising\' depending on the jurisdiction\'s terminology."
    )
    assert _old_ec in text, "BetterHelp EC anchor not found"
    text = text.replace(_old_ec, _new_ec, 1)

    # 6b. CDP events finding (JS template literal -- no \' escapes)
    # Applied first; replaces line 2589 (which comes before line 2645).
    _old_cdp = (
        "The FTC's BetterHelp consent order treats hashed identifiers as covered "
        "information for data-deletion purposes on the basis that hashing does not "
        "conceal the consumer's identity from a third party that already possesses "
        "the underlying value."
    )
    _new_cdp = (
        "The FTC's BetterHelp consent order (FTC File No. 2023-169, Docket C-4796, "
        "final order July 14, 2023) established that hashing fails to protect privacy "
        "when the receiving party can un-hash the data."
    )
    assert _old_cdp in text, "BetterHelp CDP anchor not found"
    text = text.replace(_old_cdp, _new_cdp, 1)

    # 6c. Non-CDP PII finding -- unique: 'data deletion' (no hyphen), lowercase 'the'
    _old_pii = (
        "the FTC's BetterHelp consent order treats hashed identifiers as covered "
        "information for data deletion purposes."
    )
    _new_pii = (
        "the FTC's BetterHelp consent order (FTC File No. 2023-169, Docket C-4796, "
        "final order July 14, 2023) established that hashing fails to protect privacy "
        "when the receiving party can un-hash the data."
    )
    assert _old_pii in text, "BetterHelp non-CDP PII anchor not found"
    text = text.replace(_old_pii, _new_pii, 1)

    # 6d. Hashed contact IDs finding -- unique: trailing CA AG + CPRA sentences.
    # Applied after 6b so line 2589's occurrence is already replaced; only
    # line 2645's occurrence (with the trailing sentences) remains.
    _old_hash = (
        "The FTC's BetterHelp consent order treats hashed identifiers as covered "
        "information for data-deletion purposes on the basis that hashing does not "
        "conceal the consumer's identity from a third party that already possesses "
        "the underlying value. The California Attorney General has applied similar "
        'reasoning to CCPA enforcement. Under CPRA these transmissions constitute '
        '"sharing" for cross-context behavioral advertising.'
    )
    _new_hash = (
        "The FTC's BetterHelp consent order (FTC File No. 2023-169, Docket C-4796, "
        "final order July 14, 2023) established that hashing fails to protect privacy "
        "when the receiving party can un-hash the data. Under most US state privacy "
        "laws, transmission of hashed identifying information to a third-party "
        'advertising platform constitutes "sharing," "sale," or "targeted advertising" '
        "depending on the jurisdiction's terminology."
    )
    assert _old_hash in text, "BetterHelp hashed IDs anchor not found"
    text = text.replace(_old_hash, _new_hash, 1)

    # 6e. Domain table UI label (HTML attribute text)
    _old_ui = (
        "the FTC's BetterHelp consent order treats as covered information for "
        "deletion purposes."
    )
    _new_ui = (
        "the FTC's BetterHelp consent order (FTC File No. 2023-169, Docket C-4796) "
        "established that hashing fails to protect privacy when the receiving party "
        "can un-hash the data."
    )
    assert _old_ui in text, "BetterHelp UI label anchor not found"
    text = text.replace(_old_ui, _new_ui, 1)

    # 6f. Formal citation block (JS single-quoted string)
    _old_cite = (
        "citation: 'In the Matter of BetterHelp, Inc., FTC Docket No. 2023-169 "
        "(final order July 2023). $7.8 million settlement and order treating hashed "
        "and encrypted Covered Information within the deletion-and-disclosure scope "
        "of the order, on the rationale that hashing does not conceal identity from "
        "a recipient that already possesses the underlying value.'"
    )
    _new_cite = (
        "citation: 'In the Matter of BetterHelp, Inc., FTC File No. 2023-169, "
        "Docket C-4796 (final order July 14, 2023). $7.8 million settlement and "
        "order establishing that hashing fails to protect privacy when the receiving "
        "party can un-hash the data. The FTC press release stated that hashing will "
        "not protect consumer privacy if third parties can un-hash the data.'"
    )
    assert _old_cite in text, "BetterHelp formal citation anchor not found"
    text = text.replace(_old_cite, _new_cite, 1)

    return text


# ============================================================
# CLASSIC OUTPUT
# ============================================================
classic_script = apply_universal_fixes(original_script)
classic_html   = SRC[:script_open] + classic_script + SRC[script_close:]
CLASSIC_OUT.write_text(classic_html, encoding="utf-8")
print(f"CLASSIC: wrote {len(classic_html):,} chars to {CLASSIC_OUT}")


# ============================================================
# WIZARD-SPECIFIC PREPARATIONS
# ============================================================

ADDITIONAL_CMPS = """  // ── CMPs added by wizard build (enterprise / international platforms) ───────
  'ketchcdn.com':{n:'Ketch',cat:'Consent Management',cc:'c',r:'ok',regs:['CCPA/CPRA','GDPR'],d:'Ketch consent management platform. Enterprise-tier CMP with broad jurisdiction support and TCF v2.2 compliance. The CMP itself is a compliance tool; presence does not validate compliance. Configuration determines whether it actually enforces consent.',a:'(1) Confirm Ketch loads before any tracking script; (2) verify GPC detection is enabled in the Ketch dashboard; (3) audit consent purpose mapping for each tracking category; (4) confirm opt-out propagation to ad and analytics platforms; (5) verify the Ketch jurisdiction configuration matches your visitor mix.'},
  'ketchjs.com':{n:'Ketch (SDK)',cat:'Consent Management',cc:'c',r:'ok',regs:['CCPA/CPRA','GDPR'],d:'Ketch SDK delivery domain. See Ketch findings.',a:'See Ketch findings.'},
  'iubenda.com':{n:'Iubenda',cat:'Consent Management',cc:'c',r:'ok',regs:['CCPA/CPRA','GDPR'],d:'Iubenda consent management platform. Italian CMP widely deployed across European e-commerce. Supports GDPR, CCPA, and TCF v2.2. The CMP itself is a compliance tool; configuration determines actual enforcement.',a:'(1) Confirm Iubenda loads before any tracking script; (2) verify GPC detection is enabled (Iubenda supports US Privacy String + GPC); (3) audit consent purpose mapping; (4) verify opt-out propagation; (5) confirm the privacy policy generated by Iubenda matches the actual tracker inventory in this audit.'},
  'cmp.quantcast.com':{n:'Quantcast Choice (CMP)',cat:'Consent Management',cc:'c',r:'ok',regs:['CCPA/CPRA','GDPR'],d:'Quantcast Choice consent management platform. TCF v2.2 CMP frequently bundled with Quantcast Measure analytics. Note that Quantcast operates both a CMP (compliance tool) and an analytics/audience platform (Quantcast Measure on quantserve.com); the two are separate products with separate data flows. The CMP itself does not validate compliance; configuration determines enforcement.',a:'(1) Confirm Quantcast Choice loads before tracking scripts; (2) verify GPC detection is enabled; (3) audit whether Quantcast Measure (quantserve.com) is also deployed and whether it is consent-gated by Quantcast Choice; (4) verify TCF string signaling matches expected purposes.'},
  'sp-prod.net':{n:'Sourcepoint',cat:'Consent Management',cc:'c',r:'ok',regs:['CCPA/CPRA','GDPR'],d:'Sourcepoint consent management platform. Enterprise CMP used by publishers and large-scale operators. Supports TCF v2.2, GPP, and US state privacy signals. Wrapper architecture (wrapper.sp-prod.net, cmp.sp-prod.net) is characteristic. The CMP itself is a compliance tool; configuration determines enforcement.',a:'(1) Confirm Sourcepoint loads before tracking scripts; (2) verify GPC detection in the Sourcepoint property configuration; (3) audit purpose-to-vendor mapping; (4) verify the GPP signal (Global Privacy Platform) is propagating to downstream platforms.'},
  'sourcepoint.com':{n:'Sourcepoint (CDN)',cat:'Consent Management',cc:'c',r:'ok',regs:['CCPA/CPRA','GDPR'],d:'Sourcepoint CDN. See Sourcepoint findings.',a:'See Sourcepoint findings.'},
  'didomi.io':{n:'Didomi',cat:'Consent Management',cc:'c',r:'ok',regs:['CCPA/CPRA','GDPR'],d:'Didomi consent management platform. French CMP widely deployed across European and global enterprise. Supports TCF v2.2 and US state privacy frameworks. The CMP itself is a compliance tool; configuration determines enforcement.',a:'(1) Confirm Didomi loads before tracking scripts; (2) verify GPC detection is enabled in the Didomi dashboard; (3) audit purpose mapping for each tracker; (4) verify opt-out propagation including the new US state signal layer.'},
  'sdk.privacy-center.org':{n:'Didomi (legacy SDK)',cat:'Consent Management',cc:'c',r:'ok',regs:['CCPA/CPRA','GDPR'],d:'Didomi legacy SDK domain. See Didomi findings.',a:'See Didomi findings.'},
  'usercentrics.eu':{n:'Usercentrics',cat:'Consent Management',cc:'c',r:'ok',regs:['CCPA/CPRA','GDPR'],d:'Usercentrics consent management platform. German CMP. Owns the Cookiebot product as of 2021; Usercentrics CMP (this domain) and Cookiebot (cookiebot.com) are sister products with separate codebases. Supports TCF v2.2, GPP, and US state privacy signals. The CMP itself is a compliance tool; configuration determines enforcement.',a:'(1) Confirm Usercentrics loads before tracking scripts; (2) verify GPC detection is enabled in the Usercentrics dashboard; (3) audit service-by-service consent mapping; (4) verify opt-out propagation to advertising platforms.'},
  // ── Advertising / analytics / session-replay added by wizard build ──────────
  'bzrcdn.openai.com':{n:'OpenAI Ads (SDK)',cat:'Advertising',cc:'a',r:'high',regs:['ECPA','CCPA/CPRA'],d:'OpenAI Ads Measurement Pixel SDK (oaiq.min.js) served from bzrcdn.openai.com. OpenAI Ads launched May 5, 2026 as the conversion-tracking infrastructure for the ChatGPT ad platform. The SDK reads an oppref click identifier from the page URL on init and writes it to a first-party __oppref cookie with a 30-day TTL, plus a __oaiq_domain_probe cookie. On every measure() call the SDK POSTs to bzr.openai.com/v1/sdk/events with the pixel ID, source URL, and event payload. As a third-party advertising platform receiving conversion data and visitor identifiers, OpenAI Ads constitutes \\'sharing\\' under CPRA. Must be suppressed on GPC and CCPA opt-out. The platform supports Google Consent Mode v2 integration: when ad_storage is denied, events queue at the SDK layer and dispatch only when consent is granted.',a:'(1) Verify CMP suppresses both the bzrcdn.openai.com SDK load and bzr.openai.com event endpoint on GPC and CCPA opt-out; (2) confirm gtag Consent Mode v2 integration is wired (ad_storage signal propagates to the OpenAI pixel via the published consent-listener API); (3) disclose OpenAI Ads by name in your privacy policy, including the __oppref cookie and the cross-site advertising data sharing; (4) audit the oppref click identifier handling - it is functionally equivalent to fbclid/gclid and survives most consent-based cookie suppression because it rides in URLs.'},
  'bzr.openai.com':{n:'OpenAI Ads (Events API)',cat:'Advertising',cc:'a',r:'high',regs:['ECPA','CCPA/CPRA'],d:'OpenAI Ads event collection endpoint (POST /v1/sdk/events). Receives conversion and page-action events from the oaiq.min.js SDK on a per-pixel-ID basis. See OpenAI Ads (SDK) findings for the full exposure profile.',a:'See OpenAI Ads (SDK) findings. For server-side deployments, also evaluate the OpenAI Conversions API for the same suppression and disclosure obligations as the browser pixel.'},
  'tags.srv.stackadapt.com':{n:'StackAdapt',cat:'Advertising',cc:'a',r:'high',regs:['ECPA','CCPA/CPRA'],d:'StackAdapt programmatic ad platform conversion pixel (browser endpoint at tags.srv.stackadapt.com/saq_pxl). StackAdapt is a demand-side platform (DSP) for programmatic display, native, video, and CTV advertising. The browser pixel transmits the universal pixel ID, user agent, page URL/title, visitor IP, and a JSON args payload (including revenue and order ID when configured). The server postback endpoint (srv.stackadapt.com/postback/conv) is a parallel server-side path that captures ref_id from the landing page URL and is not visible in a browser HAR. As a third-party advertising platform building retargeting audiences and conversion attribution across sites, StackAdapt constitutes \\'sharing\\' under CPRA and must be suppressed on GPC and CCPA opt-out.',a:'(1) Verify CMP suppresses the browser pixel on GPC and CCPA opt-out; (2) audit the server-side postback path separately - it fires from your backend and is not visible in this HAR; (3) disclose StackAdapt by name in your privacy policy as a third-party advertising platform; (4) confirm DPA terms with StackAdapt cover the visitor IP, URL, and pixel ID as personal information under CCPA; (5) audit the args payload for any custom fields that may contain PII.'},
  'srv.stackadapt.com':{n:'StackAdapt (Postback)',cat:'Advertising',cc:'a',r:'high',regs:['ECPA','CCPA/CPRA'],d:'StackAdapt server-side conversion postback endpoint. See StackAdapt findings.',a:'See StackAdapt findings.'},
  'inspectlet.com':{n:'Inspectlet',cat:'Session Replay',cc:'s',r:'high',regs:['ECPA','CIPA','CCPA/CPRA'],d:'Inspectlet session replay and heatmap platform. Records visitor mouse movements, clicks, scrolls, and full DOM playback of the session. Same wiretapping exposure category as Microsoft Clarity, Hotjar, and FullStory. Real-time interception of browser interaction triggers ECPA and CIPA analysis. The cdn.inspectlet.com domain serves the SDK loader; hn.inspectlet.com is the data ingestion endpoint where session payloads stream. Default input field masking exists but has documented gaps; sensitive form pages (login, checkout, account settings) require explicit per-field masking configuration to prevent credential and PII capture.',a:'(1) Implement Inspectlet input masking on all sensitive form fields and credential entry pages; (2) confirm two-party consent disclosure for visitors in California and other two-party-consent states before any recording begins; (3) audit Inspectlet DPA terms and verify the controller-vs-processor designation; (4) disclose Inspectlet by name in your privacy policy as session-replay infrastructure; (5) verify CMP gating - Inspectlet must not load before consent for behavioral-analytics processing; (6) for financial or healthcare pages, evaluate whether Inspectlet on those pages creates GLBA or HIPAA exposure beyond the baseline CIPA concern.'},
  'matomo.php':{n:'Matomo (self-hosted analytics)',cat:'Analytics',cc:'an',r:'medium',regs:['ECPA','CCPA/CPRA'],d:'Matomo analytics platform detected via the /matomo.php tracking endpoint. Matomo is open-source analytics typically self-hosted on a customer-owned subdomain, which makes it appear as first-party from the browser perspective but functions as a tracker under privacy law analysis. Self-hosting changes the data-flow boundary (the data stays under the deploying organization\\'s control rather than reaching a vendor) but does not change the tracking nature of the deployment. Whether Matomo constitutes sharing under CPRA depends on configuration: a strictly first-party Matomo deployment with no third-party forwarding is generally not sharing; a Matomo deployment that forwards data to advertising integrations or to a Matomo Cloud instance is sharing. The /matomo.php request transmits page URL, page title, visitor identifier (_id cookie), screen resolution, user agent, and any custom dimensions configured.',a:'(1) Determine the Matomo deployment model: strictly first-party self-hosted, Matomo Cloud, or a hybrid; (2) audit Matomo plugin configuration - the HeatmapSessionRecording plugin specifically converts Matomo into a session-replay tool with CIPA exposure; (3) confirm CMP gating - Matomo offers a consent integration that must be wired before tracker fires; (4) verify Matomo cookie scope and retention; (5) if Matomo is shown as first-party to bypass CMP-based blocking of third-party analytics, this is a sharing-by-configuration pattern that requires explicit disclosure.'},
  'HeatmapSessionRecording':{n:'Matomo Heatmap & Session Recording',cat:'Session Replay',cc:'s',r:'high',regs:['ECPA','CIPA','CCPA/CPRA'],d:'Matomo Heatmap and Session Recording plugin detected (path /plugins/HeatmapSessionRecording/). This converts a Matomo analytics deployment into a session-replay tool with the same wiretapping exposure category as Hotjar, FullStory, and Microsoft Clarity. Real-time recording of visitor interaction (clicks, scrolls, mouse movement, form field interaction depending on configuration) triggers ECPA and CIPA analysis regardless of whether the Matomo backend is self-hosted. Self-hosting changes where the recording is stored but not whether the recording happened.',a:'(1) Confirm whether session recording is intentionally enabled or was inherited from a default plugin configuration; (2) implement two-party consent disclosure for recorded sessions where any party may be in a two-party-consent state; (3) audit input field masking configuration; (4) disclose session recording by name in your privacy policy; (5) for financial or healthcare contexts, evaluate the deployment under the relevant overlay (GLBA or HIPAA); (6) verify CMP gating - this plugin must not record before consent for behavioral-analytics processing.'},
  'matomo.js':{n:'Matomo (SDK)',cat:'Analytics',cc:'an',r:'low',regs:['ECPA','CCPA/CPRA'],d:'Matomo SDK JavaScript file. See Matomo findings.',a:'See Matomo findings.'},
  'mgln.ai':{n:'Magellan AI',cat:'Advertising',cc:'a',r:'high',regs:['ECPA','CCPA/CPRA'],d:'Magellan AI (mgln.ai) podcast advertising attribution and cross-device identity platform. The cdn.mgln.ai/pixel.min.js loader instruments the host site for podcast-ad attribution: the pixel correlates a website visit with a prior podcast ad exposure by matching browser identifiers against podcast listener data. The mgln.ai/init and mgln.ai/view endpoints handle event capture. The flow typically includes an ID sync with Tapad (Experian device graph) at pixel.tapad.com/idsync/ex/receive, which extends visitor identification across devices using cross-context behavioral advertising infrastructure. As a third-party advertising attribution platform with cross-device identity resolution, Magellan AI constitutes sharing under CPRA. Must be suppressed on GPC and CCPA opt-out.',a:'(1) Verify CMP suppresses the Magellan AI pixel and the Tapad ID sync on GPC and CCPA opt-out; (2) disclose Magellan AI by name in your privacy policy as podcast advertising attribution infrastructure; (3) disclose the Tapad device graph integration as a separate sharing relationship under CPRA; (4) audit DPA terms with both Magellan AI and Tapad/Experian; (5) verify whether the cross-device matching constitutes selling under CCPA (most state AGs treat ID-graph sharing as selling regardless of monetary consideration).'},
  'cdn.mgln.ai':{n:'Magellan AI (CDN)',cat:'Advertising',cc:'a',r:'high',regs:['ECPA','CCPA/CPRA'],d:'Magellan AI CDN serving pixel.min.js. See Magellan AI findings.',a:'See Magellan AI findings.'},
  'humanz.com':{n:'Humanz (Influencer Marketing)',cat:'Marketing',cc:'a',r:'medium',regs:['ECPA','CCPA/CPRA'],d:'Humanz influencer marketing platform. The humanz-gtm.js loader on assets.humanz.com instruments the host site for influencer-campaign attribution: which influencer\\'s shared link or content drove a visitor to the merchant, what the visitor did on the merchant site, and whether they converted. Functions as a third-party advertising attribution tracker for influencer-driven traffic. As an external marketing platform receiving visitor behavioral data, Humanz constitutes sharing under CPRA when the data joins to the merchant\\'s customer profile or to Humanz\\'s influencer audience graph.',a:'(1) Confirm CMP suppresses the Humanz script on GPC and CCPA opt-out; (2) audit what events Humanz captures and what fields are transmitted; (3) disclose Humanz by name in your privacy policy as an advertising attribution platform; (4) verify DPA terms cover the controller-vs-processor designation.'},
  'spotapps.co':{n:'SpotApps (Restaurant Marketing)',cat:'Marketing',cc:'a',r:'medium',regs:['ECPA','CCPA/CPRA'],d:'SpotApps (Spot Hospitality) restaurant marketing and ordering platform. Provides online ordering, loyalty programs, customer data management, and marketing automation specifically for restaurants and food service. Visitor identifiers and order data flow to SpotApps infrastructure. For deployments handling customer order history, payment context, or loyalty enrollment, SpotApps is a sharing relationship under CPRA. Note that 404s on static.spotapps.co/web/<merchant>/ indicate abandoned or misconfigured deployments where the integration is still attempting to load but the merchant configuration no longer resolves - this is a privacy policy accuracy concern (the policy probably still names SpotApps) and a supply-chain risk (the path becomes available for hijack if the merchant configuration is reinstated by an attacker).',a:'(1) Confirm the SpotApps integration is intended and current; if not, remove the script reference; (2) verify CMP gating on the SpotApps loader; (3) audit what customer data flows to SpotApps and confirm DPA coverage; (4) disclose SpotApps by name in your privacy policy as restaurant marketing infrastructure; (5) for 404 responses, treat as abandoned-tag remediation per the audit\\'s failed-request finding.'},
  't.co/i/adsct':{n:'X (Twitter) Ads (Conversion)',cat:'Advertising',cc:'a',r:'high',regs:['ECPA','CCPA/CPRA'],d:'X (Twitter) Ads conversion pixel on the t.co/i/adsct path. Sister endpoint to the static.ads-twitter.com pixel loader. The t.co/i/adsct request transmits browser fingerprinting data (device, language, timezone, screen resolution, plugin enumeration) plus an event identifier to X/Twitter\\'s ad infrastructure for conversion attribution and audience building. Constitutes sharing under CPRA. Must be suppressed on GPC and CCPA opt-out.',a:'(1) Verify CMP suppresses both static.ads-twitter.com SDK loads and t.co/i/adsct conversion calls on GPC and opt-out; (2) disclose X/Twitter Ads by name in your privacy policy; (3) confirm DPA terms cover the controller-vs-processor designation for visitor identifiers transmitted; (4) audit the bci= fingerprint payload for any custom fields.'},
"""
wizard_script = original_script.replace(
    "  'osano.com':{n:'Osano',cat:'Consent Management'",
    ADDITIONAL_CMPS + "  'osano.com':{n:'Osano',cat:'Consent Management'",
    1
)
assert "'ketchcdn.com'" in wizard_script, "CMP injection failed"
assert "'bzrcdn.openai.com'" in wizard_script, "OpenAI injection failed"
assert "'inspectlet.com'" in wizard_script, "Inspectlet injection failed"

# Apply universal fixes AFTER CMP injection so the session-replay phrase fix
# also catches wizard-injected Inspectlet and Matomo Heatmap entries.
wizard_script = apply_universal_fixes(wizard_script)

# Rename to original_script: Magellan dedup block and BODY f-string both
# use the variable name original_script.
original_script = wizard_script

_mgln_source_block_old = """  // Podcast and audio attribution
  'mgln.ai':{n:'Magellan AI',cat:'Advertising',cc:'a',r:'medium',regs:['US State Privacy','ECPA'],d:'Magellan AI podcast and audio advertising attribution platform. Tracks website visitors back to podcast and streaming-audio ad impressions to attribute conversions to specific audio campaigns. Constitutes cross-context behavioral advertising under CPRA: the attribution data ties web behavior to audio listening behavior collected through a separate channel.',a:'(1) Disclose Magellan AI by name in your privacy policy including the audio-to-web cross-context attribution; (2) confirm DPA terms and controller-vs-processor designation; (3) verify CMP suppression on CCPA opt-out and GPC.'},
  'cdn.mgln.ai':{n:'Magellan AI (CDN)',cat:'Advertising',cc:'a',r:'medium',regs:['US State Privacy'],d:'Magellan AI script CDN.',a:'See Magellan AI findings.'},
"""
# Note: regs was already rewritten to 'US State Privacy' by the earlier
# regex pass, so we have to use the rewritten form here as the anchor.
assert _mgln_source_block_old in original_script, "source Magellan block anchor not found"
original_script = original_script.replace(_mgln_source_block_old, "  // Podcast and audio attribution (wizard build: see top of map for detailed entries)\n", 1)
# Sanity: should still have the wizard-injected versions only
assert original_script.count("'mgln.ai'") == 1, "wizard-injected mgln.ai entry missing after dedup"
assert original_script.count("'cdn.mgln.ai'") == 1, "wizard-injected cdn.mgln.ai entry missing after dedup"

# Extract the HAR explainer modal markup
har_modal_start = SRC.find('<!-- HAR EXPLAINER MODAL -->')
har_modal_end = SRC.find("<script>", har_modal_start)
har_modal = SRC[har_modal_start:har_modal_end].strip()

# Extract the export modal
exp_modal_start = SRC.find('<!-- EXPORT MODAL -->')
exp_modal_end = SRC.find('<!-- HAR EXPLAINER MODAL -->')
exp_modal = SRC[exp_modal_start:exp_modal_end].strip()

# Extract the right panel / report container (we'll reuse it in summary step)
rp_start = SRC.find('<div class="rp" id="rp">')
rp_end = SRC.find('</div>', SRC.find('<div class="rc"', rp_start)) + len('</div>')
# That ends rc. We need the closing </div> of rp too.
rp_end = SRC.find('</div>', rp_end + 1) + len('</div>')
report_panel = SRC[rp_start:rp_end]

# Extract step content bodies so we can drop them into wizard cards
# We'll grab innerHTML of each .step container by id markers in the source
def slice_step(label_text):
    """Find <!-- STEP X --> block, return everything until next <div class="sdiv"> or end."""
    marker = f'<!-- STEP {label_text} -->'
    if marker not in SRC:
        marker = f'<!-- STEP {label_text}: '
        idx = SRC.find(marker)
    else:
        idx = SRC.find(marker)
    assert idx > 0, f'missing marker for step {label_text}'
    # find <div class="step"
    step_start = SRC.find('<div class="step"', idx)
    # find matching closing </div> of that step.
    # We rely on the structure: <div class="step"> ... </div><div class="sdiv">
    # or for STEP 3 (last), <div class="step"> ... </div>\n    </div>  (closing .steps)
    sdiv = SRC.find('<div class="sdiv">', step_start)
    if sdiv > 0 and sdiv - step_start < 6000:
        # find the </div> just before sdiv
        end = SRC.rfind('</div>', step_start, sdiv) + len('</div>')
    else:
        # Last step. Walk forward, counting div depth, until depth hits 0.
        depth = 0
        i = step_start
        while i < len(SRC):
            o = SRC.find('<div', i)
            c = SRC.find('</div>', i)
            if c == -1:
                break
            if o != -1 and o < c:
                depth += 1
                i = o + 4
            else:
                depth -= 1
                i = c + len('</div>')
                if depth == 0:
                    end = i
                    break
        else:
            raise RuntimeError(f'could not find end of step {label_text}')
    return SRC[step_start:end]


step0 = slice_step('0')
step1 = slice_step('1')
step2 = slice_step('2')
step2b = slice_step('2b')
step3 = slice_step('3')

# Inject the "Which browser?" CTA into Step 0, just after the .brave-note block
BROWSER_CTA = '''<div class="wiz-browser-cta">
              <span class="wiz-browser-icon">🧭</span>
              <div class="wiz-browser-cta-text">Not sure which browser to use for capture? Each browser produces a different audit signal.</div>
              <button type="button" class="wiz-browser-cta-btn" onclick="openBrowserModal()" aria-label="Open browser comparison">Compare browsers →</button>
            </div>'''
import re
m = re.search(r'<div class="brave-note">.*?</div>', step0, re.DOTALL)
if m:
    step0 = step0[:m.end()] + '\n          ' + BROWSER_CTA + step0[m.end():]
else:
    raise RuntimeError('could not locate brave-note marker in step 0 for CTA injection')

# Inject the "What's a HAR file?" CTA into Step 1, at the very top of .sbody
HAR_CTA = '''<div class="wiz-browser-cta" style="margin-top:0;margin-bottom:14px;">
              <span class="wiz-browser-icon">📄</span>
              <div class="wiz-browser-cta-text">New to HAR files? Here's what they are and why HARstack needs one.</div>
              <button type="button" class="wiz-browser-cta-btn" onclick="openModal()" aria-label="What is a HAR file">What's a HAR file? →</button>
            </div>'''
# Insert just after the opening of the step's <div class="sbody">
m = re.search(r'<div class="sbody">', step1)
if m:
    step1 = step1[:m.end()] + '\n          ' + HAR_CTA + step1[m.end():]
else:
    raise RuntimeError('could not locate sbody marker in step 1 for HAR CTA injection')

# Inject the LOCAL-PROCESSING BANNER right above the HAR CTA so it's the very
# first thing readers see when they land on Step 1.
LOCAL_BANNER = '''<div class="wiz-local-banner" role="note" aria-labelledby="local-banner-title">
              <span class="wiz-local-banner-icon" aria-hidden="true">🔒</span>
              <div class="wiz-local-banner-text">
                <div class="wiz-local-banner-title" id="local-banner-title">Your HAR file never leaves this browser</div>
                <div class="wiz-local-banner-body">
                  Everything HARstack does happens inside this tab. <strong>No file upload. No server. No telemetry. No tracking.</strong> You can verify this by opening DevTools and watching the Network panel while you use the tool: no outbound requests are made with your data. <button type="button" class="linklike" onclick="openModal()">Read the full safety disclosure →</button>
                </div>
              </div>
            </div>'''
m = re.search(r'<div class="wiz-browser-cta" style="margin-top:0;margin-bottom:14px;">', step1)
if m:
    step1 = step1[:m.start()] + LOCAL_BANNER + '\n          ' + step1[m.start():]
else:
    raise RuntimeError('could not locate HAR CTA marker for local-banner injection')

# Inject the FORM-POST CAPTURE TIP just before the "Open your .har file" drop zone.
FORMPOST_TIP = '''<div class="wiz-formpost-tip" role="note">
              <span class="wiz-formpost-icon" aria-hidden="true">📝</span>
              <div class="wiz-formpost-text">
                <div class="wiz-formpost-title">Tip · capture a form submit, not just the homepage</div>
                <div class="wiz-formpost-body">
                  The most revealing data flows happen at the moment a visitor submits a form. That is where Meta CAPI fires hashed email, where session replay captures field values, where the CPPA Advisory 2024-01 fact pattern shows up. A homepage capture shows the visit-time surface. A form-submit capture shows the conversion-time exposure. <strong>To capture a submit: keep DevTools recording, fill the form, submit, then export the HAR after the submit completes.</strong>
                  <a href="https://harstack.com/captures/" target="_blank" rel="noopener" class="wiz-formpost-link">Read more about capture types →</a>
                </div>
              </div>
            </div>'''
# Find the drop zone container (id="drop" or class containing "drop")
m = re.search(r'<div[^>]*id="drop"', step1)
if m:
    step1 = step1[:m.start()] + FORMPOST_TIP + '\n          ' + step1[m.start():]
else:
    # fallback: insert before .drop class element
    m = re.search(r'<div class="drop[\s"]', step1)
    if m:
        step1 = step1[:m.start()] + FORMPOST_TIP + '\n          ' + step1[m.start():]
    else:
        raise RuntimeError('could not locate drop zone marker for form-post tip injection')

# Inject the CLEAR-FILE button into the #fok indicator block so users can swap
# a HAR without restarting the wizard.
# The source structure is roughly:
#   <div id="fok" style="display:none;..."><span id="fn"></span> loaded</div>
# We'll add the clear button inside #fok.
m = re.search(r'(<div[^>]+id="fok"[^>]*>)([^<]*<[^>]*id="fn"[^>]*>[^<]*</[^>]+>[^<]*)(</div>)', step1)
if m:
    clear_btn = '<button type="button" class="wiz-clear-file" onclick="wizClearFile()" aria-label="Clear loaded HAR file">✕ Clear file</button>'
    step1 = step1[:m.end(2)] + clear_btn + step1[m.end(2):]
else:
    # The #fok block may have different inner shape; just inject the button at
    # the end of its content via a more permissive regex.
    m = re.search(r'(<div[^>]+id="fok"[^>]*>)(.*?)(</div>)', step1, re.DOTALL)
    if m:
        clear_btn = '<button type="button" class="wiz-clear-file" onclick="wizClearFile()" aria-label="Clear loaded HAR file">✕ Clear file</button>'
        step1 = step1[:m.start(3)] + clear_btn + step1[m.start(3):]
    else:
        print('NOTE: could not locate #fok block; Clear-file button skipped')

# Sanity check
for name, s in [('0',step0),('1',step1),('2',step2),('2b',step2b),('3',step3)]:
    print(f'STEP {name}: {len(s)} chars')




# ---------------- WIZARD CSS ----------------
WIZARD_CSS = """

/* ============ WIZARD LAYOUT (alternate version) ============ */
body.wiz { background: var(--paper-mid); }
.wiz-shell {
  max-width: 880px;
  margin: 0 auto;
  padding: 36px 32px 80px;
  transition: max-width 0.25s ease;
}
/* When the report panel is showing, widen the shell so domain tables
   have room and category pills don't crowd. Triggered by JS adding
   .wiz-shell-wide to the shell when wizCurrent === 5. */
.wiz-shell.wiz-shell-wide {
  max-width: 1280px;
}

/* HERO STRIP at top of every wizard page */
.wiz-hero {
  text-align: center;
  margin-bottom: 28px;
  padding: 0 8px;
}
.wiz-hero h1 {
  font-family: var(--display);
  font-size: 30px;
  line-height: 1.15;
  font-style: italic;
  color: var(--ink);
  margin-bottom: 10px;
}
.wiz-hero h1 em {
  font-style: normal;
  color: var(--accent);
}
.wiz-hero p {
  font-size: 14px;
  line-height: 1.65;
  color: #5a6b7a;
  max-width: 640px;
  margin: 0 auto;
}

/* PROGRESS RAIL */
.wiz-rail {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0;
  margin-bottom: 36px;
  padding: 0 4px;
  flex-wrap: wrap;
  row-gap: 8px;
}
.wiz-rail-step {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  background: none;
  border: none;
  padding: 4px 2px;
  font: inherit;
  color: inherit;
}
.wiz-rail-step[disabled] { cursor: not-allowed; opacity: 0.45; }
.wiz-rail-step:focus-visible { outline: 2px solid var(--header); outline-offset: 2px; border-radius: 3px; }
.wiz-rail-dot {
  width: 26px;
  height: 26px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: var(--mono);
  font-size: 11px;
  font-weight: 600;
  border: 1.5px solid var(--rule);
  background: white;
  color: #999;
  transition: all 0.2s;
  flex-shrink: 0;
}
.wiz-rail-step.done .wiz-rail-dot {
  background: var(--ok);
  border-color: var(--ok);
  color: white;
}
.wiz-rail-step.active .wiz-rail-dot {
  background: var(--header);
  border-color: var(--header);
  color: white;
  box-shadow: 0 0 0 4px rgba(58,127,191,0.15);
}
.wiz-rail-step.done .wiz-rail-dot::after { content: "✓"; font-size: 13px; }
.wiz-rail-step.done .wiz-rail-dot { font-size: 0; }
.wiz-rail-step.done .wiz-rail-dot::after { font-size: 13px; }
.wiz-rail-label {
  font-family: var(--mono);
  font-size: 10px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: #999;
  transition: color 0.2s;
}
.wiz-rail-step.active .wiz-rail-label { color: var(--header); }
.wiz-rail-step.done .wiz-rail-label { color: var(--ok); }
.wiz-rail-line {
  width: 32px;
  height: 1.5px;
  background: var(--rule);
  margin: 0 6px;
  transition: background 0.2s;
}
.wiz-rail-line.done { background: var(--ok); }

@media (max-width: 720px) {
  .wiz-rail-label { display: none; }
  .wiz-rail-line { width: 18px; margin: 0 3px; }
}

/* CARD */
.wiz-card {
  background: white;
  border: 1px solid var(--rule);
  border-radius: 6px;
  box-shadow: 0 4px 20px rgba(26,32,48,0.06), 0 1px 3px rgba(26,32,48,0.04);
  overflow: hidden;
  animation: wizIn 0.28s ease;
}
@keyframes wizIn {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}
.wiz-card-hdr {
  background: var(--header);
  color: white;
  padding: 18px 28px;
  display: flex;
  align-items: center;
  gap: 14px;
  border-bottom: 2px solid var(--header-dark);
}
.wiz-card-num {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: rgba(255,255,255,0.18);
  border: 1.5px solid rgba(255,255,255,0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: var(--mono);
  font-size: 13px;
  font-weight: 600;
  flex-shrink: 0;
}
.wiz-card-titles { flex: 1; min-width: 0; }
.wiz-card-eyebrow {
  font-family: var(--mono);
  font-size: 10px;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: rgba(255,220,180,0.9);
  margin-bottom: 2px;
}
.wiz-card-title {
  font-family: var(--display);
  font-size: 19px;
  line-height: 1.25;
  font-style: italic;
}
.wiz-card-body {
  padding: 28px 32px;
  font-size: 13px;
  color: #333;
  line-height: 1.6;
}

/* Re-tune the original .step content to feel right inside a centered card */
.wiz-card-body .stitle { padding: 0; font-size: 0; margin-bottom: 14px; }
.wiz-card-body .stitle::before {
  content: attr(data-title);
  font-size: 14px;
  font-weight: 600;
  color: var(--ink);
  display: block;
  padding-bottom: 4px;
}
.wiz-card-body .sbody { padding: 0; }
.wiz-card-body .step-hdr { display: none; } /* original number is now in card header */
.wiz-card-body .stitle { display: none; }    /* original title now in card header */

/* Make drop zone, instr blocks more spacious in wizard */
.wiz-card-body .drop { padding: 28px; font-size: 14px; }
.wiz-card-body .drop-icon { font-size: 32px; }
.wiz-card-body .drop-lbl { font-size: 13px; }
.wiz-card-body .instr { font-size: 13px; padding: 14px 16px; }
.wiz-card-body .warn-box { padding: 14px 16px; }
.wiz-card-body .warn-box p { font-size: 12.5px; }
.wiz-card-body .bg { gap: 10px; margin-bottom: 12px; }
.wiz-card-body .bc { padding: 12px 14px; font-size: 12.5px; }
.wiz-card-body .ck li { font-size: 13px; padding: 7px 0; }
.wiz-card-body .gpc-btn { padding: 14px 16px; font-size: 11px; }
.wiz-card-body .biz-btn { padding: 10px 18px; font-size: 11px; }
.wiz-card-body .run-btn { padding: 14px; font-size: 12px; }
.wiz-card-body .caveat { font-size: 11.5px; padding: 10px 12px; }

/* NAV BAR (back / next) */
.wiz-nav {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  padding: 16px 28px;
  border-top: 1px solid var(--rule-light);
  background: var(--paper-mid);
}
.wiz-btn {
  font-family: var(--mono);
  font-size: 11px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  padding: 11px 22px;
  border-radius: 3px;
  cursor: pointer;
  transition: all 0.15s;
  font-weight: 500;
  border: 1.5px solid;
  background: white;
}
.wiz-btn-back {
  border-color: var(--rule);
  color: #666;
}
.wiz-btn-back:hover {
  border-color: var(--ink);
  color: var(--ink);
}
.wiz-btn-next {
  background: var(--accent);
  color: white;
  border-color: var(--accent);
}
.wiz-btn-next:hover {
  background: var(--accent-dark);
  border-color: var(--accent-dark);
}
.wiz-btn-next:disabled {
  background: #cbd2d9;
  border-color: #cbd2d9;
  color: #f0f4f8;
  cursor: not-allowed;
}
.wiz-btn-skip {
  background: none;
  border-color: transparent;
  color: #888;
  text-decoration: underline;
  text-underline-offset: 3px;
}
.wiz-btn-skip:hover { color: var(--ink); }

.wiz-nav-spacer { flex: 1; }
.wiz-step-counter {
  font-family: var(--mono);
  font-size: 10px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: #999;
}

/* PANEL VIS */
.wiz-panel { display: none; }
.wiz-panel.active { display: block; }

/* SUMMARY PAGE: full-width report container */
.wiz-summary-wrap {
  background: white;
  border: 1px solid var(--rule);
  border-radius: 6px;
  box-shadow: 0 4px 20px rgba(26,32,48,0.06);
  overflow: hidden;
}
/* Override .rp width inside summary so report uses full container */
.wiz-summary-wrap .rp {
  overflow: visible;
  background: white;
  min-height: 200px;
  height: auto;
  position: static;
}
.wiz-summary-wrap .empty { display: none; }
.wiz-summary-wrap .loading { padding: 80px 40px; }
.wiz-summary-actions {
  padding: 20px 28px;
  border-top: 1px solid var(--rule-light);
  background: var(--paper-mid);
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  align-items: center;
}
.wiz-summary-actions .wiz-nav-spacer { flex: 1; }

/* small inline link */
.wiz-back-inline {
  font-family: var(--mono);
  font-size: 11px;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: #888;
  background: none;
  border: none;
  cursor: pointer;
  padding: 6px 0;
  margin-bottom: 14px;
}
.wiz-back-inline:hover { color: var(--header); }

/* Footer */
.wiz-foot {
  text-align: center;
  margin-top: 32px;
  font-family: var(--mono);
  font-size: 10px;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: #aaa;
}
.wiz-foot a { color: #888; text-decoration: none; border-bottom: 1px dotted #ccc; }
.wiz-foot a:hover { color: var(--header); }
.wiz-foot-sep { color: #ccc; margin: 0 10px; }

/* ============================================================
   ACCESSIBILITY OVERRIDES (wizard alternate version)
   All overrides scoped to .wiz-summary-wrap so the classic
   two-pane view is unaffected. Every rule below is targeted
   at fixing a measured WCAG AA contrast failure.
   ============================================================ */

/* Darken report header band from --header (#3a7fbf, white text 4.2:1)
   to --header-dark (#2d6496, white text 6.2:1). This single change
   converts most rh-meta and rh-actions content to AA-compliant. */
.wiz-summary-wrap .rh {
  background: var(--header-dark) !important;
  border-bottom-color: #1f5278 !important;
}

/* Report header band — original had blue text on blue bg failing 1.3:1 to 3.1:1.
   Force solid white text on the header bg for all interior elements. */
.wiz-summary-wrap .rh-meta {
  color: #ffffff !important;            /* 6.2:1 on header-dark — PASS AA */
}
.wiz-summary-wrap .rh-meta span { color: #ffffff !important; }
.wiz-summary-wrap .gauge-label,
.wiz-summary-wrap .gauge-sub {
  color: #ffffff !important;
}

/* GPC status pill in header band — switch to filled chips with white text. */
.wiz-summary-wrap .rh-meta span[style*="border:1px solid"] {
  border: none !important;
  padding: 3px 9px !important;
  font-weight: 600 !important;
  color: #ffffff !important;
}
.wiz-summary-wrap .rh-meta span[style*="#2a7a3a"] { background: #1f5e2c !important; }   /* GPC verified — 7.8:1 on white text */
.wiz-summary-wrap .rh-meta span[style*="#b8770a"] { background: #8a5500 !important; }   /* GPC reported, not verified — 6.2:1 */
.wiz-summary-wrap .rh-meta span[style*="#666"]   { background: #2a3744 !important; }    /* GPC not active / unknown — 12.1:1 */

/* Screening result "Escalate" / "Investigate" / "Pass" text.
   At 24px italic this is "large" under WCAG (3:1 threshold).
   Tinted whites pass AA Large on --header-dark; bold weight also helps. */
.wiz-summary-wrap .gauge-val {
  font-weight: 600 !important;
  color: #ffffff !important;
  text-shadow: 0 1px 2px rgba(0,0,0,0.20);
}
.wiz-summary-wrap .gauge-val.gh { color: #ffd9d4 !important; }  /* 4.7:1 on header-dark — AA normal PASS */
.wiz-summary-wrap .gauge-val.gm { color: #ffe7c2 !important; }  /* 5.0:1 */
.wiz-summary-wrap .gauge-val.gl { color: #c8f0d8 !important; }  /* 4.9:1 */

/* Export buttons in the report header — solid filled treatment for AA contrast. */
.wiz-summary-wrap .export-btn {
  border-color: rgba(255,255,255,0.6) !important;
  font-weight: 600 !important;
}
.wiz-summary-wrap .export-btn:focus-visible {
  outline: 2px solid #ffd9d4 !important;
  outline-offset: 2px !important;
}
.wiz-summary-wrap .export-btn-har {
  background: rgba(0,0,0,0.32) !important;
  color: #ffffff !important;
}
.wiz-summary-wrap .export-btn-har:hover {
  background: rgba(0,0,0,0.5) !important;
  border-color: #ffffff !important;
}
.wiz-summary-wrap .export-btn-json {
  background: #1a4a2a !important;
  color: #ffffff !important;                /* 10.2:1 — clean PASS */
  border-color: #2a7a4f !important;
}
.wiz-summary-wrap .export-btn-json:hover {
  background: #225e35 !important;
  border-color: #6dc !important;
}
/* New CSV button — same family for visual consistency */
.wiz-summary-wrap .export-btn-csv {
  background: #3a2a5e !important;
  color: #ffffff !important;                /* 12.6:1 — clean PASS */
  border-color: #6b5aa0 !important;
}
.wiz-summary-wrap .export-btn-csv:hover {
  background: #4a3870 !important;
  border-color: #9c8cd0 !important;
}

/* Category and party pills in tables — original passes AA but the
   small font + low-weight visual makes them feel washed at typical
   viewing distance. Bump size, weight, and saturation.
   Also: never wrap — pill labels are short and should stay on one line. */
.wiz-summary-wrap .ctag {
  font-size: 10px !important;
  font-weight: 600 !important;
  padding: 3px 8px !important;
  border: 1px solid currentColor !important;
  white-space: nowrap !important;
  display: inline-block !important;
}
.wiz-summary-wrap .ca  { background: #fbd5d5 !important; color: #6b1111 !important; }   /* Advertising  → 9.1:1 */
.wiz-summary-wrap .cs  { background: #fbd9b3 !important; color: #5e2e00 !important; }   /* Session Replay → 8.4:1 */
.wiz-summary-wrap .can { background: #d5e3f7 !important; color: #102660 !important; }   /* Analytics    → 11.0:1 */
.wiz-summary-wrap .cc  { background: #cdf2cd !important; color: #0e4e0e !important; }   /* Consent Mgmt → 8.1:1 */
.wiz-summary-wrap .cd  { background: #e1d2f7 !important; color: #2f0e6b !important; }   /* CDP          → 10.6:1 */
.wiz-summary-wrap .ce  { background: #f7d2eb !important; color: #6b0e5e !important; }   /* Affiliate     → 8.3:1 */
.wiz-summary-wrap .ct  { background: #e8e4d8 !important; color: #2a2a2a !important; }   /* Other/Hosting → 11.3:1 */

/* Party pills (1P / 3P-Identified / 3P-Unidentified / Operator-related) — same family treatment + nowrap */
.wiz-summary-wrap td span[style*="background:#eef3eb"],
.wiz-summary-wrap td span[style*="background:#eff3f8"],
.wiz-summary-wrap td span[style*="background:#fff4e6"],
.wiz-summary-wrap td span[style*="background:#fbeaea"] {
  font-size: 10px !important;
  font-weight: 600 !important;
  letter-spacing: 0.06em !important;
  padding: 3px 8px !important;
  white-space: nowrap !important;
  display: inline-block !important;
}

/* Status pills (HTTP code) in domain table */
.wiz-summary-wrap .spill {
  font-weight: 600 !important;
  padding: 3px 8px !important;
}

/* Tab counters (red number badges) */
.wiz-summary-wrap .tbadge { font-weight: 700 !important; font-size: 10px !important; }

/* Findings tab labels */
.wiz-summary-wrap .tab { font-weight: 600 !important; }
.wiz-summary-wrap .tab.active { font-weight: 700 !important; }

/* Body text inside report — bump line spacing slightly for readability */
.wiz-summary-wrap p { line-height: 1.65 !important; }

/* Focus rings throughout the wizard for keyboard navigation */
.wiz-summary-wrap button:focus-visible,
.wiz-summary-wrap a:focus-visible,
.wiz-summary-wrap .tab:focus-visible,
.wiz-summary-wrap .ctab:focus-visible {
  outline: 2px solid var(--accent) !important;
  outline-offset: 2px !important;
}

/* Masthead home link */
.masthead-home {
  font-family: var(--mono);
  font-size: 10px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: rgba(255,255,255,0.95);   /* was 0.85 — now 6.0:1 on header */
  text-decoration: none;
  padding: 4px 10px;
  border: 1px solid rgba(255,255,255,0.45);
  border-radius: 2px;
  background: rgba(255,255,255,0.12);
  transition: all 0.15s;
}
.masthead-home:hover {
  background: rgba(255,255,255,0.22);
  border-color: rgba(255,255,255,0.7);
  color: white;
}
.masthead-home:focus-visible {
  outline: 2px solid #ffd9d4;
  outline-offset: 2px;
}

/* Masthead local-only trust pill — visible everywhere as a persistent
   reassurance that this tool processes HAR files entirely in the browser.
   Clickable; opens the HAR explainer modal which has the full local-only
   safety disclosure. */
.masthead-local {
  font-family: var(--mono);
  font-size: 10px;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: #ffffff;
  background: rgba(42,122,79,0.55);    /* desaturated green over header */
  border: 1px solid rgba(108,220,170,0.65);
  padding: 4px 10px 4px 8px;
  border-radius: 2px;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-weight: 600;
  transition: all 0.15s;
}
.masthead-local:hover {
  background: rgba(58,150,100,0.75);
  border-color: #6dc;
}
.masthead-local:focus-visible {
  outline: 2px solid #c8f0d8;
  outline-offset: 2px;
}
.masthead-local-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #6dc;
  box-shadow: 0 0 6px rgba(108,220,170,0.7);
  display: inline-block;
  flex-shrink: 0;
}

@media (max-width: 720px) {
  .masthead-local-text { display: none; }   /* keep just the dot + icon on mobile */
}

/* Inline "Which browser?" CTA used in Step 0 */
.wiz-browser-cta {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 14px;
  margin: 12px 0 4px;
  background: var(--header-light);
  border: 1px solid #b8d4ee;
  border-left: 3px solid var(--header);
  border-radius: 2px;
  font-size: 12.5px;
  line-height: 1.55;
  color: #2d4a66;
}
.wiz-browser-cta .wiz-browser-icon {
  font-size: 18px;
  flex-shrink: 0;
}
.wiz-browser-cta-text { flex: 1; }
.wiz-browser-cta button {
  font-family: var(--mono);
  font-size: 10px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  background: white;
  color: var(--header-dark);
  border: 1px solid var(--header);
  padding: 7px 12px;
  border-radius: 2px;
  cursor: pointer;
  transition: all 0.15s;
  flex-shrink: 0;
  font-weight: 600;
}
.wiz-browser-cta button:hover {
  background: var(--header);
  color: white;
}
.wiz-browser-cta button:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 2px;
}

/* STEP 1 LOCAL-PROCESSING BANNER — the in-context reassurance right before
   the upload action. The masthead pill provides the persistent reassurance;
   this banner provides the at-the-moment-of-action confirmation. */
.wiz-local-banner {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  background: linear-gradient(135deg, #eaf4ee 0%, #d8ede0 100%);
  border: 1px solid #a8d4ba;
  border-left: 3px solid var(--ok);
  border-radius: 3px;
  padding: 14px 16px;
  margin-bottom: 14px;
  font-size: 13px;
  line-height: 1.55;
  color: #163d23;
}
.wiz-local-banner-icon {
  font-size: 20px;
  flex-shrink: 0;
  line-height: 1;
  padding-top: 1px;
}
.wiz-local-banner-text { flex: 1; }
.wiz-local-banner-title {
  font-family: var(--mono);
  font-size: 10px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--ok);
  font-weight: 700;
  margin-bottom: 4px;
}
.wiz-local-banner-body { color: #1a4a2a; }
.wiz-local-banner-body strong { color: #0e3a1c; }
.wiz-local-banner a, .wiz-local-banner button.linklike {
  color: #14502a;
  text-decoration: underline;
  text-underline-offset: 2px;
  background: none;
  border: none;
  font: inherit;
  padding: 0;
  cursor: pointer;
}
.wiz-local-banner a:hover, .wiz-local-banner button.linklike:hover { color: #0a3018; }

/* STEP 1 FORM-POST CAPTURE TIP — visually distinct from the browser/HAR CTAs
   above and below so the eye registers it as separate guidance. */
.wiz-formpost-tip {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 14px 16px;
  margin: 14px 0;
  background: #fdf5ea;
  border: 1px solid #e9c995;
  border-left: 3px solid var(--warn);
  border-radius: 3px;
  font-size: 13px;
  line-height: 1.55;
  color: #5c3a0a;
}
.wiz-formpost-icon {
  font-size: 18px;
  flex-shrink: 0;
  padding-top: 1px;
}
.wiz-formpost-text { flex: 1; }
.wiz-formpost-title {
  font-family: var(--mono);
  font-size: 10px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  font-weight: 700;
  color: var(--warn);
  margin-bottom: 4px;
}
.wiz-formpost-body { color: #4d2f08; }
.wiz-formpost-body strong { color: #2e1b03; }
.wiz-formpost-link {
  display: inline-block;
  margin-top: 6px;
  color: #5c3a0a;
  text-decoration: underline;
  text-underline-offset: 2px;
  font-weight: 600;
}
.wiz-formpost-link:hover { color: #2e1b03; }

/* STEP 1 CLEAR-FILE BUTTON — sits next to the file-loaded indicator (#fok).
   Lets the user swap a HAR without re-doing the whole step. */
.wiz-clear-file {
  font-family: var(--mono);
  font-size: 10px;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  background: transparent;
  color: #c47a1a;
  border: 1px solid #e9c995;
  padding: 5px 10px;
  border-radius: 2px;
  cursor: pointer;
  margin-left: 10px;
  font-weight: 600;
  transition: all 0.15s;
  vertical-align: middle;
}
.wiz-clear-file:hover {
  background: #fdf5ea;
  border-color: var(--warn);
  color: #4d2f08;
}
.wiz-clear-file:focus-visible {
  outline: 2px solid var(--warn);
  outline-offset: 2px;
}

/* REPORT: "Upload a different HAR" — sits in the back-to-inputs row at the
   top of the report panel so the path back to Step 1 is visible without
   needing the rail. */
.wiz-new-har {
  font-family: var(--mono);
  font-size: 11px;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  background: white;
  color: var(--header-dark);
  border: 1px solid var(--header);
  padding: 8px 14px;
  border-radius: 2px;
  cursor: pointer;
  font-weight: 600;
  transition: all 0.15s;
  margin-left: 16px;
}
.wiz-new-har:hover {
  background: var(--header);
  color: white;
}
.wiz-new-har:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 2px;
}
"""



# ---------------- BODY MARKUP ----------------
BODY = f"""
<body class="wiz">

<div class="masthead">
  <span class="masthead-brand">Pixel and Policy</span>
  <span class="masthead-sep">|</span>
  <span class="masthead-tool">HARstack · Wizard</span>
  <a href="https://harstack.com/" class="masthead-home" aria-label="HARstack home">Home</a>
  <button type="button" class="masthead-local" onclick="openModal()" aria-label="Local processing only — open safety details">
    <span class="masthead-local-dot" aria-hidden="true"></span>
    <span class="masthead-local-text">Local only</span>
  </button>
  <div class="masthead-spacer"></div>
  <span class="masthead-v">v2.0w</span>
  <button class="dl-btn" onclick="dlTool()">⬇ Download / Run Locally</button>
</div>

<a href="#wiz-main" class="skip-link">Skip to current step</a>

<main class="wiz-shell" id="wiz-main">

  <!-- HERO (only shown on step 0) -->
  <div class="wiz-hero" id="wizHero">
    <h1>What does your site <em>actually do?</em></h1>
    <p>Upload a HAR file. Get a structured report: tracker inventory, third-party domain map, CDP payload analysis with raw and hashed PII detection, CMP identification and load order, GPC response, consent enforcement gaps. With regulatory citations and audit questions generated from your specific stack.</p>
  </div>

  <!-- PROGRESS RAIL -->
  <nav class="wiz-rail" aria-label="Audit steps">
    <button type="button" class="wiz-rail-step active" data-target="0" onclick="wizGoto(0)">
      <span class="wiz-rail-dot">0</span>
      <span class="wiz-rail-label">Prep</span>
    </button>
    <span class="wiz-rail-line"></span>
    <button type="button" class="wiz-rail-step" data-target="1" onclick="wizGoto(1)">
      <span class="wiz-rail-dot">1</span>
      <span class="wiz-rail-label">HAR</span>
    </button>
    <span class="wiz-rail-line"></span>
    <button type="button" class="wiz-rail-step" data-target="2" onclick="wizGoto(2)">
      <span class="wiz-rail-dot">2</span>
      <span class="wiz-rail-label">GPC</span>
    </button>
    <span class="wiz-rail-line"></span>
    <button type="button" class="wiz-rail-step" data-target="3" onclick="wizGoto(3)">
      <span class="wiz-rail-dot">2b</span>
      <span class="wiz-rail-label">Context</span>
    </button>
    <span class="wiz-rail-line"></span>
    <button type="button" class="wiz-rail-step" data-target="4" onclick="wizGoto(4)">
      <span class="wiz-rail-dot">3</span>
      <span class="wiz-rail-label">Audit</span>
    </button>
    <span class="wiz-rail-line"></span>
    <button type="button" class="wiz-rail-step" data-target="5" onclick="wizGoto(5)">
      <span class="wiz-rail-dot">★</span>
      <span class="wiz-rail-label">Report</span>
    </button>
  </nav>

  <!-- WIZARD PANELS -->
  <div class="wiz-panels">

    <!-- PANEL 0: PREFLIGHT -->
    <section class="wiz-panel active" data-panel="0" aria-labelledby="p0title">
      <div class="wiz-card">
        <div class="wiz-card-hdr">
          <div class="wiz-card-num">0</div>
          <div class="wiz-card-titles">
            <div class="wiz-card-eyebrow">Preflight</div>
            <h2 class="wiz-card-title" id="p0title">Set up your browser first</h2>
          </div>
        </div>
        <div class="wiz-card-body">
          {step0}
        </div>
        <div class="wiz-nav">
          <span class="wiz-step-counter">Step 1 of 6</span>
          <div class="wiz-nav-spacer"></div>
          <button class="wiz-btn wiz-btn-next" onclick="wizNext()">Continue →</button>
        </div>
      </div>
    </section>

    <!-- PANEL 1: HAR FILE -->
    <section class="wiz-panel" data-panel="1" aria-labelledby="p1title">
      <div class="wiz-card">
        <div class="wiz-card-hdr">
          <div class="wiz-card-num">1</div>
          <div class="wiz-card-titles">
            <div class="wiz-card-eyebrow">HAR File</div>
            <h2 class="wiz-card-title" id="p1title">Capture your site's network traffic</h2>
          </div>
        </div>
        <div class="wiz-card-body">
          {step1}
        </div>
        <div class="wiz-nav">
          <button class="wiz-btn wiz-btn-back" onclick="wizPrev()">← Back</button>
          <span class="wiz-step-counter">Step 2 of 6</span>
          <div class="wiz-nav-spacer"></div>
          <button class="wiz-btn wiz-btn-next" id="wizNext1" onclick="wizNext()" disabled>Continue →</button>
        </div>
      </div>
    </section>

    <!-- PANEL 2: GPC SIGNAL -->
    <section class="wiz-panel" data-panel="2" aria-labelledby="p2title">
      <div class="wiz-card">
        <div class="wiz-card-hdr">
          <div class="wiz-card-num">2</div>
          <div class="wiz-card-titles">
            <div class="wiz-card-eyebrow">GPC Signal</div>
            <h2 class="wiz-card-title" id="p2title">Was GPC active during capture?</h2>
          </div>
        </div>
        <div class="wiz-card-body">
          {step2}
        </div>
        <div class="wiz-nav">
          <button class="wiz-btn wiz-btn-back" onclick="wizPrev()">← Back</button>
          <span class="wiz-step-counter">Step 3 of 6</span>
          <div class="wiz-nav-spacer"></div>
          <button class="wiz-btn wiz-btn-next" id="wizNext2" onclick="wizNext()" disabled>Continue →</button>
        </div>
      </div>
    </section>

    <!-- PANEL 3: BUSINESS CONTEXT (2b) -->
    <section class="wiz-panel" data-panel="3" aria-labelledby="p3title">
      <div class="wiz-card">
        <div class="wiz-card-hdr">
          <div class="wiz-card-num">2b</div>
          <div class="wiz-card-titles">
            <div class="wiz-card-eyebrow">Business Context</div>
            <h2 class="wiz-card-title" id="p3title">Help us calibrate regulatory framing</h2>
          </div>
        </div>
        <div class="wiz-card-body">
          {step2b}
        </div>
        <div class="wiz-nav">
          <button class="wiz-btn wiz-btn-back" onclick="wizPrev()">← Back</button>
          <span class="wiz-step-counter">Step 4 of 6 · optional</span>
          <div class="wiz-nav-spacer"></div>
          <button class="wiz-btn wiz-btn-next" onclick="wizNext()">Continue →</button>
        </div>
      </div>
    </section>

    <!-- PANEL 4: ANALYZE -->
    <section class="wiz-panel" data-panel="4" aria-labelledby="p4title">
      <div class="wiz-card">
        <div class="wiz-card-hdr">
          <div class="wiz-card-num">3</div>
          <div class="wiz-card-titles">
            <div class="wiz-card-eyebrow">Analyze</div>
            <h2 class="wiz-card-title" id="p4title">Run the audit</h2>
          </div>
        </div>
        <div class="wiz-card-body">
          {step3}
        </div>
        <div class="wiz-nav">
          <button class="wiz-btn wiz-btn-back" onclick="wizPrev()">← Back</button>
          <span class="wiz-step-counter">Step 5 of 6</span>
          <div class="wiz-nav-spacer"></div>
          <span style="font-family:var(--mono);font-size:10px;color:#888;letter-spacing:0.1em;">Press <strong style="color:var(--accent);">Run the audit</strong> above to continue</span>
        </div>
      </div>
    </section>

    <!-- PANEL 5: REPORT (summary / results) -->
    <section class="wiz-panel" data-panel="5" aria-labelledby="p5title">
      <div style="display:flex;align-items:center;flex-wrap:wrap;gap:8px;margin-bottom:14px;">
        <button type="button" class="wiz-back-inline" onclick="wizPrev()" style="margin-bottom:0;">← Back to inputs</button>
        <button type="button" class="wiz-new-har" onclick="wizUploadDifferent()" aria-label="Upload a different HAR file">↑ Upload a different HAR</button>
      </div>
      <h2 id="p5title" style="font-family:var(--display);font-size:24px;font-style:italic;margin-bottom:6px;color:var(--ink);">Your audit report</h2>
      <p style="font-size:13px;color:#5a6b7a;margin-bottom:20px;line-height:1.6;">A finding warrants investigation. No findings does not mean compliant. Surface-level audit. One page. One session.</p>

      <div class="wiz-summary-wrap">
        {report_panel}
        <div class="wiz-summary-actions">
          <button class="wiz-btn wiz-btn-back" onclick="wizPrev()">← Adjust inputs</button>
          <button class="wiz-new-har" onclick="wizUploadDifferent()" style="margin-left:0;">↑ Upload a different HAR</button>
          <span style="font-family:var(--mono);font-size:10px;letter-spacing:0.1em;color:#999;text-transform:uppercase;">Use the Export button above for sanitized HAR / JSON / CSV / prompt block</span>
        </div>
      </div>
    </section>

  </div>

  <div class="wiz-foot">
    <a href="https://harstack.com/" target="_blank" rel="noopener">harstack.com</a>
    <span class="wiz-foot-sep">·</span>
    <a href="https://pixelandpolicy.com/" target="_blank" rel="noopener">pixelandpolicy.com</a>
    <span class="wiz-foot-sep">·</span>
    <a href="https://harstack.com/tool/" target="_blank" rel="noopener">Classic two-pane view</a>
  </div>

</main>

{exp_modal}

{har_modal}

<!-- BROWSER COMPARISON MODAL (wizard addition) -->
<div class="modal-overlay" id="browserModal" onclick="browserModalBg(event)">
  <div class="modal" role="dialog" aria-modal="true" aria-labelledby="browser-modal-title">
    <div class="modal-hdr">
      <h3 id="browser-modal-title">Which browser should I use?</h3>
      <button class="modal-close" onclick="closeBrowserModal()" aria-label="Close browser comparison">✕</button>
    </div>
    <div class="modal-body">

      <div class="modal-section">
        <div class="modal-section-hdr">The short answer</div>
        <p>Use <strong>Firefox Private Window</strong> for your first audit. It exports the most complete HAR file with no sanitization tricks. Once you have that baseline, repeat the capture in <strong>Brave with default settings</strong>. The gap between those two captures is your actual exposure to a privacy-aware visitor.</p>
      </div>

      <div class="modal-section">
        <div class="modal-section-hdr">Browser by browser</div>
        <div class="modal-browser-grid" style="grid-template-columns: 1fr;">

          <div class="modal-browser-card" style="border-top:3px solid var(--ok);">
            <strong>⭐ Firefox Private Window — Recommended for first capture</strong>
            Exports complete HAR files with full response bodies and all cookie data. No sanitize dialog to trip over. Enables HARstack's response body fingerprint scanner, which catches trackers that hide behind first-party subdomains. This is the most comprehensive single capture you can produce. Use it as the baseline against which every other browser result is compared.
          </div>

          <div class="modal-browser-card" style="border-top:3px solid var(--header);">
            <strong>Chrome Incognito — Best for typical-visitor simulation</strong>
            Chrome is what most of your visitors actually use. It has no built-in tracker blocking, no GPC signal by default. A Chrome capture shows what an average uninstrumented user experiences. Install a GPC extension before capture if you want to test how your stack responds to a privacy signal. Avoid the "sanitize sensitive data" option in the HAR export dialog. It strips cookie and credential metadata that HARstack uses for the analysis.
          </div>

          <div class="modal-browser-card" style="border-top:3px solid var(--accent);">
            <strong>Brave (default settings) — Best for privacy-floor testing</strong>
            Brave blocks third-party trackers natively, fingerprinting requests, and ships GPC turned on out of the box. Capturing in Brave shows what survives aggressive blocking. If a tracker still fires in Brave, it is either first-party hosted, proxied through your CDN, or routed server-side. The Brave result is your privacy floor. Compare it to the Firefox result to see how much leaks through even when the visitor is actively defended.
          </div>

          <div class="modal-browser-card" style="border-top:3px solid var(--warn);">
            <strong>Safari — Use only if your site is Safari-specific</strong>
            Safari is the most restrictive mainstream browser. Intelligent Tracking Prevention (ITP) caps first-party cookie lifetime at seven days, blocks third-party cookies entirely, and partitions storage by site. A Safari capture is informative for understanding the iOS and macOS user experience, but it is not a substitute for Firefox as a baseline. The HAR export workflow is also more cumbersome than Firefox or Chrome. To capture in Safari: enable the Develop menu (Safari → Settings → Advanced), open Web Inspector with <code>⌥+⌘+I</code>, go to the Network tab, then use the export icon to save the HAR. Safari does not offer a sanitize option.
          </div>

        </div>
      </div>

      <div class="modal-section">
        <div class="modal-section-hdr">The recommended workflow</div>
        <ol class="modal-steps">
          <li><strong>Capture 1 — Firefox Private Window.</strong> The complete picture. Run HARstack on this first.</li>
          <li><strong>Capture 2 — Brave default settings.</strong> The privacy floor. Run HARstack again and compare.</li>
          <li><strong>Capture 3 (optional) — Chrome Incognito with GPC extension.</strong> Tests whether your stack responds to a GPC signal. Required if you want to evidence GPC compliance under CCPA Regulations § 7025.</li>
        </ol>
        <p style="font-size:12px;color:#666;margin-top:10px;">Each capture is one HAR file. Run them through HARstack separately. The findings are independent reports. Compare them side by side to see how your tracking surface changes with the visitor's privacy posture.</p>
      </div>

      <div class="modal-warn">
        <strong>One thing the browser cannot tell you</strong>
        A HAR capture only shows what fires on the page you loaded. It does not cover authenticated pages, checkout flows, mobile app traffic, server-side tags fired from your backend, or data processor agreements with the vendors involved. A finding warrants investigation. No findings does not mean compliant.
      </div>

    </div>
  </div>
</div>

{original_script}

<script>
/* ============ WIZARD NAVIGATION (alternate version) ============ */
(function() {{
  const TOTAL_PANELS = 6;          // 0..5
  const LAST_INPUT_STEP = 4;        // panel 4 is Analyze; panel 5 is Report
  let wizCurrent = 0;
  let wizHighest = 0;               // furthest panel reached

  function panels() {{ return document.querySelectorAll('.wiz-panel'); }}
  function rails()  {{ return document.querySelectorAll('.wiz-rail-step'); }}
  function lines()  {{ return document.querySelectorAll('.wiz-rail-line'); }}

  function applyState() {{
    panels().forEach((p, i) => p.classList.toggle('active', i === wizCurrent));
    rails().forEach((r, i) => {{
      r.classList.toggle('active', i === wizCurrent);
      r.classList.toggle('done', i < wizCurrent || (i <= wizHighest && i !== wizCurrent));
      // Allow clicking to any reached step
      r.disabled = i > wizHighest;
    }});
    lines().forEach((l, i) => l.classList.toggle('done', i < wizCurrent));
    // Hide hero after step 0 for tighter screens
    const hero = document.getElementById('wizHero');
    if (hero) hero.style.display = wizCurrent === 0 ? 'block' : 'none';

    // Widen the shell on the report panel so the domain table has room.
    const shell = document.getElementById('wiz-main');
    if (shell) shell.classList.toggle('wiz-shell-wide', wizCurrent === 5);

    // scroll to top on transition
    window.scrollTo({{ top: 0, behavior: 'smooth' }});
  }}

  window.wizGoto = function(i) {{
    if (i < 0 || i >= TOTAL_PANELS) return;
    if (i > wizHighest) return;     // gated
    wizCurrent = i;
    applyState();
  }};

  window.wizNext = function() {{
    if (wizCurrent >= TOTAL_PANELS - 1) return;
    wizCurrent += 1;
    if (wizCurrent > wizHighest) wizHighest = wizCurrent;
    applyState();
  }};

  window.wizPrev = function() {{
    if (wizCurrent === 0) return;
    wizCurrent -= 1;
    applyState();
  }};

  // Clear the loaded HAR file so the user can pick a different one without
  // restarting the wizard. Resets the file input, hides the file-loaded
  // indicator, and re-disables the Continue button on Step 1.
  window.wizClearFile = function() {{
    const fhf = document.getElementById('hf');       // file input
    const fok = document.getElementById('fok');      // "✓ File loaded: name" indicator
    const fn = document.getElementById('fn');        // filename span
    const nextBtn1 = document.getElementById('wizNext1');
    if (fhf) fhf.value = '';
    if (fok) fok.style.display = 'none';
    if (fn) fn.textContent = '';
    if (nextBtn1) nextBtn1.disabled = true;
    // Also clear any cached audit state so a stale report can't surface
    // if the user navigates forward without uploading a new file.
    try {{
      if (typeof window._currentTrackers !== 'undefined') window._currentTrackers = null;
      const rc = document.getElementById('rc');
      const es = document.getElementById('es');
      if (rc) rc.innerHTML = '';
      if (es) es.style.display = '';
    }} catch (e) {{ /* non-fatal */ }}
    // Focus the file input so the next pick is one click away
    if (fhf) fhf.focus();
  }};

  // From the report panel, take the user back to Step 1 and clear the loaded
  // HAR so they can drop a new file. Equivalent to: rail-back to Step 1 +
  // wizClearFile, in one click.
  window.wizUploadDifferent = function() {{
    window.wizClearFile();
    // Navigate directly to Step 1 (panel index 1). Allowed because Step 1
    // has been reached already (wizHighest will be ≥ 1).
    wizCurrent = 1;
    applyState();
  }};

  // Gate Step 1 -> file loaded
  // We poll #fok visibility because the original script sets style.display='block' on file load
  const fok = document.getElementById('fok');
  const nextBtn1 = document.getElementById('wizNext1');
  if (fok && nextBtn1) {{
    const obs = new MutationObserver(() => {{
      const visible = fok.style.display && fok.style.display !== 'none';
      nextBtn1.disabled = !visible;
    }});
    obs.observe(fok, {{ attributes: true, attributeFilter: ['style'] }});
  }}

  // Gate Step 2 -> GPC choice (a .gpc-btn becomes .gsy or .gsn)
  const nextBtn2 = document.getElementById('wizNext2');
  function refreshGpcGate() {{
    if (!nextBtn2) return;
    const chosen = document.querySelector('.gpc-btn.gsy, .gpc-btn.gsn');
    nextBtn2.disabled = !chosen;
  }}
  // Hook into the existing GPC buttons
  const gy = document.getElementById('gy');
  const gn = document.getElementById('gn');
  if (gy) gy.addEventListener('click', () => setTimeout(refreshGpcGate, 0));
  if (gn) gn.addEventListener('click', () => setTimeout(refreshGpcGate, 0));

  // When the user clicks "Run the audit" on panel 4, advance to panel 5 (Report).
  // The original run() displays #ls (loading) then #rc (results). We just transition the panel.
  const rb = document.getElementById('rb');
  if (rb) {{
    rb.addEventListener('click', function() {{
      // Only advance if the button is enabled (HAR is loaded etc.)
      // The button text changes from "Open a HAR file to begin" to "Run audit" when ready;
      // also disabled flag is removed. We rely on the disabled flag.
      if (rb.disabled) return;
      // Allow original handler to start work first, then transition panel
      setTimeout(() => {{
        wizCurrent = 5;
        if (wizCurrent > wizHighest) wizHighest = wizCurrent;
        applyState();
      }}, 60);
    }}, true); // capture so we run alongside, not after
  }}

  // Init
  applyState();
}})();

/* ============ BROWSER COMPARISON MODAL (wizard addition) ============ */
window.openBrowserModal = function() {{
  const modal = document.getElementById('browserModal');
  modal.classList.add('open');
  document.body.style.overflow = 'hidden';
  setTimeout(function() {{
    const first = modal.querySelector('button, [href], input, [tabindex]:not([tabindex="-1"])');
    if (first) first.focus();
  }}, 50);
}};
window.closeBrowserModal = function() {{
  document.getElementById('browserModal').classList.remove('open');
  document.body.style.overflow = '';
  const trigger = document.querySelector('.wiz-browser-cta-btn');
  if (trigger) trigger.focus();
}};
window.browserModalBg = function(e) {{
  if (e.target === document.getElementById('browserModal')) closeBrowserModal();
}};
// Extend existing Escape handler so the new modal also closes
document.addEventListener('keydown', e => {{
  if (e.key === 'Escape') closeBrowserModal();
}});

/* ============================================================
   CSV EXPORT (wizard addition)
   Builds a single sectioned CSV from the existing _analysisJSON
   that the audit script already produces. Injects a download
   button into both the report header band (.rh-actions) and
   as a 4th tab in the Export modal.
   ============================================================ */
(function() {{
  // --- CSV escape helper. Anything with comma, quote, newline, or CR gets quoted. ---
  function csvEsc(v) {{
    if (v === null || v === undefined) return '';
    if (typeof v === 'object') v = JSON.stringify(v);
    v = String(v);
    if (/[",\\r\\n]/.test(v)) {{
      return '"' + v.replace(/"/g, '""') + '"';
    }}
    return v;
  }}

  function rowCsv(arr) {{
    return arr.map(csvEsc).join(',');
  }}

  function section(title) {{
    return ['', '## ' + title.toUpperCase(), ''];
  }}

  function buildCSV() {{
    // The original audit script declares buildAnalysisJSON() as a global function.
    // We call it directly here so the CSV can be built before the Export modal
    // has been opened (which is what populates the _analysisJSON cache var).
    let a;
    try {{
      a = (typeof buildAnalysisJSON === 'function') ? buildAnalysisJSON() : null;
    }} catch (e) {{
      console.error('CSV: buildAnalysisJSON threw', e);
      return null;
    }}
    if (!a) return null;
    const lines = [];

    // ---- META ----
    lines.push('## META');
    lines.push(rowCsv(['key', 'value']));
    lines.push(rowCsv(['tool', a._meta?.tool || '']));
    lines.push(rowCsv(['generated', a._meta?.generated || '']));
    lines.push(rowCsv(['site', a._meta?.site || '']));
    lines.push(rowCsv(['total_requests', a._meta?.total_requests || 0]));
    lines.push(rowCsv(['first_party_domain', a.first_party_domain || '']));
    lines.push(rowCsv(['cmp_status', a.cmp_status || '']));
    lines.push(rowCsv(['cmp_names', (a.cmp_names || []).join('; ')]));
    if (a.outcome) {{
      lines.push(rowCsv(['screening_result', a.outcome.bucket || '']));
      lines.push(rowCsv(['severity', a.outcome.severity || '']));
      lines.push(rowCsv(['recommended_action', a.outcome.recommended_action || '']));
    }}
    if (a.gpc) {{
      lines.push(rowCsv(['gpc_status', a.gpc.status || '']));
      lines.push(rowCsv(['gpc_verified_in_har', a.gpc.verified_in_har]));
      lines.push(rowCsv(['gpc_reported_by_user', a.gpc.reported_by_user]));
    }}

    // ---- FINDINGS ----
    lines.push(...section('Findings'));
    lines.push(rowCsv(['severity', 'type', 'title', 'regulations', 'confidence', 'send_to', 'plain', 'action']));
    (a.findings || []).forEach(f => {{
      lines.push(rowCsv([
        f.severity || '',
        f.type || '',
        f.title || '',
        (f.regulations || []).join('; '),
        f.confidence || '',
        (f.send_to || []).join('; '),
        f.plain || '',
        f.action || '',
      ]));
    }});

    // ---- TRACKERS ----
    lines.push(...section('Trackers Identified'));
    lines.push(rowCsv(['name', 'category', 'risk', 'code', 'regulations']));
    (a.trackers || []).forEach(t => {{
      lines.push(rowCsv([
        t.name || '',
        t.category || '',
        t.risk || '',
        t.code || '',
        (t.regs || []).join('; '),
      ]));
    }});

    // ---- THIRD-PARTY DOMAINS ----
    lines.push(...section('Third-Party Domains'));
    lines.push(rowCsv(['domain', 'registrable', 'requests', 'identified', 'tracker_name', 'tracker_category']));
    (a.third_party_domains || []).forEach(d => {{
      lines.push(rowCsv([
        d.domain || '',
        d.registrable || '',
        d.requests || 0,
        d.identified ? 'yes' : 'no',
        d.tracker_name || '',
        d.tracker_category || '',
      ]));
    }});

    // ---- UNIDENTIFIED THIRD-PARTY DOMAINS ----
    lines.push(...section('Unidentified Third-Party Domains'));
    lines.push(rowCsv(['domain', 'registrable', 'requests']));
    (a.unidentified_third_party_domains || []).forEach(d => {{
      lines.push(rowCsv([d.domain || '', d.registrable || '', d.requests || 0]));
    }});

    // ---- OPERATOR-RELATED DOMAINS ----
    lines.push(...section('Operator-Related Domains'));
    lines.push(rowCsv(['domain', 'registrable', 'requests']));
    (a.operator_related_domains || []).forEach(d => {{
      lines.push(rowCsv([d.domain || '', d.registrable || '', d.requests || 0]));
    }});

    // ---- COOKIES ----
    lines.push(...section('Cookies (Set-Cookie response headers)'));
    lines.push(rowCsv(['name', 'domain', 'set_by', 'persistence_days', 'http_only', 'secure', 'same_site']));
    (a.cookies_summary?.cookies || []).forEach(c => {{
      lines.push(rowCsv([
        c.name || '',
        c.domain || '',
        c.set_by || '',
        c.persistence_days !== null && c.persistence_days !== undefined ? c.persistence_days : '',
        c.http_only ? 'yes' : 'no',
        c.secure ? 'yes' : 'no',
        c.same_site || '',
      ]));
    }});

    // ---- CDP EVENTS ----
    lines.push(...section('CDP Events'));
    lines.push(rowCsv([
      'platform', 'endpoint_type', 'event_type', 'event_name', 'status', 'batch_count',
      'integrations_all_true', 'marketing_consent_denied', 'consent_enforcement_gap',
      'pii_field_paths', 'ad_id_field_paths', 'enabled_destinations', 'denied_consent_ids',
      'allowed_consent_ids', 'context_flags', 'url',
    ]));
    (a.cdp_events || []).forEach(ev => {{
      lines.push(rowCsv([
        ev.platform || '',
        ev.endpoint_type || '',
        ev.event_type || '',
        ev.event_name || '',
        ev.status || '',
        ev.batch_count || '',
        ev.integrations_all_true ? 'yes' : 'no',
        ev.marketing_consent_denied ? 'yes' : 'no',
        ev.consent_enforcement_gap ? 'yes' : 'no',
        (ev.pii_field_paths || []).join('; '),
        (ev.ad_id_field_paths || []).join('; '),
        (ev.enabled_destinations || []).join('; '),
        (ev.denied_consent_ids || []).join('; '),
        (ev.allowed_consent_ids || []).join('; '),
        (ev.context_flags || []).join('; '),
        ev.url || '',
      ]));
    }});

    // ---- FIRST-PARTY POST PII ----
    lines.push(...section('First-Party POST PII'));
    lines.push(rowCsv(['host', 'path', 'operation_name', 'raw_pii_fields', 'hashed_pii_fields', 'uuid_fields', 'url']));
    (a.first_party_pii || []).forEach(r => {{
      lines.push(rowCsv([
        r.host || '',
        r.path || '',
        r.operation_name || '',
        (r.raw_pii_fields || []).map(f => `${{f.path}} (${{f.type}})`).join('; '),
        (r.hashed_pii_fields || []).map(f => `${{f.path}} (${{f.type}})`).join('; '),
        (r.uuid_fields || []).join('; '),
        r.url || '',
      ]));
    }});

    // ---- THIRD-PARTY POST PII ----
    lines.push(...section('Third-Party POST PII'));
    lines.push(rowCsv(['host', 'path', 'operation_name', 'raw_pii_fields', 'hashed_pii_fields', 'uuid_fields', 'url']));
    (a.third_party_pii || []).forEach(r => {{
      lines.push(rowCsv([
        r.host || '',
        r.path || '',
        r.operation_name || '',
        (r.raw_pii_fields || []).map(f => `${{f.path}} (${{f.type}})`).join('; '),
        (r.hashed_pii_fields || []).map(f => `${{f.path}} (${{f.type}})`).join('; '),
        (r.uuid_fields || []).join('; '),
        r.url || '',
      ]));
    }});

    // Excel-friendly BOM so column headers + accented characters render correctly
    return '\\ufeff' + lines.join('\\r\\n') + '\\r\\n';
  }}

  function dlCSV() {{
    // Use window.buildReportCSV so any wrappers (e.g. the consent-signal
    // augmentation) are respected. Falling back to the closure buildCSV
    // only if no wrapper exists.
    const builder = (typeof window.buildReportCSV === 'function') ? window.buildReportCSV : buildCSV;
    const csv = builder();
    if (!csv) {{ alert('Run the audit before exporting CSV.'); return; }}
    const site = (document.getElementById('su')?.value || '')
      .replace(/https?:\\/\\//, '')
      .replace(/[^a-z0-9]/gi, '-')
      .toLowerCase() || 'site';
    const blob = new Blob([csv], {{ type: 'text/csv;charset=utf-8' }});
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `harstack-report-${{site}}-${{Date.now()}}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }}
  window.dlReportCSV = dlCSV;
  window.buildReportCSV = buildCSV;

  // --- Copy CSV to clipboard for the modal's preview/copy button ---
  window.copyReportCSV = async function() {{
    const builder = (typeof window.buildReportCSV === 'function') ? window.buildReportCSV : buildCSV;
    const csv = builder();
    if (!csv) return;
    try {{
      await navigator.clipboard.writeText(csv);
      const btn = document.getElementById('csvCopyBtn');
      if (btn) {{ const orig = btn.textContent; btn.textContent = '✓ Copied'; setTimeout(() => btn.textContent = orig, 2000); }}
    }} catch {{ alert('Copy failed — use the download button.'); }}
  }};

  // --- DOM injection: add CSV button into .rh-actions whenever the report renders ---
  function injectCsvButton() {{
    const rha = document.querySelector('#rc .rh-actions');
    if (!rha) return;
    if (rha.querySelector('.export-btn-csv')) return; // already there
    const btn = document.createElement('button');
    btn.className = 'export-btn export-btn-csv';
    btn.type = 'button';
    btn.setAttribute('aria-label', 'Download report as CSV');
    btn.innerHTML = '⬇ CSV Report';
    btn.onclick = dlCSV;
    rha.appendChild(btn);
  }}

  // Observe #rc for changes; re-inject when the report (re)renders.
  const rc = document.getElementById('rc');
  if (rc) {{
    const obs = new MutationObserver(injectCsvButton);
    obs.observe(rc, {{ childList: true, subtree: false }});
    // also try immediately in case content already exists
    injectCsvButton();
  }}

  // --- Inject the 4th tab into the Export modal ---
  function injectCsvTab() {{
    const tabs = document.querySelector('#expModal .exp-format-tabs');
    if (!tabs || tabs.querySelector('[data-exp-csv]')) return;
    const tab = document.createElement('div');
    tab.className = 'exp-tab';
    tab.setAttribute('data-exp-csv', '1');
    tab.setAttribute('role', 'tab');
    tab.setAttribute('tabindex', '0');
    tab.textContent = 'CSV Report';
    tab.onclick = function() {{
      // mimic the original expTab() switch behavior
      document.querySelectorAll('#expModal .exp-pane').forEach(p => p.classList.remove('active'));
      document.querySelectorAll('#expModal .exp-tab').forEach(t => t.classList.remove('active'));
      document.getElementById('exp-pane-csv').classList.add('active');
      tab.classList.add('active');
    }};
    tab.onkeydown = function(e) {{ if (e.key === 'Enter' || e.key === ' ') {{ e.preventDefault(); tab.click(); }} }};
    tabs.appendChild(tab);

    // Build the matching pane
    const modal = document.querySelector('#expModal .exp-modal-body');
    if (!modal) return;
    const pane = document.createElement('div');
    pane.className = 'exp-pane';
    pane.id = 'exp-pane-csv';
    pane.innerHTML = `
      <div class="exp-warn" style="background:#f0eaf7;border-left:3px solid #6b5aa0;padding:10px 13px;font-size:12px;line-height:1.6;color:#3a2a5e;margin-bottom:14px;border-radius:0 3px 3px 0;">
        <strong style="display:block;font-family:var(--mono);font-size:9px;letter-spacing:0.1em;text-transform:uppercase;color:#3a2a5e;margin-bottom:3px;">What this contains</strong>
        One CSV file. Sectioned by report area: Meta, Findings, Trackers, Third-Party Domains, Unidentified Third-Party Domains, Operator-Related Domains, Cookies, CDP Events, First-Party POST PII, Third-Party POST PII. Each section has its own header row. Opens cleanly in Excel, Google Sheets, or Numbers.
      </div>
      <div class="exp-info" style="background:#eaf4ee;border-left:3px solid #2a7a4f;padding:10px 13px;font-size:12px;line-height:1.6;color:#1a4a2a;margin-bottom:14px;border-radius:0 3px 3px 0;">
        <strong style="display:block;font-family:var(--mono);font-size:9px;letter-spacing:0.1em;text-transform:uppercase;color:#1a4a2a;margin-bottom:3px;">What is safe to share</strong>
        Same redaction posture as the Analysis JSON. URLs and field paths are retained; PII values are not present. Cookie names retained, cookie values are not. Safe to share with legal, compliance, or a vendor for follow-up.
      </div>
      <div style="display:flex;gap:8px;margin-bottom:14px;flex-wrap:wrap;">
        <button class="exp-dl-btn" onclick="dlReportCSV()">⬇ Download report .csv</button>
        <button class="exp-dl-btn" id="csvCopyBtn" onclick="copyReportCSV()" style="flex:0 0 auto;">Copy CSV</button>
      </div>
      <div class="exp-preview-label">Preview (first ~40 rows)</div>
      <pre class="exp-preview" id="csv-preview" style="max-height:300px;"></pre>
    `;
    // Insert after the last existing pane if possible
    const lastPane = modal.querySelector('.exp-pane:last-of-type');
    if (lastPane) {{
      lastPane.parentNode.insertBefore(pane, lastPane.nextSibling);
    }} else {{
      modal.appendChild(pane);
    }}
  }}

  // Hook the existing openExpModal so we populate CSV preview when shown.
  function refreshCsvPreview() {{
    const builder = (typeof window.buildReportCSV === 'function') ? window.buildReportCSV : buildCSV;
    const csv = builder();
    const el = document.getElementById('csv-preview');
    if (!el) return;
    if (!csv) {{ el.textContent = '(Run the audit first.)'; return; }}
    // Strip BOM, take first ~40 lines for preview
    const text = csv.replace(/^\\ufeff/, '');
    const head = text.split('\\r\\n').slice(0, 40).join('\\r\\n');
    el.textContent = head + (text.split('\\r\\n').length > 40 ? '\\r\\n... (truncated for preview)' : '');
  }}

  // Wrap openExpModal so injection + preview refresh both happen automatically.
  const origOpen = window.openExpModal;
  window.openExpModal = function(which) {{
    if (typeof origOpen === 'function') origOpen.call(this, which);
    injectCsvTab();
    refreshCsvPreview();
  }};
}})();

/* ============================================================
   CONSENT SIGNAL VERIFICATION (wizard addition, v1)

   Adds parsing for ad-platform consent signals that ride as URL
   parameters on tracker requests. The HAR captures these but the
   v1 audit script does not parse them.

   Platforms supported:
     - Google Consent Mode v2 (gcs, gcd, dma, dma_cps, npa)
     - Meta Pixel DPO/LDU (dpo, dpoco, dpost, ud[em], ud[ph])
     - Microsoft UET (gv, enableMUID, mskwid, pid)
     - Click ID persistence (fbclid, gclid, msclkid, ttclid,
       wbraid, gbraid, li_fat_id)

   Five new finding rules:
     1. Google consent state mismatch (gcs vs CMP-declared/GPC)
     2. Meta DPO missing on US-CA visitor
     3. Meta Advanced Matching despite LDU signal
     4. Microsoft UET granted despite GPC denied
     5. Click IDs persisting in tracker requests after opt-out

   The "consent_default_granted" finding (GDPR-flavored) is held
   for v2.

   Each finding's recommended action includes:
     - A pointer to a consent-flip capture for verification
     - A note that CMP cookie state and server-side propagation
       must be verified separately

   Output:
     - New finding type 'consent_signal' (annotated via
       annotateFinding extension)
     - Findings appended to window._currentAllFindings
     - Outcome re-computed via computeOutcome
     - Report re-rendered with augmented findings
     - Analysis JSON gains a consent_signals_observed section
     - CSV export gains a CONSENT SIGNALS section
   ============================================================ */

(function() {{
  // Stash the parsed HAR on window so our wrapper can read it without
  // re-parsing the file from the input. The original code calls loadF(f)
  // as a free identifier inside its own script, so we cannot intercept it
  // by replacing window.loadF. Instead we attach a parallel listener to
  // the same DOM events that trigger loadF, and we also support the
  // file-input being repopulated via wizUploadDifferent.
  function stashHarFromFile(f) {{
    if (!f) return;
    const r = new FileReader();
    r.onload = e => {{
      try {{ window._har = JSON.parse(e.target.result); }} catch {{ /* original handler alerts */ }}
    }};
    r.readAsText(f);
  }}
  // Wire to the file input
  function wireHarStash() {{
    const hf = document.getElementById('hf');
    const dz = document.getElementById('dz');
    if (hf && !hf._wizConsentWired) {{
      hf.addEventListener('change', e => {{ if (e.target.files[0]) stashHarFromFile(e.target.files[0]); }});
      hf._wizConsentWired = true;
    }}
    if (dz && !dz._wizConsentWired) {{
      dz.addEventListener('drop', e => {{
        if (e.dataTransfer && e.dataTransfer.files[0]) stashHarFromFile(e.dataTransfer.files[0]);
      }});
      dz._wizConsentWired = true;
    }}
  }}
  if (document.readyState === 'loading') {{
    document.addEventListener('DOMContentLoaded', wireHarStash);
  }} else {{
    wireHarStash();
  }}

  // ---------- HELPERS ----------
  function getQueryParam(url, name) {{
    try {{
      const u = new URL(url, 'https://placeholder.invalid');
      return u.searchParams.get(name);
    }} catch {{ return null; }}
  }}
  function getAllQueryParams(url) {{
    try {{
      const u = new URL(url, 'https://placeholder.invalid');
      const o = {{}};
      for (const [k, v] of u.searchParams.entries()) o[k] = v;
      return o;
    }} catch {{ return {{}}; }}
  }}
  function parsePostBody(entry) {{
    try {{
      const pd = entry.request && entry.request.postData;
      if (!pd) return null;
      if (pd.mimeType && /application\\/json/.test(pd.mimeType)) {{
        return JSON.parse(pd.text || '{{}}');
      }}
      if (pd.mimeType && /application\\/x-www-form-urlencoded/.test(pd.mimeType)) {{
        const o = {{}};
        (pd.text || '').split('&').forEach(p => {{
          const [k, v] = p.split('=');
          if (k) o[decodeURIComponent(k.replace(/\\+/g, ' '))] = decodeURIComponent((v||'').replace(/\\+/g, ' '));
        }});
        return o;
      }}
      return null;
    }} catch {{ return null; }}
  }}

  // ---------- GOOGLE CONSENT MODE V2 ----------
  // gcs is a five-character string. Position 1 = 'G', position 2 = '1'.
  // Position 3 = ad_storage (0/1). Position 4 = analytics_storage (0/1).
  // Values: G100 = both denied, G101 = ad denied, G110 = analytics denied,
  // G111 = both granted, G1-- = consent default (no user choice yet).
  function decodeGcs(gcs) {{
    if (!gcs) return null;
    const map = {{
      'G100': {{ ad_storage: 'denied', analytics_storage: 'denied', label: 'both denied' }},
      'G101': {{ ad_storage: 'denied', analytics_storage: 'granted', label: 'ad denied / analytics granted' }},
      'G110': {{ ad_storage: 'granted', analytics_storage: 'denied', label: 'ad granted / analytics denied' }},
      'G111': {{ ad_storage: 'granted', analytics_storage: 'granted', label: 'both granted' }},
      'G1--': {{ ad_storage: 'default', analytics_storage: 'default', label: 'consent default (no user choice)' }},
    }};
    return map[gcs] || {{ raw: gcs, label: 'unknown' }};
  }}

  function extractGoogleSignals(entry) {{
    const url = entry.request && entry.request.url;
    if (!url) return null;
    // Identify Google endpoints that carry CM v2 signals
    const isGoogleEndpoint = /\\/g\\/collect|\\/ccm\\/collect|\\/pagead\\/form-data|\\/pagead\\/1p-user-list|gtag\\/js\\?id=/.test(url);
    if (!isGoogleEndpoint) return null;

    const params = getAllQueryParams(url);
    const gcs = params.gcs || null;
    const gcd = params.gcd || null;
    const dma = params.dma || null;
    const dma_cps = params.dma_cps || null;
    const npa = params.npa || null;

    // Enhanced Conversions hashed PII fields
    const em = params.em || null;
    const pn = params.pn || null;

    if (!gcs && !gcd && !dma && !em && !pn) return null;  // no signal info

    return {{
      platform: 'google',
      endpoint: url.split('?')[0],
      url,
      method: entry.request.method,
      gcs,
      gcs_decoded: decodeGcs(gcs),
      gcd,
      dma,
      dma_cps,
      npa,
      enhanced_conversions_email_hashed: !!em,
      enhanced_conversions_phone_hashed: !!pn,
      raw_params: {{ gcs, gcd, dma, dma_cps, npa, em: em ? '[redacted]' : null, pn: pn ? '[redacted]' : null }},
    }};
  }}

  // ---------- META PIXEL DPO / LDU ----------
  // dpo is a stringified JSON array. ["LDU"] = Limited Data Use enabled.
  // dpoco: country code (1=US, 0=default).
  // dpost: state code (1000=CA, 1001=CO, 1002=CT, 1003=VA, 1004=UT, etc.)
  function decodeDpo(dpo) {{
    if (!dpo) return null;
    try {{
      const parsed = JSON.parse(dpo);
      if (Array.isArray(parsed) && parsed.includes('LDU')) {{
        return {{ ldu: true, label: 'Limited Data Use signaled' }};
      }}
      return {{ ldu: false, raw: dpo, label: 'no LDU flag' }};
    }} catch {{ return {{ raw: dpo, label: 'unparseable' }}; }}
  }}
  function decodeDpost(dpost) {{
    if (!dpost) return null;
    const map = {{ '1000': 'CA', '1001': 'CO', '1002': 'CT', '1003': 'VA', '1004': 'UT' }};
    return map[String(dpost)] || dpost;
  }}

  function extractMetaSignals(entry) {{
    const url = entry.request && entry.request.url;
    if (!url) return null;
    const isMeta = /facebook\\.com\\/tr|facebook\\.com\\/signals|graph\\.facebook\\.com.*events/.test(url);
    if (!isMeta) return null;

    const params = getAllQueryParams(url);
    const postBody = parsePostBody(entry);

    // Pull from either query (GET pixel) or body (CAPI POST)
    const get = (key) => params[key] || (postBody && postBody[key]) || null;

    const dpo = get('dpo');
    const dpoco = get('dpoco');
    const dpost = get('dpost');

    // Advanced Matching fields. In the GET pixel they appear as ud[em]=..., in CAPI as user_data.em
    const am_email = params['ud[em]'] || (postBody && postBody.user_data && postBody.user_data.em) || null;
    const am_phone = params['ud[ph]'] || (postBody && postBody.user_data && postBody.user_data.ph) || null;
    const am_firstname = params['ud[fn]'] || (postBody && postBody.user_data && postBody.user_data.fn) || null;
    const am_lastname = params['ud[ln]'] || (postBody && postBody.user_data && postBody.user_data.ln) || null;

    const fbc = params.fbc || (postBody && postBody.fbc) || null;
    const fbp = params.fbp || (postBody && postBody.fbp) || null;

    if (!dpo && !dpoco && !dpost && !am_email && !am_phone && !fbc && !fbp) return null;

    return {{
      platform: 'meta',
      endpoint: url.split('?')[0],
      url,
      method: entry.request.method,
      dpo,
      dpo_decoded: decodeDpo(dpo),
      dpoco,
      dpost,
      dpost_decoded: decodeDpost(dpost),
      advanced_matching: {{
        email_present: !!am_email,
        phone_present: !!am_phone,
        firstname_present: !!am_firstname,
        lastname_present: !!am_lastname,
      }},
      fbc_present: !!fbc,
      fbp_present: !!fbp,
    }};
  }}

  // ---------- MICROSOFT UET ----------
  // gv: granted-state code. 2 = granted, 1 = denied.
  // enableMUID: 1 = drop the Microsoft User ID cookie.
  function extractMicrosoftSignals(entry) {{
    const url = entry.request && entry.request.url;
    if (!url) return null;
    const isMs = /bat\\.bing\\.com\\/action|bat\\.bing\\.net\\/action|bat\\.bing\\.com\\/p\\/action/.test(url);
    if (!isMs) return null;

    const params = getAllQueryParams(url);
    const gv = params.gv || null;
    const enableMUID = params.enableMUID || null;
    const mskwid = params.mskwid || null;
    const pid = params.pid || null;          // Enhanced Conversions hashed identifier

    if (!gv && !enableMUID && !mskwid && !pid) return null;

    return {{
      platform: 'microsoft',
      endpoint: url.split('?')[0],
      url,
      method: entry.request.method,
      gv,
      gv_decoded: gv === '2' ? 'granted' : (gv === '1' ? 'denied' : 'unknown'),
      enableMUID,
      enableMUID_decoded: enableMUID === '1' ? 'MUID cookie will be set' : (enableMUID === '0' ? 'MUID cookie suppressed' : 'not signaled'),
      mskwid_present: !!mskwid,
      pid_present: !!pid,                    // Enhanced Conversions hashed identifier
    }};
  }}

  // ---------- CLICK ID PERSISTENCE ----------
  // Identify tracker requests that carry ad-platform click IDs.
  // Skip placeholder values that platforms use to mean "no click present":
  //   - "N" (Bing's standard placeholder for missing msclkid)
  //   - empty string
  //   - "null" / "undefined" / "0" as string sentinels
  const CLICK_ID_KEYS = ['fbclid','gclid','msclkid','ttclid','wbraid','gbraid','li_fat_id','twclid','dclid'];
  const CLICK_ID_PLACEHOLDERS = new Set(['', 'N', 'null', 'undefined', '0', 'none']);
  function isRealClickIdValue(v) {{
    if (v === null || v === undefined) return false;
    const s = String(v).trim();
    if (s.length < 5) return false;   // genuine click IDs are always longer
    if (CLICK_ID_PLACEHOLDERS.has(s)) return false;
    return true;
  }}
  function extractClickIdsInTrackers(entry, isTrackerDomain) {{
    if (!isTrackerDomain) return null;
    const url = entry.request && entry.request.url;
    if (!url) return null;
    const params = getAllQueryParams(url);
    const found = [];
    for (const k of CLICK_ID_KEYS) {{
      if (isRealClickIdValue(params[k])) found.push({{ key: k, present: true }});
    }}
    if (!found.length) return null;
    return {{
      platform: 'click_id_carrier',
      endpoint: url.split('?')[0],
      url,
      method: entry.request.method,
      click_ids: found,
    }};
  }}

  // ---------- CDP-LAYER CONSENT FIELDS ----------
  // GA4 events ship event parameters as ep.* in the query string. Many CMPs
  // and CDPs add a marketing_consent / tracking_consent event parameter so
  // downstream BigQuery / data plane processing can filter by consent state.
  // RudderStack and Segment use a context.consent object in the request body.
  //
  // We extract whatever we find and surface it for comparison with the
  // gtag-level consent signal. A contradiction (e.g. gcs=granted but
  // ep.marketing_consent=false) tells you the CDP layer believes one thing
  // and the ad layer believes another.
  function extractCdpConsentFields(entry) {{
    const url = entry.request && entry.request.url;
    if (!url) return null;
    const params = getAllQueryParams(url);
    const postBody = parsePostBody(entry);

    const fields = {{}};
    // GA4 ep.* fields
    for (const key of ['ep.marketing_consent', 'ep.tracking_consent', 'ep.analytics_consent', 'ep.ad_consent']) {{
      if (params[key] !== undefined) fields[key] = params[key];
    }}
    // RudderStack / Segment context.consent object in POST bodies
    if (postBody && postBody.context && postBody.context.consent) {{
      fields['context.consent'] = postBody.context.consent;
    }}
    // RudderStack also uses integrations.* for per-destination consent
    if (postBody && postBody.integrations && typeof postBody.integrations === 'object') {{
      fields['integrations'] = Object.keys(postBody.integrations).filter(k => postBody.integrations[k] === false).join(',') || null;
    }}
    // Some CDPs put marketing_consent at the top level of the event body
    if (postBody) {{
      for (const k of ['marketing_consent', 'tracking_consent', 'analytics_consent']) {{
        if (postBody[k] !== undefined) fields[k] = postBody[k];
      }}
    }}

    if (Object.keys(fields).length === 0) return null;
    return {{
      platform: 'cdp_consent_field',
      endpoint: url.split('?')[0],
      url,
      method: entry.request.method,
      fields,
    }};
  }}

  // ---------- ORCHESTRATOR ----------
  function parseConsentSignals(har, thirdPartyDomains) {{
    if (!har || !har.log || !har.log.entries) return [];
    const tpHosts = new Set((thirdPartyDomains || []).map(d => d.domain || d));
    const signals = [];

    for (const e of har.log.entries) {{
      let s;
      s = extractGoogleSignals(e);     if (s) signals.push(s);
      s = extractMetaSignals(e);       if (s) signals.push(s);
      s = extractMicrosoftSignals(e);  if (s) signals.push(s);
      s = extractCdpConsentFields(e);  if (s) signals.push(s);
      // Click ID check needs the tracker-domain hint
      try {{
        const host = new URL(e.request.url).hostname;
        const isTp = [...tpHosts].some(h => host === h || host.endsWith('.' + h));
        s = extractClickIdsInTrackers(e, isTp); if (s) signals.push(s);
      }} catch {{ /* skip */ }}
    }}
    return signals;
  }}

  // ---------- FINDING RULES ----------
  // For each rule, the recommended action references the consent-flip
  // capture and the CMP / server-side propagation checks. This matches the
  // editorial decision to point users at the next step rather than try to
  // adjudicate from one HAR.

  const NEXT_STEPS = 'Next steps for this finding: (1) Run a consent-flip capture against the same page (load with consent denied, capture; then load with consent granted, capture; compare). (2) Inspect the CMP consent state cookie in the browser to see what the CMP declared. (3) Verify server-side consent propagation: the browser signal here may not match what your CAPI / Conversions API endpoints transmit from your backend.';

  function detectConsentSignalFindings(signals, gpcStatus) {{
    const findings = [];
    const gpcActive = (gpcStatus === 'verified' || gpcStatus === 'reported');
    const sevUnderGpc = gpcActive ? 'high' : 'medium';
    const gpcContext = gpcActive
      ? 'The visitor\\'s browser sent the Sec-GPC:1 header during this capture, which raises the severity of this finding.'
      : 'The visitor\\'s browser did not send a GPC signal during this capture. The finding is independent of GPC but a re-capture with GPC active is recommended to confirm severity.';

    // ---- Rule 1: Google consent state mismatch (GPC-conditional, HIGH) ----
    // Trigger: user reported/verified GPC active, but a Google CM v2 endpoint
    // shows gcs=G110 or G111 (ad_storage granted) or G1-- (default-granted).
    const googleSignals = signals.filter(s => s.platform === 'google' && s.gcs);
    const googleAdGranted = googleSignals.filter(s =>
      s.gcs_decoded && (s.gcs_decoded.ad_storage === 'granted' || s.gcs_decoded.ad_storage === 'default')
    );
    if (gpcActive && googleAdGranted.length > 0) {{
      findings.push({{
        type: 'consent_signal',
        title: `Google Consent Mode signal mismatch: ad_storage granted despite GPC`,
        sev: 'high',
        regs: ['CCPA/CPRA', 'ECPA'],
        plain: `${{googleAdGranted.length}} Google tracker request${{googleAdGranted.length>1?'s':''}} fired with ad_storage granted (gcs values: ${{[...new Set(googleAdGranted.map(s => s.gcs))].join(', ')}}) while the visitor's browser sent the Sec-GPC:1 header. The gcs parameter is what Google actually saw at the moment of the hit, not what your CMP dashboard reports. A granted ad_storage signal means Google treated the visitor as having consented to advertising data use, despite the GPC opt-out. This is the kind of mismatch that produces enforcement exposure under CCPA Regulations § 7025. ${{NEXT_STEPS}}`,
        action: 'Verify the gtag consent state propagation in your tag manager. The CMP must call gtag(\\'consent\\', \\'update\\', {{ad_storage: \\'denied\\'}}) before any gtag-managed pixel fires. Confirm in your tag manager that the consent update listener is wired and tested. Check the CMP cookie to see whether the CMP itself recorded the GPC signal correctly. If yes, the gap is at the CMP-to-gtag handoff. If no, the gap is at the GPC-to-CMP layer.',
        _consent_signal_detail: googleAdGranted.map(s => ({{ url: s.endpoint, gcs: s.gcs, decoded: s.gcs_decoded.label }})),
      }});
    }}

    // ---- Rule 6 (new): Google Consent Mode v2 not wired into gtag ----
    // Trigger: Google requests are present in the HAR but NONE of them carry a
    // gcs parameter. This means gtag is firing without ever having received a
    // gtag('consent', 'update', ...) call. Google treats absent gcs as full
    // consent inferred. This is a configuration bug regardless of GPC.
    const googleAll = signals.filter(s => s.platform === 'google');
    const googleWithGcs = googleAll.filter(s => s.gcs);
    if (googleAll.length >= 2 && googleWithGcs.length === 0) {{
      findings.push({{
        type: 'consent_signal',
        title: `Google Consent Mode v2 not wired: no gcs parameter on any Google request`,
        sev: sevUnderGpc,
        regs: ['CCPA/CPRA', 'ECPA'],
        plain: `${{googleAll.length}} Google tracker request${{googleAll.length>1?'s':''}} fired without a gcs (Google Consent State) parameter. Under Google Consent Mode v2, the gcs parameter is set on every hit after gtag('consent', 'update', ...) has been called. Its absence indicates that the consent state is never being declared to gtag. Google then defaults to treating the visitor as if both ad_storage and analytics_storage are granted. This is a configuration gap, not necessarily a violation, but the gtag deployment is not honoring whatever consent state the CMP recorded. ${{gpcContext}} ${{NEXT_STEPS}}`,
        action: 'Wire gtag Consent Mode v2 into your CMP. Most CMPs (Osano, OneTrust, Cookiebot, Termly, CookieYes) ship a gtag integration template. Verify the integration is active: open DevTools, type gtag(\\'get\\', \\'AW-...\\', \\'consent_state\\') and check the returned object. If the CMP is loaded but no integration is configured, the simplest fix is to call gtag(\\'consent\\', \\'default\\', {{ad_storage: \\'denied\\', analytics_storage: \\'denied\\'}}) on page load before any gtag commands, then have the CMP fire gtag(\\'consent\\', \\'update\\', ...) when a consent choice is made.',
        _consent_signal_detail: googleAll.slice(0, 5).map(s => ({{ url: s.endpoint, gcd: s.gcd, dma: s.dma, npa: s.npa }})),
      }});
    }}

    // ---- Rule 6b (new): Google Enhanced Conversions PII transmitted ----
    // Trigger: any Google request (g/collect, ccm/collect, pagead/form-data,
    // pagead/1p-user-list, viewthroughconversion, rmkt) carries em=tv.1~em.{hash}
    // or pn=tv.1~pn.{hash}. The em= field encodes a hashed email captured
    // client-side via auto-detection or developer-configured Enhanced
    // Conversions. The pn= field is the equivalent for phone.
    //
    // Hashed PII still constitutes a sharing event under CCPA/CPRA. The FTC's
    // BetterHelp consent order (FTC Docket No. 2023-169, July 2023) treats
    // hashed identifiers as covered information, on the basis that the
    // receiving party already possesses the underlying value and the hash
    // does not conceal identity.
    //
    // Severity scales with GPC posture. Independent of "consent mode wired"
    // because Enhanced Conversions fires through a separate configuration
    // path (auto-detection or manual ec_mode) and can fire even when consent
    // mode signals are correctly set.
    const ecGoogle = googleAll.filter(s =>
      s.enhanced_conversions_email_hashed || s.enhanced_conversions_phone_hashed
    );
    if (ecGoogle.length > 0) {{
      const fieldsTransmitted = [];
      if (ecGoogle.some(s => s.enhanced_conversions_email_hashed)) fieldsTransmitted.push('hashed email (em)');
      if (ecGoogle.some(s => s.enhanced_conversions_phone_hashed)) fieldsTransmitted.push('hashed phone (pn)');
      findings.push({{
        type: 'consent_signal',
        title: `Google Enhanced Conversions transmitted ${{fieldsTransmitted.join(' and ')}}`,
        sev: sevUnderGpc,
        regs: ['CCPA/CPRA', 'ECPA'],
        plain: `Google Enhanced Conversions PII was transmitted on ${{ecGoogle.length}} Google request${{ecGoogle.length>1?'s':''}}. Field${{fieldsTransmitted.length>1?'s':''}} present: ${{fieldsTransmitted.join(', ')}}. Enhanced Conversions hashes the visitor's email or phone number client-side (in the gtag library) before transmitting to Google for ad attribution matching. Google already possesses the underlying values from logged-in users, so the hash does not conceal identity. The FTC's BetterHelp consent order (FTC Docket No. 2023-169, July 2023) treats hashed identifiers as covered information and treats their transmission to ad platforms as a disclosure that requires consent. Under CCPA/CPRA the same analysis applies: this is a sharing event for cross-context behavioral advertising. ${{gpcContext}} ${{NEXT_STEPS}}`,
        action: 'Configure Enhanced Conversions to respect consent state. The standard wiring: (1) Enhanced Conversions fires only when ad_storage is granted in the Google Consent Mode v2 state. (2) Your CMP must signal ad_storage=denied via gtag(\\'consent\\', \\'update\\', ...) before any conversion event fires. Verify in Google Tag Manager that the Enhanced Conversions configuration on each conversion tag has "Wait for consent before sending" enabled and is set to require ad_storage. For sites using auto-detection (gtag scans form fields), the auto-detection itself extracts the PII from the page; suppress this by disabling Enhanced Conversions on opt-out at the tag manager level rather than at the platform setting level. Disclose Enhanced Conversions by name in your privacy policy.',
        _consent_signal_detail: ecGoogle.slice(0, 5).map(s => ({{
          endpoint: s.endpoint,
          email: s.enhanced_conversions_email_hashed,
          phone: s.enhanced_conversions_phone_hashed,
        }})),
      }});
    }}

    // ---- Rule 2: Meta DPO missing (always-on, severity varies with GPC) ----
    // Trigger: Meta pixel fires with no dpo parameter. This is a CCPA exposure
    // for US visitors and a heightened concern under GPC. We flag both, but
    // severity scales with GPC posture.
    const metaSignals = signals.filter(s => s.platform === 'meta');
    const metaNoDpo = metaSignals.filter(s => !s.dpo);
    if (metaNoDpo.length > 0) {{
      const titleSuffix = gpcActive ? ' under GPC' : '';
      findings.push({{
        type: 'consent_signal',
        title: `Meta Pixel fired with no Data Processing Options signal${{titleSuffix}}`,
        sev: sevUnderGpc,
        regs: ['CCPA/CPRA', 'ECPA'],
        plain: `${{metaNoDpo.length}} Meta Pixel request${{metaNoDpo.length>1?'s':''}} fired without a Data Processing Options (dpo) parameter. Meta honors Limited Data Use (LDU) when signaled by the dpo parameter ([\\"LDU\\"]). Absence of the dpo parameter is interpreted as full consent for Meta's data processing. For California visitors under CCPA, the LDU signal must be sent to satisfy the opt-out propagation requirement; silence does not satisfy it. ${{gpcContext}} ${{NEXT_STEPS}}`,
        action: 'Configure your Meta Pixel deployment to set the LDU flag when GPC is active or when the visitor has opted out under CCPA. In the standard fbq() pixel: fbq(\\'dataProcessingOptions\\', [\\'LDU\\'], 1, 1000) before any track call. In server-side CAPI: include data_processing_options=["LDU"], data_processing_options_country=1, data_processing_options_state=1000 in every event payload. Confirm your tag manager fires the LDU configuration before any standard Meta Pixel events.',
        _consent_signal_detail: metaNoDpo.slice(0, 5).map(s => ({{ url: s.endpoint, advanced_matching: s.advanced_matching }})),
      }});
    }}

    // ---- Rule 3: Meta LDU present but Advanced Matching firing (always-on, HIGH) ----
    // This is a configuration bug regardless of GPC.
    const metaLduAm = metaSignals.filter(s =>
      s.dpo_decoded && s.dpo_decoded.ldu === true &&
      (s.advanced_matching.email_present || s.advanced_matching.phone_present ||
       s.advanced_matching.firstname_present || s.advanced_matching.lastname_present)
    );
    if (metaLduAm.length > 0) {{
      findings.push({{
        type: 'consent_signal',
        title: `Meta Advanced Matching PII transmitted alongside LDU signal`,
        sev: 'high',
        regs: ['CCPA/CPRA', 'ECPA'],
        plain: `${{metaLduAm.length}} Meta Pixel request${{metaLduAm.length>1?'s':''}} carried Advanced Matching fields (hashed email, phone, name) in the same request as a Limited Data Use signal. LDU restricts what Meta does with the data downstream; it does not suppress the data from being transmitted in the request. The hashed PII still leaves your site and reaches Meta's infrastructure. For audit and disclosure purposes, this is a sharing event under CPRA, regardless of the LDU restriction Meta applies after receipt. The FTC's position on hashed identifiers (BetterHelp consent order, FTC Docket No. 2023-169) treats hashed identifiers as covered information. ${{NEXT_STEPS}}`,
        action: 'Configure your Meta Pixel deployment to suppress Advanced Matching extraction entirely when the visitor has opted out, rather than relying on LDU as a downstream restriction. In fbq(): omit the Advanced Matching object from fbq(\\'init\\', \\'PIXEL_ID\\', {{}}) when consent is denied. In CAPI: do not populate the user_data object when consent is denied. The browser request should not include ud[em], ud[ph], or any related field for opted-out users. Audit your tag manager and any CMP integration that suppresses pixel firing -- many of them suppress the page-load fbq.track() but not the upstream fbq.init() that configures Advanced Matching.',
        _consent_signal_detail: metaLduAm.slice(0, 5).map(s => ({{ url: s.endpoint, ldu: true, advanced_matching: s.advanced_matching }})),
      }});
    }}

    // ---- Rule 4: Microsoft UET granted under GPC (GPC-conditional, HIGH) ----
    const msSignals = signals.filter(s => s.platform === 'microsoft');
    const msGranted = msSignals.filter(s => s.gv === '2');
    if (gpcActive && msGranted.length > 0) {{
      findings.push({{
        type: 'consent_signal',
        title: `Microsoft UET fired with consent granted despite GPC`,
        sev: 'high',
        regs: ['CCPA/CPRA', 'ECPA'],
        plain: `${{msGranted.length}} Microsoft UET request${{msGranted.length>1?'s':''}} fired with gv=2 (consent granted) while the visitor's browser sent the Sec-GPC:1 header. The gv parameter is the consent state Microsoft saw at the moment of the hit. A granted signal means Microsoft Advertising treated the visitor as having consented to ad personalization despite the GPC opt-out. ${{NEXT_STEPS}}`,
        action: 'Configure your Microsoft UET deployment to set the consent state correctly. The UET tag supports a uetq.push([\\'consent\\', \\'update\\', {{ad_storage: \\'denied\\'}}]) API. The CMP must call this before any uetq.push() event. Verify in your tag manager that the consent update fires before any UET event tag. If MUID cookie persistence is undesired on opt-out, also set enableMUID=0 in the UET configuration.',
        _consent_signal_detail: msGranted.map(s => ({{ url: s.endpoint, gv: s.gv, decoded: s.gv_decoded }})),
      }});
    }}

    // ---- Rule 5: Click ID persistence (always-on, severity scales with GPC) ----
    const clickIdSignals = signals.filter(s => s.platform === 'click_id_carrier');
    if (clickIdSignals.length > 0) {{
      const allKeys = [...new Set(clickIdSignals.flatMap(s => s.click_ids.map(c => c.key)))];
      const titleSuffix = gpcActive ? ' under GPC' : '';
      findings.push({{
        type: 'consent_signal',
        title: `Ad-platform click IDs persisted into tracker requests${{titleSuffix}}`,
        sev: sevUnderGpc,
        regs: ['CCPA/CPRA'],
        plain: `Ad-platform click IDs (${{allKeys.join(', ')}}) appeared in ${{clickIdSignals.length}} third-party tracker request${{clickIdSignals.length>1?'s':''}}. Click IDs ride in URLs and survive most consent-based suppression because they are forwarded as URL parameters rather than as separately-set cookies. Forwarding a click ID to a third-party tracker is a sharing event under CCPA: the click ID itself, joined to the third-party's data, identifies the visitor's prior advertising context. ${{gpcContext}} ${{NEXT_STEPS}}`,
        action: 'Strip ad-platform click IDs from URLs before they are forwarded to third-party trackers. Server-side: rewrite outbound URLs to omit fbclid, gclid, msclkid, ttclid, wbraid, gbraid, and li_fat_id when consent is denied. Tag manager: configure custom JavaScript variables that read these parameters from the URL and conditionally suppress them based on consent state. The pattern is the same for all click ID parameters. Note that this finding describes a transport-layer leakage; the receiving platforms have their own consent enforcement obligations which are separate.',
        _consent_signal_detail: clickIdSignals.slice(0, 5).map(s => ({{ url: s.endpoint, click_ids: s.click_ids.map(c => c.key) }})),
      }});
    }}

    // ---- Rule 7 (new): CDP-layer consent contradicts gtag-layer consent ----
    // Trigger: ep.marketing_consent / ep.tracking_consent / context.consent
    // says one thing, and the gtag gcs parameter in the same HAR says another.
    //
    // The most common contradiction pattern: gtag fires with gcs=G111
    // (both granted) but the CDP layer carries marketing_consent=false. That
    // means the CMP is talking to the CDP correctly but is not talking to
    // gtag, so the ad-side trackers are firing as if the user consented even
    // though the analytics-side records the denial.
    //
    // The inverse case (gtag denies but CDP says granted) is rarer but worth
    // flagging because it indicates the CDP layer is the gap.
    const cdpFields = signals.filter(s => s.platform === 'cdp_consent_field');
    if (cdpFields.length > 0 && googleSignals.length > 0) {{
      // Aggregate: does CDP say marketing is denied?
      const cdpDeniesMarketing = cdpFields.some(s => {{
        const v = s.fields['ep.marketing_consent'] !== undefined ? s.fields['ep.marketing_consent']
                : s.fields['marketing_consent'] !== undefined ? s.fields['marketing_consent']
                : null;
        if (v === null) return false;
        const sv = String(v).toLowerCase();
        return sv === 'false' || sv === '0' || sv === 'denied' || sv === 'no';
      }});
      const cdpGrantsMarketing = cdpFields.some(s => {{
        const v = s.fields['ep.marketing_consent'] !== undefined ? s.fields['ep.marketing_consent']
                : s.fields['marketing_consent'] !== undefined ? s.fields['marketing_consent']
                : null;
        if (v === null) return false;
        const sv = String(v).toLowerCase();
        return sv === 'true' || sv === '1' || sv === 'granted' || sv === 'yes';
      }});

      // Does gtag say ad_storage is granted?
      const gtagGrantsAd = googleSignals.some(s =>
        s.gcs_decoded && s.gcs_decoded.ad_storage === 'granted'
      );
      // Does gtag say ad_storage is denied?
      const gtagDeniesAd = googleSignals.some(s =>
        s.gcs_decoded && s.gcs_decoded.ad_storage === 'denied'
      );

      if (cdpDeniesMarketing && gtagGrantsAd) {{
        findings.push({{
          type: 'consent_signal',
          title: `CDP layer denies marketing consent but gtag fires with ad_storage granted`,
          sev: 'high',
          regs: ['CCPA/CPRA', 'ECPA'],
          plain: `The CDP layer (CDP event parameters such as ep.marketing_consent or context.consent) records that marketing consent was denied for this visitor. The gtag layer, in the same HAR, sent Google Consent Mode signals indicating ad_storage was granted. The CMP is talking to one part of your stack and not the other. The CDP layer is honoring the consent state; the gtag layer is not. ${{NEXT_STEPS}}`,
          action: 'Audit the gtag consent integration in your CMP. Many CMPs have a separate integration template for gtag versus for CDP event enrichment, and they can fall out of sync when one is updated and the other is not. Run gtag(\\'get\\', \\'<your_ad_id>\\', \\'consent_state\\') in DevTools immediately after the page loads with consent denied; the returned object should show ad_storage as denied. If it shows granted, the CMP-to-gtag integration is broken. The CDP-to-CMP integration is working correctly.',
          _consent_signal_detail: [
            {{ source: 'cdp', marketing_consent: 'denied', example: cdpFields[0].endpoint }},
            {{ source: 'gtag', ad_storage: 'granted', example: googleSignals[0].endpoint }},
          ],
        }});
      }} else if (cdpGrantsMarketing && gtagDeniesAd) {{
        findings.push({{
          type: 'consent_signal',
          title: `gtag denies ad_storage but CDP layer grants marketing consent`,
          sev: 'medium',
          regs: ['CCPA/CPRA'],
          plain: `The CDP layer indicates that marketing consent was granted for this visitor. The gtag layer, in the same HAR, sent Google Consent Mode signals indicating ad_storage was denied. This is the inverse of the more common configuration gap: the CDP layer thinks the user consented but the ad layer is treating them as opted out. Less risky than the inverse, but indicates the consent integration is inconsistent. ${{NEXT_STEPS}}`,
          action: 'Determine which layer reflects the user\\'s actual choice. Inspect the CMP cookie to see what consent state it recorded. Whichever layer disagrees with the CMP cookie is the layer with the broken integration. Reconcile so that gtag, the CDP, and the CMP all hold the same state for each visitor.',
          _consent_signal_detail: [
            {{ source: 'cdp', marketing_consent: 'granted', example: cdpFields[0].endpoint }},
            {{ source: 'gtag', ad_storage: 'denied', example: googleSignals[0].endpoint }},
          ],
        }});
      }}
    }}

    // ---- Rule 8 (new): Consent signals verified (info-level) ----
    // Fires when:
    //   - At least one substantive consent signal was captured
    //     (Google gcs, Meta dpo, Microsoft gv, or CDP marketing_consent)
    //   - AND none of rules 1-7 fired (so we are not papering over a real finding)
    //   - This is the positive-verification disclosure the report otherwise lacks
    if (findings.length === 0) {{
      // Build a summary of what we did see, so the user understands what
      // was checked and confirmed clean.
      const verifiedSummary = [];
      if (googleSignals.length > 0) {{
        const states = [...new Set(googleSignals.map(s => s.gcs_decoded && s.gcs_decoded.label).filter(Boolean))];
        const gcsStates = states.length ? states.join('; ') : 'gcs parameter present';
        verifiedSummary.push(`Google Consent Mode v2 active on ${{googleSignals.length}} Google request${{googleSignals.length>1?'s':''}} (${{gcsStates}})`);
      }}
      const metaWithDpo = metaSignals.filter(s => s.dpo);
      if (metaWithDpo.length > 0) {{
        verifiedSummary.push(`Meta Data Processing Options signaled on ${{metaWithDpo.length}} Meta request${{metaWithDpo.length>1?'s':''}}`);
      }}
      const msWithGv = msSignals.filter(s => s.gv);
      if (msWithGv.length > 0) {{
        const granted = msWithGv.filter(s => s.gv === '1').length;
        verifiedSummary.push(`Microsoft UET consent signaled on ${{msWithGv.length}} UET request${{msWithGv.length>1?'s':''}} (${{granted}} denied state${{granted!==1?'s':''}})`);
      }}
      if (cdpFields.length > 0) {{
        verifiedSummary.push(`CDP-layer consent fields present on ${{cdpFields.length}} CDP event${{cdpFields.length>1?'s':''}}`);
      }}

      // Only fire if we actually saw substantive signals worth verifying
      if (verifiedSummary.length > 0) {{
        findings.push({{
          type: 'consent_signal',
          title: `Consent signals verified, no mismatches detected`,
          sev: 'ok',
          regs: ['CCPA/CPRA'],
          plain: `Your stack is signaling consent state to its ad and analytics platforms, and the signals captured in this HAR are internally consistent. What was verified in this capture: ${{verifiedSummary.join('; ')}}. ${{gpcActive ? 'The consent signals captured here are consistent with the GPC posture you reported.' : 'GPC was not active for this capture, so this verification confirms that consent signals are being transmitted but does not test the GPC response path.'}} This is a positive observation about one capture against one page in one consent state. It does not guarantee correct behavior on other pages, on form submits, or under different consent choices. Run a consent-flip capture against the same page to verify the signals change as expected when the consent state changes.`,
          action: gpcActive
            ? 'No remediation required for this capture. To extend coverage: (1) Run a form-submit capture to verify the same consent signals propagate at the moment a user submits a form. (2) Run a consent-flip capture (pre-consent, post-grant, post-denial) to verify the signals change correctly between states. (3) Check the CMP consent cookie alongside this capture to confirm the CMP recorded the same state the signals reflect.'
            : 'No remediation required for this capture. To extend coverage: (1) Run the same capture with GPC active to verify the consent signals change to a denied state. (2) Run a form-submit capture to verify the same consent signals propagate at the moment a user submits a form. (3) Run a consent-flip capture (pre-consent, post-grant, post-denial) to verify the signals change correctly between states.',
          _consent_signal_detail: signals.slice(0, 5).map(s => ({{
            platform: s.platform,
            endpoint: s.endpoint,
            gcs: s.gcs,
            dpo: s.dpo,
            gv: s.gv,
            cdp_fields: s.fields ? Object.keys(s.fields) : undefined,
          }})),
        }});
      }}
    }}

    return findings;
  }}

  // ---------- FAILED-REQUEST DETECTION ----------
  // Walk the HAR entries and flag requests with 4xx/5xx status codes.
  //
  // Severity model:
  //   HIGH  - failed request on a recognized tracker domain. The privacy
  //           policy probably names the vendor; the abandoned infrastructure
  //           is a hijack / supply-chain risk; data is still leaving the
  //           browser in the request despite the server returning an error.
  //   INFO  - any other failed request. Surfaced as a low-priority
  //           observation. Many of these are benign (deleted image, dead
  //           CDN asset) but worth noting in case a privacy-relevant pattern
  //           emerges.
  //
  // Tracker domains are sourced from a.trackers (Map) which the original
  // audit populates during analyzeHAR.
  function detectFailedRequestFindings(har, analysis) {{
    const findings = [];
    if (!har || !har.log || !har.log.entries) return findings;

    // Build a set of registrable domains that the audit identified as
    // trackers. We match each failed-request host against this set.
    const trackerDomains = new Set();
    if (analysis && analysis.trackers) {{
      for (const t of analysis.trackers.values()) {{
        if (t.url) {{
          try {{
            const h = new URL(t.url).hostname;
            trackerDomains.add(h);
            // Also add the registrable form (last two labels)
            const parts = h.split('.');
            if (parts.length >= 2) trackerDomains.add(parts.slice(-2).join('.'));
          }} catch {{ /* skip */ }}
        }}
      }}
    }}

    function isTrackerHost(host) {{
      if (trackerDomains.has(host)) return true;
      // Check parent domains
      const parts = host.split('.');
      for (let i = 1; i < parts.length - 1; i++) {{
        if (trackerDomains.has(parts.slice(i).join('.'))) return true;
      }}
      return false;
    }}

    const trackerFailures = [];
    const otherFailures = [];

    for (const e of har.log.entries) {{
      const status = (e.response && e.response.status) || 0;
      if (status < 400) continue;
      const url = e.request && e.request.url;
      if (!url) continue;
      let host = '';
      try {{ host = new URL(url).hostname; }} catch {{ continue; }}
      // Skip first-party failures on the audited domain itself; these are
      // usually internal app errors, not privacy concerns.
      const firstPartyHost = analysis && analysis.firstPartyDomain;
      if (firstPartyHost && (host === firstPartyHost || host.endsWith('.' + firstPartyHost))) {{
        continue;
      }}
      // Also skip operator-related domains (sister domains under the same
      // brand stem) for the same reason.
      const opRelated = (analysis && analysis.operatorRelatedDomains) || [];
      if (opRelated.some(d => host === d.domain || host.endsWith('.' + d.domain))) {{
        continue;
      }}

      const item = {{ status, url, host, method: (e.request && e.request.method) || 'GET' }};
      if (isTrackerHost(host)) {{
        trackerFailures.push(item);
      }} else {{
        otherFailures.push(item);
      }}
    }}

    // HIGH-severity finding: failures on recognized tracker domains
    if (trackerFailures.length > 0) {{
      const uniqueHosts = [...new Set(trackerFailures.map(f => f.host))];
      findings.push({{
        type: 'failed_request',
        title: `${{trackerFailures.length}} failed request${{trackerFailures.length>1?'s':''}} on tracker infrastructure (${{uniqueHosts.length}} host${{uniqueHosts.length>1?'s':''}})`,
        sev: 'high',
        regs: ['CCPA/CPRA', 'ECPA'],
        plain: `${{trackerFailures.length}} request${{trackerFailures.length>1?'s':''}} to recognized tracker domains failed (4xx/5xx status) during this capture. Hosts: ${{uniqueHosts.join(', ')}}. A failed request to a tracker is not a "nothing happened" event. The visitor's IP address, User-Agent, referrer, and cookies in scope for that host were transmitted before the server responded. Beyond the in-request data leakage, failed tracker requests create three additional privacy concerns: (1) Domain hijack and supply-chain risk: if the vendor's infrastructure goes away, the path becomes available for an attacker to take over and serve hostile content to your visitors. The Polyfill.io supply-chain attack in 2024 is the canonical recent example. (2) Privacy policy mismatch: your privacy policy probably names this vendor as a sub-processor, describing a data flow that no longer exists as documented. (3) Subresource integrity gap: if the loading tag does not pin a hash via the integrity attribute, any future response from that host (including from a new owner) will execute as authoritative.`,
        action: 'For each failed tracker request: (1) Remove the tag if it is no longer needed. Leaving abandoned tag references in production is a configuration debt that becomes a security debt. (2) If the tag is still intended, contact the vendor about the failure and reach out to your CDN/tag manager to confirm the integration is current. (3) Update your privacy policy: if the vendor is named but the integration is no longer active, remove the reference. If the vendor is named and the integration is broken, document that explicitly. (4) For all third-party script tags, add subresource integrity (SRI) hashes via the integrity attribute. This prevents supply-chain attacks if the third-party host is compromised.',
        _failed_request_detail: trackerFailures.slice(0, 10).map(f => ({{ status: f.status, host: f.host, url: f.url, method: f.method }})),
      }});
    }}

    // INFO-level finding: failures on non-tracker domains
    if (otherFailures.length > 0) {{
      const uniqueHosts = [...new Set(otherFailures.map(f => f.host))];
      findings.push({{
        type: 'failed_request',
        title: `${{otherFailures.length}} failed request${{otherFailures.length>1?'s':''}} on non-tracker third-party host${{uniqueHosts.length>1?'s':''}}`,
        sev: 'ok',
        regs: ['CCPA/CPRA'],
        plain: `${{otherFailures.length}} request${{otherFailures.length>1?'s':''}} to non-tracker third-party domains failed (4xx/5xx status) during this capture. Hosts: ${{uniqueHosts.slice(0, 8).join(', ')}}${{uniqueHosts.length>8?` and ${{uniqueHosts.length-8}} more`:''}}. Most failed third-party requests are benign (a deleted image, a stale CDN asset, a removed feature). The data transmitted in the request itself (IP, User-Agent, referrer, cookies in scope) still left the browser. This is surfaced as an observation rather than a finding because the privacy impact is typically minimal. Review the host list to confirm none of these are vendors that should have been recognized as trackers.`,
        action: 'Optional: review the host list and confirm none are tracker or analytics vendors that the audit failed to recognize. If any are unrecognized trackers, the audit should be updated to include them. For routine CDN or image-host failures, no action is required beyond the normal site-quality concern of fixing broken assets.',
        _failed_request_detail: otherFailures.slice(0, 20).map(f => ({{ status: f.status, host: f.host, url: f.url, method: f.method }})),
      }});
    }}

    return findings;
  }}

  // ---------- WRAPPER ----------
  // Wrap window.run to augment the audit with consent-signal parsing.
  // Runs after the original audit completes and _currentAnalysis is set.
  const origRun = window.run;
  window.run = async function() {{
    if (typeof origRun !== 'function') return;
    await origRun.apply(this, arguments);

    // Original audit is complete. _currentAnalysis is set.
    const a = window._currentAnalysis;
    if (!a) return;
    if (!window._har) return;       // HAR not stashed for some reason

    try {{
      const signals = parseConsentSignals(window._har, a.thirdPartyDomains || []);
      const consentFindings = detectConsentSignalFindings(signals, a.gpcStatus);
      const failedReqFindings = detectFailedRequestFindings(window._har, a);
      const newFindings = consentFindings.concat(failedReqFindings);

      // Run annotateFinding on each new finding so send_to and confidence are set
      const annotated = newFindings.map(f => {{
        try {{
          if (typeof annotateFinding === 'function') {{
            const r = annotateFinding(f);
            // Force send_to for our new types
            if (!r.send_to || !r.send_to.length) {{
              if (f.type === 'failed_request') {{
                r.send_to = ['Tag manager owner', 'Web engineering', 'Security'];
              }} else {{
                r.send_to = ['Tag manager owner', 'Marketing ops', 'Privacy counsel'];
              }}
            }}
            r.confidence = r.confidence || 'observed';
            return r;
          }}
        }} catch {{ /* fall through to default */ }}
        const defaultSendTo = f.type === 'failed_request'
          ? ['Tag manager owner', 'Web engineering', 'Security']
          : ['Tag manager owner', 'Marketing ops', 'Privacy counsel'];
        return {{ ...f, send_to: defaultSendTo, confidence: 'observed' }};
      }});

      // Append to the analysis
      a.findings = (a.findings || []).concat(annotated);
      a.consent_signals_observed = signals;

      // Re-compute outcome with the augmented findings
      if (typeof computeOutcome === 'function') {{
        // Re-implement the escalate hook to recognize consent_signal AND
        // tracker-domain failed-request findings (both are high severity)
        const consentEscalate = annotated.some(f =>
          (f.type === 'consent_signal' || f.type === 'failed_request') && f.sev === 'high'
        );
        const newOutcome = computeOutcome(a.findings, a);
        if (consentEscalate && newOutcome.bucket !== 'Escalate') {{
          newOutcome.bucket = 'Escalate';
          newOutcome.sev = 'high';
          newOutcome.reasons = newOutcome.reasons || [];
          newOutcome.reasons.unshift('Ad-platform consent signals or tracker infrastructure failures observed.');
          newOutcome.action = 'Send to legal, security, and privacy counsel immediately. The factual observations above are the primary exhibit.';
        }} else if (consentEscalate) {{
          newOutcome.reasons = newOutcome.reasons || [];
          newOutcome.reasons.push('Ad-platform consent signals or tracker infrastructure failures observed.');
        }}
        a.outcome = newOutcome;
      }}

      window._currentAllFindings = a.findings;

      // Re-render the report. genAuditQs needs the same arg order it had originally.
      if (typeof genAuditQs === 'function' && typeof render === 'function') {{
        const aqData = genAuditQs(a.findings, a.trackers, a.cookies, a.cmpStatus, a.cdpEvents, a.sgtmCandidates, a.gpcStatus);
        render(a.findings, a, aqData);
      }}
    }} catch (err) {{
      console.error('Consent signal / failed-request augmentation failed:', err);
    }}
  }};

  // ---------- BUILD INTO ANALYSIS JSON ----------
  // Extend buildAnalysisJSON so the JSON export and AI prompt include
  // the consent signals.
  const origBuildJson = window.buildAnalysisJSON;
  if (typeof origBuildJson === 'function') {{
    window.buildAnalysisJSON = function() {{
      const a = origBuildJson.apply(this, arguments);
      try {{
        const ca = window._currentAnalysis;
        if (a && ca && ca.consent_signals_observed) {{
          a.consent_signals_observed = ca.consent_signals_observed;
        }}
      }} catch {{ /* non-fatal */ }}
      return a;
    }};
  }}

  // ---------- EXTEND CSV EXPORT ----------
  // buildReportCSV is set on window by our CSV exporter. Wrap to add a
  // CONSENT SIGNALS section.
  const origBuildCsv = window.buildReportCSV;
  if (typeof origBuildCsv === 'function') {{
    window.buildReportCSV = function() {{
      let csv = origBuildCsv.apply(this, arguments);
      if (!csv) return csv;
      try {{
        const ca = window._currentAnalysis;
        const signals = (ca && ca.consent_signals_observed) || [];
        const failedReqFindings = (ca && ca.findings)
          ? ca.findings.filter(f => f.type === 'failed_request' && f._failed_request_detail)
          : [];
        if (!signals.length && !failedReqFindings.length) return csv;

        // Helper: csvEsc is in scope inside the original IIFE only.
        // Re-implement locally.
        const esc = v => {{
          if (v === null || v === undefined) return '';
          if (typeof v === 'object') v = JSON.stringify(v);
          v = String(v);
          return /[",\\r\\n]/.test(v) ? '"' + v.replace(/"/g, '""') + '"' : v;
        }};
        const rowCsv = arr => arr.map(esc).join(',');

        const sectionLines = [];

        // ---- CONSENT SIGNALS section ----
        if (signals.length) {{
          sectionLines.push('');
          sectionLines.push('## CONSENT SIGNALS');
          sectionLines.push('');
          sectionLines.push(rowCsv(['platform', 'endpoint', 'method', 'gcs', 'gcs_decoded', 'gcd', 'dma', 'dma_cps', 'dpo', 'dpoco', 'dpost_decoded', 'gv', 'gv_decoded', 'enableMUID', 'click_ids', 'advanced_matching', 'enhanced_conversions_pii', 'url']));
          for (const s of signals) {{
            const gcsDec = s.gcs_decoded ? s.gcs_decoded.label : '';
            const dpoDec = s.dpo_decoded ? s.dpo_decoded.label : '';
            const am = s.advanced_matching
              ? Object.keys(s.advanced_matching).filter(k => s.advanced_matching[k]).join('+')
              : '';
            const ecPii = s.enhanced_conversions_email_hashed ? 'email_hashed' :
                          s.enhanced_conversions_phone_hashed ? 'phone_hashed' : '';
            const clickIds = (s.click_ids || []).map(c => c.key).join('+');
            sectionLines.push(rowCsv([
              s.platform || '', s.endpoint || '', s.method || '',
              s.gcs || '', gcsDec, s.gcd || '', s.dma || '', s.dma_cps || '',
              s.dpo || '', s.dpoco || '', s.dpost_decoded || '',
              s.gv || '', s.gv_decoded || '', s.enableMUID || '',
              clickIds, am, ecPii, s.url || '',
            ]));
          }}
        }}

        // ---- FAILED REQUESTS section ----
        if (failedReqFindings.length) {{
          sectionLines.push('');
          sectionLines.push('## FAILED REQUESTS');
          sectionLines.push('');
          sectionLines.push(rowCsv(['category', 'status', 'method', 'host', 'url']));
          for (const f of failedReqFindings) {{
            const category = f.sev === 'high' ? 'tracker_infrastructure' : 'non_tracker';
            for (const r of (f._failed_request_detail || [])) {{
              sectionLines.push(rowCsv([category, r.status, r.method || '', r.host || '', r.url || '']));
            }}
          }}
        }}

        // Append before the trailing newline
        csv = csv.replace(/\\r?\\n$/, '');
        csv = csv + '\\r\\n' + sectionLines.join('\\r\\n') + '\\r\\n';
      }} catch (err) {{
        console.error('CSV consent-signals/failed-requests augmentation failed:', err);
      }}
      return csv;
    }};
  }}
}})();
</script>
"""




# Reassemble wizard output
out = head_with_style + WIZARD_CSS + "</style>\n</head>\n" + BODY + "\n</body>\n</html>\n"

# ============================================================
# POST-ASSEMBLY TEXTUAL FIXES (wizard-only)
# Catches wizard-injected entries (ADDITIONAL_CMPS) and embedded
# JS-template finding strings in BODY.
# ============================================================

POST_FIXES = [
    # ---- regs:[] arrays in the wizard-injected tracker entries ----
    # The build-time regex-based rewrite above handles `original_script`
    # (the source's existing tracker map). It does NOT touch the BODY
    # string which contains my wizard-injected entries. Catch those here.
    ("regs:['ECPA','CCPA/CPRA']", "regs:['ECPA','US State Privacy']", None),
    ("regs:['CCPA/CPRA','GDPR']", "regs:['US State Privacy','GDPR']", None),
    ("regs:['ECPA','CIPA','CCPA/CPRA']", "regs:['ECPA','CIPA','US State Privacy']", None),
    ("regs: ['CCPA/CPRA', 'ECPA']", "regs: ['US State Privacy', 'ECPA']", None),
    ("regs: ['CCPA/CPRA','ECPA']", "regs: ['US State Privacy','ECPA']", None),
    ("regs: ['CCPA/CPRA']", "regs: ['US State Privacy']", None),

    # ---- 'Must be suppressed' softening in wizard-injected tracker entries ----
    # Replaces the absolute claim with a more accurate jurisdiction-aware
    # version. Used in OpenAI Ads SDK, StackAdapt, Magellan AI, X Ads.
    # Note: the wizard-injected entries use \' escape in the rendered output
    # (Python triple-quoted -> in-memory has \\' -> output file has \').
    # Replacement text must use \' for any single quotes because the
    # surrounding d:'...' JS string literal needs them escaped.
    (
        r"OpenAI Ads constitutes \'sharing\' under CPRA. Must be suppressed on GPC and CCPA opt-out.",
        r"OpenAI Ads generally constitutes \'sharing,\' \'sale,\' or \'targeted advertising\' under most US state privacy laws. Suppression on GPC is required in California (per the August 2022 Sephora settlement and subsequent CPPA enforcement, including the March 2025 Honda settlement) and is required or recommended under most of the other 19 state privacy laws active in 2026, with 12 of those states specifically requiring honoring of universal opt-out signals including GPC.",
        1,
    ),
    (
        r"StackAdapt constitutes \'sharing\' under CPRA and must be suppressed on GPC and CCPA opt-out.",
        r"StackAdapt generally constitutes \'sharing,\' \'sale,\' or \'targeted advertising\' under most US state privacy laws. Suppression on GPC is required in California and is required or recommended under most other state privacy law jurisdictions.",
        1,
    ),
    (
        "Magellan AI constitutes sharing under CPRA. Must be suppressed on GPC and CCPA opt-out.",
        r"Magellan AI generally constitutes \'sharing,\' \'sale,\' or \'targeted advertising\' under most US state privacy laws (the cross-device ID resolution with Tapad is a particularly clear case for the \'sale\' classification in California, where the CCPA defines \'sale\' to include disclosure for non-monetary value exchange). Suppression on GPC is required in California and is required or recommended under most other state privacy law jurisdictions.",
        1,
    ),
    (
        "Constitutes sharing under CPRA. Must be suppressed on GPC and CCPA opt-out.",
        r"Generally constitutes \'sharing,\' \'sale,\' or \'targeted advertising\' under most US state privacy laws. Suppression on GPC is required in California and is required or recommended under most other state privacy law jurisdictions.",
        1,  # X Ads entry
    ),

    # ---- BetterHelp citation: imprecise → precise + narrower hashing framing ----
    # Used in the Enhanced Conversions finding (Rule 6b) and Meta LDU+AM
    # finding (Rule 3). The original framing said BetterHelp 'treats hashed
    # identifiers as covered information' which is too categorical. The
    # narrower accurate version is that hashing doesn't protect privacy
    # when the recipient can un-hash, which is the case for Meta and Google.
    (
        "The FTC's BetterHelp consent order (FTC Docket No. 2023-169, July 2023) treats hashed identifiers as covered information and treats their transmission to ad platforms as a disclosure that requires consent. Under CCPA/CPRA the same analysis applies: this is a sharing event for cross-context behavioral advertising.",
        "The FTC's BetterHelp consent order (FTC File No. 2023-169, In the Matter of BetterHelp, Inc., Docket C-4796, final order July 14, 2023) established that hashing fails to protect privacy when the receiving party can un-hash the data. The FTC's press release specifically stated that hashing 'won't protect the privacy of consumers' information if third parties can un-hash the data.' That fact pattern applies directly here: Google already possesses the underlying email and phone values for logged-in users and can match the hashed values back to identified accounts. Under most US state privacy laws, transmission of identifying information to a third-party advertising platform constitutes 'sharing,' 'sale,' or 'targeted advertising' depending on the jurisdiction's terminology.",
        1,
    ),
    (
        "For audit and disclosure purposes, this is a sharing event under CPRA, regardless of the LDU restriction Meta applies after receipt. The FTC's position on hashed identifiers (BetterHelp consent order, FTC Docket No. 2023-169) treats hashed identifiers as covered information.",
        "For audit and disclosure purposes, this is a sharing/sale event under most US state privacy laws regardless of the LDU restriction Meta applies after receipt; LDU is a Meta-side processing limitation, not a transmission suppression. The FTC's BetterHelp consent order (FTC File No. 2023-169, Docket C-4796, final order July 14, 2023) established that hashing does not protect privacy when the recipient can un-hash the data, which applies here because Meta already possesses email and phone values for its logged-in users.",
        1,
    ),

    # ---- 'sharing' under CPRA → broader US state privacy framing ----
    # Two places in finding plain-text that use CPRA-only framing for
    # 'sharing' events. Generalize to the multi-state framing.
    (
        "Forwarding a click ID to a third-party tracker is a sharing event under CCPA: the click ID itself, joined to the third-party's data, identifies the visitor's prior advertising context.",
        "Forwarding a click ID to a third-party tracker is generally a 'sharing,' 'sale,' or 'targeted advertising' event under most US state privacy laws: the click ID itself, joined to the third-party's data, identifies the visitor's prior advertising context.",
        1,
    ),

    # ---- CPPA Advisory 2024-01 reference removal ----
    # Confirmed wrong: 2024-01 is about data minimization in DSAR
    # processing, not GPC. Per Phil's direction, just remove the
    # reference without adding anything in its place.
    (
        "That is where Meta CAPI fires hashed email, where session replay captures field values, where the CPPA Advisory 2024-01 fact pattern shows up.",
        "That is where Meta CAPI fires hashed email and where session replay captures field values.",
        1,
    ),

    # ---- 'CCPA/CPRA the same analysis applies' bare phrase ----
    # Catch any remaining 'Under CCPA/CPRA' framing in finding plain-text
    # that isn't tied to a specific California-only point.
    # (Skipped for now - most remaining occurrences are in description
    # copy where 'CCPA/CPRA' is genuinely the right specific reference.)
]

for old, new, must_n in POST_FIXES:
    if must_n is None:
        # No assertion - replacement may or may not match in this build
        out = out.replace(old, new)
    else:
        count = out.count(old)
        assert count == must_n, f"POST_FIXES: expected {must_n} occurrence(s) of {old[:80]!r}, found {count}"
        out = out.replace(old, new, must_n)

# Wizard-specific inline assertions
assert "'US State Privacy'" in out, "regs label rewrite did not propagate to wizard"
assert "Docket C-4796" in out, "BetterHelp citation fix did not land in wizard"
assert "CPPA Advisory 2024-01" not in out, "CPPA Advisory reference still in wizard"
assert "most state AGs treat ID-graph" not in out, "ID-graph 'most state AGs' in wizard"
assert "Real-time interception of browser interaction triggers ECPA and CIPA analysis" \
    not in out, "session replay phrase still in wizard"

WIZARD_OUT.write_text(out, encoding="utf-8")
print(f"WIZARD: wrote {len(out):,} chars to {WIZARD_OUT}")


# ============================================================
# CROSS-OUTPUT SANITY CHECK
# ============================================================
def sanity_check_both_outputs(classic_path, wizard_path):
    classic = classic_path.read_text(encoding="utf-8")
    wizard  = wizard_path.read_text(encoding="utf-8")

    def _bad_regs(text):
        return bool(re.search(r"regs: ?\[[^\]]*'CCPA/CPRA'[^\]]*\]", text))

    assert not _bad_regs(classic), "classic: 'CCPA/CPRA' found inside regs array"
    assert not _bad_regs(wizard),  "wizard: 'CCPA/CPRA' found inside regs array"

    for label, text in [("classic", classic), ("wizard", wizard)]:
        assert "CPPA Advisory 2024-01" not in text, \
            f"{label}: CPPA Advisory reference still present"
        assert "Real-time interception of browser interaction triggers ECPA and CIPA analysis" \
            not in text, f"{label}: session replay phrase still present"
        assert "Docket C-4796" in text, \
            f"{label}: BetterHelp citation fix did not land"
        assert "most state AGs treat ID-graph" not in text, \
            f"{label}: ID-graph 'most state AGs' claim still present"
        assert len(text) > 50_000, \
            f"{label}: output suspiciously short ({len(text):,} chars)"
        assert "</html>" in text, \
            f"{label}: HTML not properly closed"

    assert "bzrcdn.openai.com" in wizard, "wizard: OpenAI Ads tracker missing"
    assert "bzrcdn.openai.com" not in classic, \
        "classic: wizard-only tracker leaked"
    assert "wiz-shell" in wizard, "wizard: wizard CSS marker missing"
    assert "wiz-shell" not in classic, \
        "classic: wizard CSS marker leaked"

    print("sanity_check_both_outputs: ALL CHECKS PASSED")


sanity_check_both_outputs(CLASSIC_OUT, WIZARD_OUT)
