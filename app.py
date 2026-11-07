import inspect
import json
import os
from datetime import date, datetime, time, timedelta

import pandas as pd
import plotly.express as px
import streamlit as st

from tracker.analytics import (
    get_dashboard_stats,
    get_monthly_applications,
    get_status_distribution,
    get_upcoming_interviews,
)
from tracker.applications import (
    JOB_TYPES,
    VALID_STATUSES,
    WORK_MODES,
    add_application,
    delete_application,
    filter_applications,
    get_all_applications,
    normalize_salary,
    update_application,
)
from tracker.database import init_db
from tracker.interviews import add_interview, delete_interview, get_interviews
from tracker.seed import seed_demo_data
from views.compare import render_compare_page

init_db()  # create tables on first run (needed on a fresh clone)
if os.getenv("JOB_TRACKER_DEMO") == "1":
    seed_demo_data()  # live-demo mode: start with sample data

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="CareerTrack | Job Tracker", page_icon="💼", layout="wide",
                   initial_sidebar_state="expanded")

# --- SESSION STATE INITIALIZATION ---
# بنخزن هنا حالة الزرار عشان نعرف إنت دوست على أي كارت
if 'view_details' not in st.session_state:
    st.session_state.view_details = None

# --- CLEAN MODERN CSS ---
st.markdown("""
<style>
    .block-container { padding-top: 2.5rem; max-width: 1280px; }
    .main-title { font-size: 32px; font-weight: 800; letter-spacing: -0.5px; margin-bottom: 2px; }
    .subtitle { opacity: 0.65; font-size: 15px; margin-bottom: 22px; }
    .section-header { font-size: 18px; font-weight: 700; margin: 18px 0 12px; }

    /* neutral until the page detects its real theme (see THEME_SYNC_JS), then explicit colours */
    [data-testid="stMetric"], div[data-testid="stExpander"] {
        background: rgba(128, 128, 128, 0.08);
        border: 1px solid rgba(128, 128, 128, 0.25);
        border-radius: 12px;
    }
    html[data-card-theme="light"] [data-testid="stMetric"],
    html[data-card-theme="light"] div[data-testid="stExpander"] { background: #FFFFFF; border-color: #E3E6F0; }
    html[data-card-theme="dark"] [data-testid="stMetric"],
    html[data-card-theme="dark"] div[data-testid="stExpander"] { background: #171C28; border-color: #262D3D; }
    [data-testid="stMetric"] { padding: 16px 20px; }
    [data-testid="stMetricValue"] { font-weight: 700; }
    div[data-testid="stExpander"] { margin-bottom: 10px; }
    div[data-testid="stExpander"] p { font-size: 14px; font-weight: 600; }
    .stButton > button, .stDownloadButton > button { font-weight: 600; }
</style>
""", unsafe_allow_html=True)

# Live thousands separators in every "Salary" box: 90000 -> 90,000 while typing.
# Runs inside the page itself (installed once), so it survives Streamlit reruns.
SALARY_FORMATTER_JS = r"""
(function () {
  if (window.__salaryFmt) return; window.__salaryFmt = true;
  const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
  document.addEventListener('input', function (e) {
    const el = e.target;
    if (!el || el.tagName !== 'INPUT' || el.getAttribute('aria-label') !== 'Salary') return;
    const raw = el.value;
    const formatted = raw.replace(/[\d,]+/g, function (m) {
      return m.replace(/,/g, '').replace(/\B(?=(\d{3})+(?!\d))/g, ',');
    });
    if (formatted === raw) return;
    const caret = el.selectionStart;
    const digitsBefore = raw.slice(0, caret).replace(/\D/g, '').length;
    setter.call(el, formatted);
    el.dispatchEvent(new Event('input', { bubbles: true }));
    let pos = 0, seen = 0;
    while (pos < formatted.length && seen < digitsBefore) { if (/\d/.test(formatted[pos])) seen++; pos++; }
    el.setSelectionRange(pos, pos);
  }, true);
})();
"""

THEME_SYNC_JS = r"""
(function () {
  if (window.__themeSync) return; window.__themeSync = true;
  function sync() {
    const app = document.querySelector('.stApp');
    const rgb = app && getComputedStyle(app).backgroundColor.match(/\d+/g);
    if (!rgb) return;
    const luminance = 0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2];
    document.documentElement.dataset.cardTheme = luminance < 128 ? 'dark' : 'light';
  }
  sync();
  setInterval(sync, 300);
})();
"""


