"""Compare page: put offers (or interview-stage jobs) side by side."""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from tracker.comparison import CRITERIA, build_comparison, get_highlights, save_ratings

POOLS = {
    "Offers": ["Offer"],
    "Interview stage": ["Interview"],
    "Offers + Interview stage": ["Offer", "Interview"],
}
SORTS = {"Overall score": "overall_score", "Salary": "salary_value", "Fit score": "fit_score"}


def _card(title, item, detail):
    with st.container(border=True):
        st.caption(title)
        if item is None:
            st.markdown("**-**")
            st.caption("Not enough data yet")
        else:
            st.markdown(f"**{item['company']}**")
            st.caption(f"{item['job_title']} | {detail}")


def _badges(item, top):
    labels = {"top_salary": "💰 Highest salary", "best_fit": "⭐ Best fit", "top_overall": "🎯 Top pick"}
    return ", ".join(text for key, text in labels.items() if top[key] and top[key]["id"] == item["id"])


def render_compare_page():
    st.markdown('<div class="main-title">Compare</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="subtitle">Put your best options side by side: salary, location and how well each fits you.</div>',
        unsafe_allow_html=True)

    col_pool, col_weight = st.columns([3, 2])
    pool = col_pool.radio("Compare", list(POOLS), horizontal=True)
    weight = col_weight.slider("Salary importance (%)", 0, 100, 50, step=10,
                               help="0% ranks by fit only, 100% by salary only. The overall score needs both a "
                                    "salary and your ratings (unless one of them has 0% weight).")

    items = build_comparison(POOLS[pool], weight / 100)
    if not items:
        st.info("Nothing to compare yet. Move applications to 'Offer' or 'Interview' on the board.")
        return

    top = get_highlights(items)
    cards = st.columns(3)
    with cards[0]:
        _card("Highest salary", top["top_salary"], top["top_salary"]["salary"] if top["top_salary"] else "")
    with cards[1]:
        _card("Best fit", top["best_fit"], f"{top['best_fit']['fit_score']:.1f} / 5" if top["best_fit"] else "")
    with cards[2]:
        _card("Top pick overall", top["top_overall"],
              f"{top['top_overall']['overall_score']:.0f} / 100" if top["top_overall"] else "")

    sort_key = SORTS[st.selectbox("Sort by", list(SORTS))]
    ordered = sorted(items, key=lambda i: (i[sort_key] is None, -(i[sort_key] or 0), i["company"].lower()))
    rows = [{
        "Company": i["company"], "Position": i["job_title"], "Stage": i["status"],
        "Location": i["location"] or "-", "Work mode": i["work_mode"] or "-", "Salary": i["salary"] or "-",
        "Fit (1-5)": f"{i['fit_score']:.1f}" if i["fit_score"] is not None else "not rated",
        "Overall": f"{i['overall_score']:.0f}/100" if i["overall_score"] is not None else "-",
        "Highlights": _badges(i, top), "Link": i["job_url"] or "",
    } for i in ordered]
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch",
                 column_config={"Link": st.column_config.LinkColumn("Job link", display_text="Open")})

    left, right = st.columns(2)
    priced = [i for i in ordered if i["salary_value"] is not None]
    rated = [i for i in ordered if i["ratings"]]
    with left:
        st.markdown('<div class="section-header">Salary</div>', unsafe_allow_html=True)
        if priced:
            fig = go.Figure(go.Bar(
                x=[i["company"] for i in priced], y=[i["salary_value"] for i in priced], marker_color="#6366F1",
                text=[f"{i['salary_value']:,.0f}" for i in priced], textposition="outside"))
            fig.update_layout(height=320, margin={"l": 10, "r": 10, "t": 20, "b": 10})
            st.plotly_chart(fig, width="stretch")
        else:
            st.info("No salaries yet. Add them in 'Add & Manage'.")
    with right:
        st.markdown('<div class="section-header">Fit profile</div>', unsafe_allow_html=True)
        if rated:
            labels = list(CRITERIA.values())
            fig = go.Figure()
            for i in rated:
                values = [i["ratings"][k] for k in CRITERIA]
                fig.add_trace(go.Scatterpolar(r=values + values[:1], theta=labels + labels[:1],
                                              name=i["company"], fill="toself", opacity=0.55))
            fig.update_layout(polar={"radialaxis": {"range": [0, 5], "visible": True}}, height=320,
                              margin={"l": 50, "r": 50, "t": 20, "b": 10}, legend={"orientation": "h", "y": -0.1})
            st.plotly_chart(fig, width="stretch")
        else:
            st.info("Rate your options below to compare how well each one fits you.")

    st.markdown('<div class="section-header">Rate your options</div>', unsafe_allow_html=True)
    st.caption("1 = poor, 5 = great. Your ratings drive the fit score and the overall score.")
    for i in ordered:
        with st.expander(f"{i['company']} | {i['job_title']}"):
            with st.form(f"rate_form_{i['id']}"):
                scores = {}
                for col, (name, label) in zip(st.columns(len(CRITERIA)), CRITERIA.items()):
                    current = (i["ratings"] or {}).get(name, 3)
                    scores[name] = col.slider(label, 1, 5, current, key=f"rate_{i['id']}_{name}")
                if st.form_submit_button("Save ratings"):
                    save_ratings(i["id"], **scores)
                    st.rerun()
