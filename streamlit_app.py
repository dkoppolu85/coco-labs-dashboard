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


@st.cache_data
def load_events() -> tuple[pd.DataFrame, str]:
    with open(DATA_FILE) as f:
        raw = json.load(f)
    df = pd.DataFrame(raw["events"])
    return df, raw.get("last_updated", "unknown")


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
        "TBD": "— TBD",
    }.get(status, "— TBD")


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

st.caption(
    f"Data last synced: **{ts_str}** · "
    "To pull fresh data from Google Sheets, run: `python3 refresh_data.py`"
)
st.divider()

# ── Derived columns ───────────────────────────────────────────────────────────
df[["event_date_clean", "event_status"]] = df["Date of Event"].apply(
    lambda x: pd.Series(parse_event_date(x))
)
df["registrations_int"] = pd.to_numeric(df["Registrations"], errors="coerce").fillna(0).astype(int)
df["attendance_int"] = pd.to_numeric(df["Attendance"], errors="coerce").fillna(0).astype(int)

# ── KPI Row ───────────────────────────────────────────────────────────────────
total_events = len(df)
confirmed_events = int((df["event_status"] == "confirmed").sum())
total_regs = int(df["registrations_int"].sum())
total_att = int(df["attendance_int"].sum())
att_rate = (total_att / total_regs * 100) if total_regs > 0 else 0
att_label = f"{total_att} ({att_rate:.0f}%)" if total_att > 0 else "Pending"

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

            venue = row["Venue"] if isinstance(row["Venue"], str) and row["Venue"].strip() else "TBD"
            leader = row["Chapter Leader"] if isinstance(row["Chapter Leader"], str) else "TBD"
            poc = row["Snowflake SE PoC"] if isinstance(row["Snowflake SE PoC"], str) else "TBD"

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

            reg_link = row.get("Reg link")
            if isinstance(reg_link, str) and reg_link.strip().startswith("http"):
                st.link_button(
                    ":material/open_in_new: Registration Link",
                    reg_link,
                    use_container_width=True,
                )

st.divider()

# ── Email Blast Schedule ──────────────────────────────────────────────────────
st.markdown("### Email Blast Schedule")

email_rows = []
for _, row in df.iterrows():
    m1 = row.get("Marketo Email Blast - 1") or ""
    m2 = row.get("Marketo Email Blast - 2") or ""
    bevy = row.get("Bevy Email Blast") or ""

    email_rows.append({
        "Chapter": row["Chapter Name"],
        "Event Date": row["event_date_clean"],
        "Marketo Blast 1": str(m1).strip() if m1 else "—",
        "Blast 1 Status": blast_badge(parse_blast_status(m1)),
        "Marketo Blast 2": str(m2).strip() if m2 else "—",
        "Blast 2 Status": blast_badge(parse_blast_status(m2)),
        "Bevy Blast": str(bevy).strip() if bevy else "—",
        "Bevy Status": blast_badge(parse_blast_status(bevy)),
    })

email_df = pd.DataFrame(email_rows)

st.dataframe(
    email_df,
    hide_index=True,
    use_container_width=True,
    column_config={
        "Chapter": st.column_config.TextColumn("Chapter", width="medium"),
        "Event Date": st.column_config.TextColumn("Event Date", width="medium"),
        "Marketo Blast 1": st.column_config.TextColumn("Marketo Blast 1", width="small"),
        "Blast 1 Status": st.column_config.TextColumn("", width="small"),
        "Marketo Blast 2": st.column_config.TextColumn("Marketo Blast 2", width="small"),
        "Blast 2 Status": st.column_config.TextColumn("", width="small"),
        "Bevy Blast": st.column_config.TextColumn("Bevy Blast", width="small"),
        "Bevy Status": st.column_config.TextColumn("", width="small"),
    },
)

st.caption("Blast status is derived from today's date. Run `python3 refresh_data.py` to sync latest data from Google Sheets.")