def run_js(code):
    """Run JavaScript inside the app page (the Streamlit API for this differs between versions)."""
    if "unsafe_allow_javascript" in inspect.signature(st.html).parameters:
        st.html("<script>" + code + "</script>", unsafe_allow_javascript=True)
    else:  # older Streamlit: install the same script into the page from a hidden iframe
        import streamlit.components.v1 as components

        components.html(
            "<script>const t = window.parent.document.createElement('script');"
            "t.textContent = " + json.dumps(code) + ";"
            "window.parent.document.head.appendChild(t);</script>", height=0)


run_js(SALARY_FORMATTER_JS)
run_js(THEME_SYNC_JS)

# --- SIDEBAR ---
with st.sidebar:
    st.markdown("## 💼 CareerTrack")
    st.caption("Track your software engineering journey.")
    st.divider()
    page = st.radio(
        "Navigation",
        ["📊 Dashboard", "📋 My Jobs Board", "⚖️ Compare", "⚙️ Add & Manage"],
        label_visibility="collapsed",
    )
    st.divider()

    st.markdown("### 📥 Export Data")
    all_apps = get_all_applications()
    if all_apps:
        df_export = pd.DataFrame(all_apps)
        csv = df_export.to_csv(index=False).encode('utf-8')
        st.download_button(label="Download CSV", data=csv, file_name=f"My_Applications_{date.today()}.csv",
                           mime="text/csv", width="stretch")

    st.divider()
    st.caption("Built with Python & SQLite")


def format_number(value): return value or 0


def get_status_color(status):
    colors = {"Applied": "#3b82f6", "Assessment": "#f59e0b", "Interview": "#8b5cf6", "Offer": "#10b981",
              "Rejected": "#ef4444", "Withdrawn": "#64748b"}
    return colors.get(status, "#94a3b8")


# --- DASHBOARD PAGE ---
if page == "📊 Dashboard":
    st.markdown('<div class="main-title">Analytics Dashboard</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Overview of your job search progress and upcoming interviews.</div>',
                unsafe_allow_html=True)

    # --- SMART NOTIFICATIONS (Reminders) ---
    upcoming = get_upcoming_interviews()
    now = datetime.now()
    has_alerts = False

    if upcoming:
        for intv in upcoming:
            try:
                intv_date = datetime.fromisoformat(intv['interview_date'])
                time_diff = intv_date - now

                # If interview is today or tomorrow (within 48 hours)
                if timedelta(days=0) <= time_diff <= timedelta(days=2):
                    has_alerts = True
                    date_str = intv_date.strftime('%B %d, %Y at %I:%M %p')
                    st.info(
                        f"**Reminder:** You have a **{intv['interview_type']} Interview** "
                        f"with **{intv['company']}** coming up on {date_str}!",
                        icon="⏰")
                    st.toast(f"Upcoming interview with {intv['company']}!", icon="🔔")
            except Exception:
                pass

    if has_alerts:
        st.markdown("<br>", unsafe_allow_html=True)

    stats = get_dashboard_stats()

    # --- INTERACTIVE METRICS CARDS ---
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Total Applications", format_number(stats["total_applications"]))
        if st.button("🔍 View All", key="btn_all", width="stretch"):
            st.session_state.view_details = "All"

    with c2:
        st.metric("Interviews", format_number(stats["interviews"]))
        if st.button("🔍 View Interviews", key="btn_int", width="stretch"):
            st.session_state.view_details = "Interview"

    with c3:
        st.metric("Job Offers", format_number(stats["offers"]))
        if st.button("🔍 View Offers", key="btn_off", width="stretch"):
            st.session_state.view_details = "Offer"

    with c4:
        st.metric("Response Rate", f'{stats["response_rate"]}%')
        if st.button("🔍 View Responses", key="btn_res", width="stretch"):
            st.session_state.view_details = "Responses"

    # --- DYNAMIC DETAILS SECTION ---
    if st.session_state.view_details:
        st.markdown(f"### 📑 Details: {st.session_state.view_details}")
        apps_data = get_all_applications()

        if st.session_state.view_details == "All":
            filtered_data = apps_data
        elif st.session_state.view_details == "Interview":
            filtered_data = [a for a in apps_data if a['status'] == 'Interview']
        elif st.session_state.view_details == "Offer":
            filtered_data = [a for a in apps_data if a['status'] == 'Offer']
        elif st.session_state.view_details == "Responses":
            # Companies that actually responded (not just 'Applied')
            filtered_data = [a for a in apps_data if a['status'] in ['Assessment', 'Interview', 'Offer', 'Rejected']]

        if filtered_data:
            df_filtered = pd.DataFrame(filtered_data)[['company', 'job_title', 'status', 'applied_date', 'location']]
            st.dataframe(
                df_filtered,
                width="stretch",
                hide_index=True,
                column_config={
                    "company": "Company", "job_title": "Position", "status": "Status",
                    "applied_date": "Date", "location": "Location"
                }
            )
        else:
            st.info(f"No applications found for category: {st.session_state.view_details}")

        if st.button("❌ Close Details", type="secondary"):
            st.session_state.view_details = None
            st.rerun()

    st.divider()

    # Upcoming Interviews Table
    st.markdown('<div class="section-header">📅 Upcoming Interviews</div>', unsafe_allow_html=True)
    if upcoming:
        df_up = pd.DataFrame(upcoming)
        df_up["interview_date"] = pd.to_datetime(df_up["interview_date"]).dt.strftime("%b %d, %Y  %I:%M %p")
        st.dataframe(df_up, width="stretch", hide_index=True,
                     column_config={"id": None, "interview_date": "Date & Time", "company": "Company",
                                    "job_title": "Position", "interview_type": "Type",
                                    "meeting_link": st.column_config.LinkColumn("Link")})
    else:
        st.info("No upcoming interviews right now. Keep applying!")

    st.divider()

    # Charts
    left, right = st.columns(2)
    with left:
        st.markdown('<div class="section-header">Application Status</div>', unsafe_allow_html=True)
        dist = get_status_distribution()
        if dist:
            df_dist = pd.DataFrame(dist)
            fig = px.pie(df_dist, names="status", values="count", hole=0.6, color="status",
                         color_discrete_map={s: get_status_color(s) for s in VALID_STATUSES})
            fig.update_layout(margin=dict(t=20, b=20, l=20, r=20), paper_bgcolor="rgba(0,0,0,0)",
                              plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig, width="stretch")
        else:
            st.info("Add applications to see charts.")

    with right:
        st.markdown('<div class="section-header">Timeline</div>', unsafe_allow_html=True)
        monthly = get_monthly_applications()
        if monthly:
            fig2 = px.bar(pd.DataFrame(monthly), x="month", y="total", text="total")
            fig2.update_traces(marker_color="#6366F1")
            fig2.update_layout(margin=dict(t=20, b=20, l=20, r=20), paper_bgcolor="rgba(0,0,0,0)",
                               plot_bgcolor="rgba(0,0,0,0)", xaxis_title="", yaxis_title="")
            st.plotly_chart(fig2, width="stretch")

