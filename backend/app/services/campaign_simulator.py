"""
AXonic — Campaign Simulator (Rule-Based Fallback)
Used when Groq/LLM is unavailable.
Produces believable events from campaign parameters alone.
"""

import random
import logging

logger = logging.getLogger("axonic.campaign_simulator")


def simulate(campaign: dict) -> list:
    """
    Generate 3 simulation rounds using deterministic rules.
    Fast, free, no API calls. Used as fallback or for demo mode.
    """
    platform = campaign.get("platform", "Instagram")
    tone     = campaign.get("tone",     "Inspirational")
    audience = campaign.get("audience", "Indian consumers")
    name     = campaign.get("name",     "the campaign")

    # ── Round 1: Launch ───────────────────────────────────────────────────────
    initial_reach = random.randint(8000, 18000)
    round1 = {
        "round":     1,
        "event":     f"'{name}' launched on {platform} targeting {audience}. "
                     f"Initial impressions started accumulating across metro pin codes.",
        "metric":    f"Reach: {initial_reach:,} in first 6 hours | Impressions: {initial_reach * 3:,}",
        "sentiment": "neutral",
    }

    # ── Round 2: Reaction (tone-based) ───────────────────────────────────────
    tone_reactions = {
        "Aggressive": (
            f"Hard-sell messaging triggered scepticism among {audience}. "
            "Several users flagged the content as overly promotional.",
            f"Negative comment rate: 12% | Trust score dropped 9 points | CTR: 1.8%",
            "negative",
        ),
        "Inspirational": (
            f"The aspirational narrative resonated deeply with {audience}. "
            "Save and share rate spiked within the first 48 hours.",
            f"Save rate: 4.2× above benchmark | Shares: {random.randint(3000, 7000):,} | Avg watch time: 38 sec",
            "positive",
        ),
        "Informational": (
            f"Content-heavy posts generated high bookmark rates among {audience}. "
            "Immediate conversion was low but audience quality was excellent.",
            f"Bookmark rate: 8.7% | Time-on-page: 2 min 14 sec | Bounce rate: 31%",
            "neutral",
        ),
        "Emotional": (
            f"Emotional storytelling triggered a sharing wave within community groups. "
            "Family WhatsApp and Facebook groups were the primary amplification vectors.",
            f"Organic reach: +280% | Shares via WhatsApp: {random.randint(1200, 4000):,} | Sentiment: 91% positive",
            "positive",
        ),
        "Humorous": (
            f"Meme remixes of the campaign appeared on Twitter within 36 hours. "
            "User-generated content extended reach without additional spend.",
            f"UGC pieces: {random.randint(40, 150):,} | Earned media estimated: ₹{random.randint(150, 400)}K | Virality score: 7.4/10",
            "positive",
        ),
    }
    r2_event, r2_metric, r2_sentiment = tone_reactions.get(
        tone,
        (
            f"Mixed engagement from {audience}. Core demographic responded above average.",
            f"Engagement rate: 3.4% | Reach growth: +{random.randint(20, 60)}%",
            "mixed",
        ),
    )
    round2 = {"round": 2, "event": r2_event, "metric": r2_metric, "sentiment": r2_sentiment}

    # ── Round 3: Spread / Decay (platform-based) ─────────────────────────────
    platform_outcomes = {
        "Instagram": (
            f"Instagram Reels algorithm surfaced '{name}' to non-followers. "
            f"Three micro-influencers (50K–200K) independently reshared the content.",
            f"Total reach: {random.randint(120000, 250000):,} | Follower growth: +{random.randint(800, 3000):,} | ROI: {random.uniform(2.8, 5.1):.1f}×",
            "positive",
        ),
        "Twitter": (
            f"A campaign-related hashtag entered the top-15 trending in the target region. "
            "News journalists picked up the story adding earned media reach.",
            f"Hashtag impressions: {random.randint(500000, 1200000):,} | Media pickups: {random.randint(3, 9)} | Share of voice: 22%",
            "positive",
        ),
        "LinkedIn": (
            f"Four industry leaders reshared the post with personal commentary. "
            "Three inbound partnership queries received within the week.",
            f"Post impressions: {random.randint(30000, 80000):,} | Profile visits: +{random.randint(400, 1200):,} | Leads generated: {random.randint(8, 25)}",
            "positive",
        ),
        "WhatsApp": (
            f"A forward chain spread across family groups and interest communities. "
            f"Message reached six degrees of separation from the original send list.",
            f"Estimated forwards: {random.randint(5000, 20000):,} | New audience reached: {random.randint(50000, 150000):,} | Cost-per-reach: ₹0.00",
            "positive",
        ),
        "YouTube": (
            f"Algorithm recommended the video to non-subscribers in the target demographic. "
            "Average watch time climbed, signalling strong content-audience fit.",
            f"Views: {random.randint(40000, 120000):,} | Watch time per session: +3.8 min | Subscriber gain: {random.randint(300, 1500):,}",
            "positive",
        ),
    }
    r3_event, r3_metric, r3_sentiment = platform_outcomes.get(
        platform,
        (
            f"Organic spread continued on {platform}. Audience retention remained above category benchmark.",
            f"Total unique reach: {random.randint(50000, 120000):,} | Cost-per-result: ₹{random.uniform(2.0, 6.5):.2f}",
            "positive",
        ),
    )
    round3 = {"round": 3, "event": r3_event, "metric": r3_metric, "sentiment": r3_sentiment}

    logger.info(f"[RuleSimulator] Generated 3 events for campaign: {name}")
    return [round1, round2, round3]
