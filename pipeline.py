"""Orchestrates: discover -> enrich -> AI qualify -> DataFrame."""
import time, pandas as pd
from sources import osm
from enrich import website, social
from ai import gemini

def run(place, category, limit=50, radius_km=0, enrich=True, use_ai=True, progress=lambda i, n, m: None):
    leads = osm.search(place, category, limit, radius_km)
    for i, lead in enumerate(leads):
        progress(i, len(leads), lead["name"])
        if enrich:
            if lead["website"]:
                extra = website.scrape(lead["website"])
                for k, v in extra.items():
                    if v and not lead.get(k):
                        lead[k] = v
            elif not (lead["facebook"] and lead["instagram"]):
                for k, v in social.find_social(lead["name"], lead["city"]).items():
                    lead[k] = lead.get(k) or v
            time.sleep(1)  # be polite
        if use_ai:
            lead.update(gemini.analyze(lead))
            time.sleep(4)  # stay inside free-tier rate limits
    df = pd.DataFrame(leads)
    if "ai_score" in df:
        df = df.sort_values("ai_score", ascending=False, na_position="last")
    return df