# --- KANBAN BOARD PAGE ---
elif page == "📋 My Jobs Board":
    st.markdown('<div class="main-title">My Jobs Board</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Move a card to another stage with its selector.</div>',
                unsafe_allow_html=True)


    def move_card(app_id, key):
        update_application(app_id, status=st.session_state[key])


    f1, f2 = st.columns([2, 3])
    query = f1.text_input("Search", placeholder="Company, title, location or notes")
    shown = f2.multiselect("Stages", VALID_STATUSES, default=VALID_STATUSES)

    apps = filter_applications(get_all_applications(), query, shown)
    if not apps:
        st.info("No applications match. Add one in 'Add & Manage' or clear the filters.")
    elif shown:
        for col, status in zip(st.columns(len(shown)), [s for s in VALID_STATUSES if s in shown]):
            with col:
                col_apps = [a for a in apps if a["status"] == status]
                st.markdown(
                    f'<div style="border-top:4px solid {get_status_color(status)};padding-top:6px;'
                    f'font-weight:700">{status} ({len(col_apps)})</div>', unsafe_allow_html=True)
                for a in col_apps:
                    with st.expander(f"{a['company']} | {a['job_title']}"):
                        st.markdown(f"**Date:** {a['applied_date']}")
                        st.markdown(f"**Location:** {a['location'] or 'N/A'} ({a['work_mode'] or 'N/A'})")
                        if a["salary"]:
                            st.markdown(f"**Salary:** {normalize_salary(a['salary'])}")
                        if a["job_url"]:
                            st.markdown(f"[View job posting]({a['job_url']})")
                        if a["notes"]:
                            st.markdown(f"**Notes:** {a['notes']}")
                        key = f"mv_{a['id']}"
                        st.selectbox("Move to", VALID_STATUSES, index=VALID_STATUSES.index(a["status"]),
                                     key=key, on_change=move_card, args=(a["id"], key))

# --- ADD & MANAGE PAGE ---
elif page == "⚖️ Compare":
    render_compare_page()

