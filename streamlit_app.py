import json
import os
import pandas as pd
import streamlit as st
from datetime import date, datetime

DATA_FILE = os.path.join(os.path.dirname(__file__), "events_data.json")

st.set_page_config(
    page_title="CoCo Labs — Pre-Summit Events",
    page_icon=":material/event:",
    layout="wide",
)


@st.cache_data(ttl=60)
def load_events() -> tuple[pd.DataFrame, str]:
    with open(DATA_FILE) as f:
        raw = json.load(f)
    df = pd.DataFrame(raw["events"])
    return df, raw.get("last_updated", "unknown")


def safe_str(val) -> str:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return ""
    return str(val).strip()


def parse_event_date(raw) -> tuple[str, str]:
    if not isinstance(raw, str) or raw.strip() == "" or raw.strip().upper() == "TBD":
        return "TBD", "tbd"
    raw = raw.strip()
    if "(tentative)" in raw.lower():
        clean = raw.lower().replace("(tentative)", "").strip().title()
        return clean, "tentative"
    return raw, "confirmed"


def parse_blast_status(raw, year: int = 2025) -> str:
    if not isinstance(raw, str) or raw.strip() == "":
        return "TBD"
    if "requested" in raw.lower():
        return "Requested"
    if "unlikely" in raw.lower():
        return "Unlikely"
    try:
        dt = datetime.strptime(f"{raw.strip()} {year}", "%B %d %Y")
        return "Sent" if dt.date() <= date.today() else "Upcoming"
    except ValueError:
        return "TBD"


def status_badge(status: str) -> str:
    return {
        "confirmed": ":green[CONFIRMED]",
        "tentative": ":orange[TENTATIVE]",
        "tbd": ":gray[TBD]",
    }.get(status, ":gray[TBD]")


def blast_badge(status: str) -> str:
    return {
        "Sent": "✓ Sent",
        "Upcoming": "⏳ Upcoming",
        "Requested": "📋 Requested",
        "Unlikely": "✗ Unlikely",
        "TBD": "—",
    }.get(status, "—")


# ── Header ────────────────────────────────────────────────────────────────────
with st.container(horizontal=True, vertical_alignment="center"):
    st.markdown("## :material/event: CoCo Labs — Pre-Summit Meetups (May 2025)")
    if st.button(":material/refresh: Refresh", type="tertiary"):
        st.cache_data.clear()
        st.rerun()

df, last_updated = load_events()

try:
    ts = datetime.fromisoformat(last_updated)
    ts_str = ts.strftime("%b %d, %Y %I:%M %p")
except Exception:
    ts_str = last_updated

st.caption(f"Data last synced: **{ts_str}**")
st.divider()

# ── Derived columns ───────────────────────────────────────────────────────────
date_col = "Event Date" if "Event Date" in df.columns else "Date of Event"
df[["event_date_clean", "event_status"]] = df[date_col].apply(
    lambda x: pd.Series(parse_event_date(x))
)
df["registrations_int"] = pd.to_numeric(df["Registrations"], errors="coerce").fillna(0).astype(int)
df["attendance_int"] = pd.to_numeric(df["Attendance"], errors="coerce").fillna(0).astype(int)

# ── KPI Row ───────────────────────────────────────────────────────────────────
total_events = len(df)
confirmed_events = int((df["event_status"] == "confirmed").sum())
total_regs = int(df["registrations_int"].sum())
total_att = int(df["attendance_int"].sum())
att_label = f"{total_att} ({total_att / total_regs * 100:.0f}%)" if total_att > 0 else "Pending"

with st.container(horizontal=True):
    st.metric("Total Events", total_events, border=True)
    st.metric("Confirmed", confirmed_events, border=True)
    st.metric("Total Registrations", total_regs, border=True)
    st.metric("Attendance", att_label, border=True)

st.divider()

# ── Event Cards ───────────────────────────────────────────────────────────────
st.markdown("### Event Details")

cols = st.columns(2)

for i, (_, row) in enumerate(df.iterrows()):
    with cols[i % 2]:
        with st.container(border=True):
            badge = status_badge(row["event_status"])
            st.markdown(f"**{row['Chapter Name']}** &nbsp; {badge}")

            venue = safe_str(row.get("Venue")) or "TBD"
            leader = safe_str(row.get("Chapter Leader")) or "TBD"
            poc = safe_str(row.get("Snowflake SE PoC")) or "TBD"

            c1, c2 = st.columns(2)
            with c1:
                st.markdown(f":material/calendar_today: **Date:** {row['event_date_clean']}")
                st.markdown(f":material/location_on: **Venue:** {venue}")
            with c2:
                st.markdown(f":material/person: **Chapter Lead:** {leader}")
                st.markdown(f":material/badge: **SE POC:** {poc}")

            reg_count = row["registrations_int"]
            att_count = row["attendance_int"]

            if reg_count > 0:
                people_label = f":material/people: **{reg_count}** registered"
                if att_count > 0:
                    rate = att_count / reg_count * 100
                    people_label += f" · **{att_count}** attended ({rate:.0f}%)"
                st.markdown(people_label)
                progress_val = min(att_count / reg_count, 1.0) if att_count > 0 else 0.0
                progress_text = f"Attendance: {att_count}/{reg_count}" if att_count > 0 else "No attendance data yet"
                st.progress(progress_val, text=progress_text)
            else:
                st.markdown(":material/people: :gray[Registrations pending]")

            link_cols = st.columns(2)
            reg_link = safe_str(row.get("Reg link"))
            trial_link = safe_str(row.get("Trial Sign Up Link"))
            with link_cols[0]:
                if reg_link.startswith("http"):
                    st.link_button(":material/open_in_new: Reg Link", reg_link, use_container_width=True)
            with link_cols[1]:
                if trial_link.startswith("http"):
                    st.link_button(":material/science: Trial Link", trial_link, use_container_width=True)

st.divider()

# ── Email Blast Schedule ──────────────────────────────────────────────────────
st.markdown("### Email Blast Schedule")

email_rows = []
for _, row in df.iterrows():
    m1 = safe_str(row.get("Mkto Email 1") or row.get("Marketo Email Blast - 1"))
    m2 = safe_str(row.get("Mkto Email 2") or row.get("Marketo Email Blast - 2"))
    b1 = safe_str(row.get("Bevy Email 1") or row.get("Bevy Email Blast"))
    b2 = safe_str(row.get("Bevy Email 2"))

    email_rows.append({
        "Chapter": row["Chapter Name"],
        "Event Date": row["event_date_clean"],
        "Mkto Email 1": m1 if m1 else "—",
        "Status": blast_badge(parse_blast_status(m1)),
        "Mkto Email 2": m2 if m2 else "—",
        "Status ": blast_badge(parse_blast_status(m2)),
        "Bevy Email 1": b1 if b1 else "—",
        "Status  ": blast_badge(parse_blast_status(b1)),
        "Bevy Email 2": b2 if b2 else "—",
        "Status   ": blast_badge(parse_blast_status(b2)),
    })

email_df = pd.DataFrame(email_rows)

st.dataframe(
    email_df,
    hide_index=True,
    use_container_width=True,
)

st.caption("Status: ✓ Sent · ⏳ Upcoming · 📋 Requested · ✗ Unlikely")
