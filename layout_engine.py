import streamlit as st

def render_dashboard(charts):

    if len(charts)==1:
        st.plotly_chart(charts[0],use_container_width=True)

    elif len(charts)==2:
        c1,c2=st.columns(2)
        c1.plotly_chart(charts[0],use_container_width=True)
        c2.plotly_chart(charts[1],use_container_width=True)

    elif len(charts)>=3:
        c1,c2=st.columns(2)

        c1.plotly_chart(charts[0],use_container_width=True)
        c2.plotly_chart(charts[1],use_container_width=True)

        for chart in charts[2:]:
            st.plotly_chart(chart,use_container_width=True)