elif page == "⚙️ Add & Manage":
    st.markdown('<div class="main-title">Workspace</div>', unsafe_allow_html=True)

    tab_add, tab_manage = st.tabs(["➕ Add New Application", "🛠️ Edit & Interviews"])

    # ADD TAB
    with tab_add:
        with st.form("add_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                company = st.text_input("Company Name *")
                job_title = st.text_input("Job Title *")
                location = st.text_input("Location")
                job_type = st.selectbox("Job Type", JOB_TYPES)
            with c2:
                work_mode = st.selectbox("Work Mode", WORK_MODES)
                salary = st.text_input("Salary", placeholder="e.g. 90000 or 15,000 - 20,000 EGP")
                job_url = st.text_input("Job Link URL")
                status = st.selectbox("Status", VALID_STATUSES)

            applied_date = st.date_input("Applied Date", value=date.today())
            notes = st.text_area("Notes")

            if st.form_submit_button("Save Application", type="primary"):
                if not company.strip() or not job_title.strip():
                    st.error("Company and Title are required.")
                else:
                    add_application(company=company, job_title=job_title, applied_date=applied_date.isoformat(),
                                    location=location, job_type=job_type, work_mode=work_mode, salary=salary,
                                    job_url=job_url, status=status, notes=notes)
                    st.success("Added successfully!")
                    st.rerun()

    # MANAGE TAB
    with tab_manage:
        apps = get_all_applications()
        if apps:
            app_options = {f"{a['company']} - {a['job_title']}": a for a in apps}
            sel_label = st.selectbox("Select an application:", list(app_options.keys()))
            sel_app = app_options[sel_label]
            app_id = sel_app["id"]

            st.divider()

            c_edit, c_intv = st.columns(2, gap="large")
            with c_edit:
                st.markdown("#### Edit Details")


                def _idx(options, value):
                    return options.index(value) if value in options else 0


                with st.form(f"edit_form_{app_id}"):
                    e_comp = st.text_input("Company", value=sel_app["company"])
                    e_title = st.text_input("Title", value=sel_app["job_title"])
                    e_loc = st.text_input("Location", value=sel_app["location"] or "")
                    e_type = st.selectbox("Job Type", JOB_TYPES, index=_idx(JOB_TYPES, sel_app["job_type"]))
                    e_mode = st.selectbox("Work Mode", WORK_MODES, index=_idx(WORK_MODES, sel_app["work_mode"]))
                    e_salary = st.text_input("Salary", value=normalize_salary(sel_app["salary"]) or "")
                    e_url = st.text_input("Job Link URL", value=sel_app["job_url"] or "")
                    e_status = st.selectbox("Status", VALID_STATUSES, index=VALID_STATUSES.index(sel_app["status"]))
                    e_date = st.date_input("Applied Date", value=date.fromisoformat(sel_app["applied_date"]))
                    e_notes = st.text_area("Notes", value=sel_app["notes"] or "")

                    if st.form_submit_button("Save changes", type="primary"):
                        try:
                            update_application(
                                app_id, company=e_comp, job_title=e_title, location=e_loc, job_type=e_type,
                                work_mode=e_mode, salary=e_salary, job_url=e_url, status=e_status,
                                applied_date=e_date.isoformat(), notes=e_notes)
                            st.rerun()
                        except ValueError as err:
                            st.error(str(err))

                confirm = st.checkbox("I want to delete this application", key=f"confirm_del_{app_id}")
                if st.button("Delete application", disabled=not confirm):
                    delete_application(app_id)
                    st.rerun()

            with c_intv:
                st.markdown("#### 📅 Schedule Interview")
                with st.form("intv_form"):
                    i_date = st.date_input("Date")
                    i_time = st.time_input("Time", value=time(12, 0))
                    i_type = st.selectbox("Type", ["HR", "Technical", "Manager", "Final"])
                    i_link = st.text_input("Link")
                    if st.form_submit_button("Book Interview"):
                        dt_str = datetime.combine(i_date, i_time).isoformat()
                        add_interview(application_id=app_id, interview_date=dt_str, interview_type=i_type,
                                      meeting_link=i_link)
                        st.rerun()

                interviews = get_interviews(app_id)
                if interviews:
                    st.write("Current Interviews:")
                    for iv in interviews:
                        t_col, d_col = st.columns([4, 1])
                        t_col.write(f"{iv['interview_date'].replace('T', ' ')[:16]} - {iv['interview_type']}")
                        if d_col.button("Delete", key=f"del_iv_{iv['id']}"):
                            delete_interview(iv["id"])
                            st.rerun()
        else:
            st.info("No applications to manage.")