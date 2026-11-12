import calendar
import html
import io
import os
from datetime import datetime, timedelta
import xml.dom.minidom
import xml.etree.ElementTree as ET

import pandas as pd
import streamlit as st
from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

# Page Configuration
st.set_page_config(
    page_title="Learn@TLC - Training Calendar & XML Suite",
    page_icon="📅",
    layout="wide"
)

PERSISTED_DATA_FILE = "saved_schedule_state.csv"
DEFAULT_DESC_FILE = "class_desc.csv"
BANNER_FILE = "LearnTLC_.png"

# Built-in Course Descriptions Lookup
DEFAULT_DESCRIPTIONS = {
    "CapCentral": "Discover how to navigate the CapCentral website to quickly access the latest legislative information. View legislative calendars, committee hearings agendas, bill details, your LMS bill tracks and CMS stats, and live chamber and committee videos. (1 hr.)",
    "CapCentral-Committee": "Discover how to navigate the CapCentral website to quickly access the latest legislative information. View legislative calendars, committee hearings agendas, bill details, your LMS bill tracks and CMS stats, and live chamber and committee videos. (1 hr.)",
    "CapCentral-House": "Discover how to navigate the CapCentral website to quickly access the latest legislative information. View legislative calendars, committee hearings agendas, bill details, your LMS bill tracks and CMS stats, and live chamber and committee videos. (1 hr.)",
    "CapCentral-Senate": "Discover how to navigate the CapCentral website to quickly access the latest legislative information. View legislative calendars, committee hearings agendas, bill details, your LMS bill tracks and CMS stats, and live chamber and committee videos. (1 hr.)",
    "CMS": "CMS introduces you to the features in the Correspondence Management System (CMS), including storing and searching for contact and incoming and outgoing correspondence information, saving email from Outlook to CMS, multiple entry, combining contact records, mass updates, creating, updating, and resolving casework, and creating mail and email merges and reports. (2 hrs.)",
    "LDR": "The Legislative Draft Request (LDR) system is an internal website that allows members and committees to request legislative drafts, access information about draft requests made by their office, and view completed draft text. Learn how to review information on the home page, create a new request, view office drafts reports, and manage office security. (1 hr.)",
    "LDR-House": "The Legislative Draft Request (LDR) system is an internal website that allows members and committees to request legislative drafts, access information about draft requests made by their office, and view completed draft text. Learn how to review information on the home page, create a new request, view office drafts reports, and manage office security. (1 hr.)",
    "LDR-Senate": "The Legislative Draft Request (LDR) system is an internal website that allows members and committees to request legislative drafts, access information about draft requests made by their office, and view completed draft text. Learn how to review information on the home page, create a new request, view office drafts reports, and manage office security. (1 hr.)",
    "LMS": "LMS (Legislative Management System) allows legislative analysts to track the movement of bills and store comments and bill information. In this class, create bill tracks, bill lists, and searches, customize folders, perform mass updates, and generate custom reports with recommendations, comments, and statistical data. (2 hrs.)",
    "LMS-House": "LMS (Legislative Management System) allows legislative analysts to track the movement of bills and store comments and bill information. In this class, create bill tracks, bill lists, and searches, customize folders, perform mass updates, and generate custom reports with recommendations, comments, and statistical data. (2 hrs.)",
    "LMS-Senate": "LMS (Legislative Management System) allows legislative analysts to track the movement of bills and store comments and bill information. In this class, create bill tracks, bill lists, and searches, customize folders, perform mass updates, and generate custom reports with recommendations, comments, and statistical data. (2 hrs.)",
    "LMS-Committee": "LMS (Legislative Management System) allows legislative analysts to track the movement of bills and store comments and bill information. In this class, create bill tracks, bill lists, and searches, customize folders, perform mass updates, and generate custom reports with recommendations, comments, and statistical data. (2 hrs.)",
    "Texas Legislative Apps": "Attendees will gain a foundational understanding of the Texas Legislative Information Systems (TLIS), Legislative Management System (LMS), Correspondence Management System (CMS), Legislative Draft Request (LDR), CapCentral, and Office 365 applications. The session will also cover the technical environment in which these tools operate, including system access, navigation, and basic troubleshooting tips.",
    "TLIS": "TLIS introduces you to the features of the Texas Legislative Information System. Discover the different ways to access and search for bill information using the Bill Lookup, Bill Search, Text Search, Drilldown Bill Search, and Witness List Search features. Find how to view reports, calendar and agenda items, committee meetings and minutes, and use the My TLIS features to create watch lists and set bill alerts to track the actions on bills. (2 hr.)",
    "Making Word Docs Accessible": "Prepare your Word documents for accessible PDF export. This class covers the best practices for structuring and formatting your Word documents to ensure they are accessible from the start, saving you time and effort."
}

# 1. Custom Brand Banner
if os.path.exists(BANNER_FILE):
    st.image(BANNER_FILE, use_container_width=True)
else:
    st.title("📅 Learn @ TLC")
    st.subheader("Training Calendar & Orchard XML Automation Suite")

st.markdown("---")


# 2. Data Transformation Engine (Adobe Report -> Unified DataFrame)
def format_12hr(dt_obj: datetime) -> str:
    """Formats a datetime object to a clean 12-hour string (e.g., 2:00 PM)."""
    return dt_obj.strftime("%I:%M %p").lstrip("0")


def parse_uploaded_schedule(file_source, desc_dict: dict) -> pd.DataFrame:
    """Transforms raw Adobe Learning Manager CSV (or pre-formatted CSV) into unified schedule records."""
    raw_df = pd.read_csv(file_source)

    # Case 1: Already in unified format
    if "FullDate" in raw_df.columns and "StartTime24" in raw_df.columns:
        return raw_df

    # Case 2: Raw Adobe Report CSV
    start_col = "Start Date and Time (America/Chicago TimeZone)"
    end_col = "End Date and Time (America/Chicago TimeZone)"

    records = []
    if start_col in raw_df.columns:
        for _, row in raw_df.iterrows():
            try:
                start_dt = pd.to_datetime(row[start_col])
                end_dt = pd.to_datetime(row[end_col])
            except Exception:
                continue

            course_name = str(row.get("Course Name", ""))
            if ": " in course_name:
                split_parts = course_name.split(": ", 1)
                title_part = split_parts[1].strip()
            else:
                title_part = course_name.strip()


            course_id = str(row.get("Course ID", "")).strip()
            enroll_url = f"https://learningmanager.adobe.com/app/learner?accountId=57953#/course/{course_id}"
            description = desc_dict.get(title_part, f"Class description for {title_part}.")

            records.append({
                "FullDate": start_dt.strftime("%Y-%m-%d"),
                "Date": int(start_dt.day),
                "Title": title_part,
                "StartTime24": start_dt.strftime("%H:%M:%S"),
                "StartTime": format_12hr(start_dt),
                "EndTime": format_12hr(end_dt),
                "Location": str(row.get("Location", "")).strip(),
                "InPersonLink": enroll_url,
                "Description": description
            })

    out_df = pd.DataFrame(records)
    if not out_df.empty:
        out_df = out_df.sort_values(by=["FullDate", "StartTime24"]).reset_index(drop=True)
    return out_df


# 3. Orchard XML Generator
def generate_orchard_xml(df: pd.DataFrame, start_id: int, time_offset: int, author: str, owner: str, status: str) -> bytes:
    """Compiles the unified DataFrame into an Orchard CMS XML Recipe."""
    root = ET.Element("Orchard")

    recipe = ET.SubElement(root, "Recipe")
    export_utc = ET.SubElement(recipe, "ExportUtc")
    export_utc.text = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    author_elem = ET.SubElement(recipe, "Author")
    author_elem.text = author
    is_setup = ET.SubElement(recipe, "IsSetupRecipe")
    is_setup.text = "false"

    content = ET.SubElement(root, "Content")
    current_id = start_id

    for _, row in df.iterrows():
        dt_str = f"{str(row['FullDate']).strip()} {str(row['StartTime24']).strip()}"
        try:
            local_dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            local_dt = pd.to_datetime(dt_str)

        utc_dt = local_dt + timedelta(hours=time_offset)
        xml_time_str = utc_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

        course = ET.SubElement(content, "Course", {
            "Id": f"/Identifier={current_id}",
            "Status": status
        })

        ET.SubElement(course, "Course.StartTime", {"Value": xml_time_str})
        ET.SubElement(course, "TextField.Location", {"Text": str(row["Location"])})

        desc_html = (
            f'<p><a href="{row["InPersonLink"]}" target="_blank" '
            f'title="Register for {row["Title"]} Class">Register for {row["Title"]} Class</a></p>\n'
            f'<p>{row["Description"]}</p>'
        )
        ET.SubElement(course, "TextField.Description", {"Text": desc_html})

        now_str = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
        ET.SubElement(course, "CommonPart", {
            "Owner": owner,
            "CreatedUtc": now_str,
            "PublishedUtc": now_str,
            "ModifiedUtc": now_str
        })
        ET.SubElement(course, "IdentityPart", {"Identifier": ""})
        ET.SubElement(course, "TitlePart", {"Title": str(row["Title"])})

        current_id += 1

    raw_xml = ET.tostring(root, encoding="utf-8")
    dom = xml.dom.minidom.parseString(raw_xml)
    return dom.toprettyxml(indent="  ", encoding="utf-8")


# 4. Helper for Dynamic Weekday Calendar Grid
def get_weekday_grid(df: pd.DataFrame):
    """Generates Monday-Friday week arrays dynamically based on the schedule's month/year."""
    if df.empty or "FullDate" not in df.columns:
        w1 = [2, 3, 4, 5, 6]
        w2 = [9, 10, 11, 12, 13]
        w3 = [16, 17, 18, 19, 20]
        w4 = [23, 24, 25, 26, 27]
        w5 = [30, 31, None, None, None]
        return [w1, w2, w3, w4, w5], "Monthly"

    first_date = pd.to_datetime(df["FullDate"].dropna().iloc[0])
    year, month = first_date.year, first_date.month
    month_label = first_date.strftime("%B %Y")

    cal = calendar.Calendar(firstweekday=0)  # Monday = 0
    month_days = cal.monthdayscalendar(year, month)

    weekday_weeks = []
    for week in month_days:
        mon_fri = [d if d != 0 else None for d in week[:5]]
        if any(mon_fri):
            weekday_weeks.append(mon_fri)

    return weekday_weeks, month_label


# 5. PDF Compilation Engine (ReportLab)
from reportlab.lib.utils import ImageReader
from reportlab.platypus import Image as RLImage

def generate_calendar_pdf(df: pd.DataFrame) -> io.BytesIO:
    """Assembles a high-resolution landscape calendar with banner and active enrollment links."""
    pdf_buffer = io.BytesIO()
    
    # Landscape Letter (792 x 612 pt) with 18 pt margins (756 pt printable width)
    doc = SimpleDocTemplate(
        pdf_buffer,
        pagesize=landscape(letter),
        leftMargin=18,
        rightMargin=18,
        topMargin=18,
        bottomMargin=18
    )
    
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle('DocTitle', parent=styles['Heading1'], fontSize=15, leading=17, textColor=colors.HexColor('#1f4e79'), alignment=1)
    day_header_style = ParagraphStyle('DayHeader', parent=styles['Normal'], fontSize=9, leading=11, fontName='Helvetica-Bold', textColor=colors.white, alignment=1)
    date_num_style = ParagraphStyle('DateNum', parent=styles['Normal'], fontSize=8.5, leading=10, fontName='Helvetica-Bold', textColor=colors.HexColor('#555555'), alignment=2)
    course_name_style = ParagraphStyle('CourseName', parent=styles['Normal'], fontSize=7, leading=8.5, fontName='Helvetica-Bold', textColor=colors.HexColor('#1f4e79'))
    course_meta_style = ParagraphStyle('CourseMeta', parent=styles['Normal'], fontSize=6, leading=7.5, textColor=colors.HexColor('#333333'))
    link_style = ParagraphStyle('LinkStyle', parent=styles['Normal'], fontSize=6, leading=7.5, textColor=colors.HexColor('#0056b3'))
    empty_cell_style = ParagraphStyle('EmptyCell', parent=styles['Normal'], fontSize=6, leading=7, textColor=colors.HexColor('#cccccc'), alignment=1)

    elements = []
    
    # 1. Embed Header Banner Image (with automatic aspect ratio preservation)
    banner_path = "LearnTLC_.png"
    if os.path.exists(banner_path):
        try:
            reader = ImageReader(banner_path)
            orig_w, orig_h = reader.getSize()
            aspect = orig_h / float(orig_w)
            
            # Target width up to full printable width (756 pt), capped at 50 pt height
            target_w = 756.0
            target_h = target_w * aspect
            if target_h > 50.0:
                target_h = 50.0
                target_w = target_h / aspect
                
            banner_img = RLImage(banner_path, width=target_w, height=target_h)
            banner_img.hAlign = 'CENTER'
            elements.append(banner_img)
            elements.append(Spacer(1, 6))
        except Exception:
            elements.append(Paragraph("Learn@TLC - Course Training Calendar", title_style))
            elements.append(Spacer(1, 6))
    else:
        elements.append(Paragraph("Learn@TLC - Course Training Calendar", title_style))
        elements.append(Spacer(1, 6))
    
    # 2. Build Calendar Table
    weekdays = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    table_data = [[Paragraph(day, day_header_style) for day in weekdays]]
    
    calendar_weeks = [
        [2, 3, 4, 5, 6],
        [9, 10, 11, 12, 13],
        [16, 17, 18, 19, 20],
        [23, 24, 25, 26, 27],
        [30, 31, None, None, None]
    ]
    
    for week in calendar_weeks:
        row_cells = []
        for day in week:
            cell_content = []
            if day is not None:
                cell_content.append(Paragraph(str(day), date_num_style))
                cell_content.append(Spacer(1, 1))
                
                day_classes = df[df['Date'] == day]
                if not day_classes.empty:
                    for _, course in day_classes.iterrows():
                        safe_title = html.escape(str(course['Title']))
                        safe_loc = html.escape(str(course['Location']))
                        safe_time = f"{course['StartTime']} - {course['EndTime']}"
                        
                        cell_content.append(Paragraph(safe_title, course_name_style))
                        cell_content.append(Paragraph(f"{safe_time} | {safe_loc}", course_meta_style))
                        
                        enroll_link = course.get('InPersonLink')
                        if pd.notna(enroll_link) and str(enroll_link).startswith("http"):
                            cell_content.append(Paragraph(f'<a href="{enroll_link}"><u>Enroll Now &rarr;</u></a>', link_style))
                        cell_content.append(Spacer(1, 2))
                else:
                    cell_content.append(Paragraph("&nbsp;", empty_cell_style))
            else:
                cell_content.append(Paragraph("&nbsp;", empty_cell_style))
            
            row_cells.append(cell_content)
        table_data.append(row_cells)
    
    cal_table = Table(table_data, colWidths=[151.2] * 5)
    cal_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f4e79')),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cccccc')),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#1f4e79')),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
    ]))
    
    elements.append(cal_table)
    doc.build(elements)
    pdf_buffer.seek(0)
    return pdf_buffer

# 6. Sidebar Data Ingestion & Settings
st.sidebar.header("📂 1. Upload Data Source")
uploaded_adobe = st.sidebar.file_uploader("Upload Raw Adobe Report CSV", type=["csv"])
uploaded_desc = st.sidebar.file_uploader("Optional: Upload class_desc.csv", type=["csv"])

desc_dict = DEFAULT_DESCRIPTIONS.copy()
if os.path.exists(DEFAULT_DESC_FILE):
    try:
        local_desc_df = pd.read_csv(DEFAULT_DESC_FILE, header=None, names=["TitleKey", "DescValue"])
        desc_dict.update(dict(zip(local_desc_df["TitleKey"], local_desc_df["DescValue"])))
    except Exception:
        pass

if uploaded_desc is not None:
    try:
        desc_df = pd.read_csv(uploaded_desc, header=None, names=["TitleKey", "DescValue"])
        desc_dict.update(dict(zip(desc_df["TitleKey"], desc_df["DescValue"])))
        st.sidebar.success("Custom descriptions loaded!")
    except Exception as e:
        st.sidebar.error(f"Error loading descriptions: {e}")

# Process new upload and persist to disk
if uploaded_adobe is not None:
    df_parsed = parse_uploaded_schedule(uploaded_adobe, desc_dict)
    if not df_parsed.empty:
        if "last_uploaded_name" not in st.session_state or st.session_state.last_uploaded_name != uploaded_adobe.name:
            df_parsed.to_csv(PERSISTED_DATA_FILE, index=False)
            st.session_state.last_uploaded_name = uploaded_adobe.name

if os.path.exists(PERSISTED_DATA_FILE):
    df_raw = pd.read_csv(PERSISTED_DATA_FILE)
else:
    df_raw = None

st.sidebar.markdown("---")
st.sidebar.header("⚙️ 2. Orchard XML Settings")
start_id = st.sidebar.number_input("Starting Course ID", min_value=1, value=201, step=1)
time_offset = st.sidebar.selectbox(
    "Timezone Offset (Central to UTC)",
    options=[6, 5, 0],
    index=0,
    help="Use 6 for CST (Nov–Mar), 5 for CDT (Mar–Nov), or 0 if already UTC."
)
author = st.sidebar.text_input("Recipe Author", value="LEGIS\\LISIRAS")
owner = st.sidebar.text_input("Course Owner", value="/User.UserName=LEGIS\\\\LISINCW")
status = st.sidebar.selectbox("Course Status", ["Draft", "Published"], index=0)


# 7. Main Application Views
if df_raw is None or df_raw.empty:
    st.info("👋 Upload your monthly **Adobe Report CSV** in the sidebar to generate the interactive calendar, printable PDF, and Orchard XML recipe.")
else:
    st.sidebar.markdown("---")
    st.sidebar.header("🔍 3. Calendar Filters")
    search_term = st.sidebar.text_input("Search Course Title", "")
    available_locs = ["All"] + sorted(df_raw["Location"].dropna().astype(str).unique().tolist())
    selected_loc = st.sidebar.selectbox("Location", available_locs)

    filtered_df = df_raw.copy()
    if search_term:
        filtered_df = filtered_df[filtered_df["Title"].astype(str).str.contains(search_term, case=False, na=False)]
    if selected_loc != "All":
        filtered_df = filtered_df[filtered_df["Location"].astype(str) == selected_loc]

    calendar_weeks, month_label = get_weekday_grid(filtered_df)

    # Sidebar Exports
    st.sidebar.markdown("---")
    st.sidebar.header("📥 4. Quick Exports")
    pdf_output = generate_calendar_pdf(filtered_df, calendar_weeks, month_label)
    st.sidebar.download_button(
        label="📄 Download Printable Calendar PDF",
        data=pdf_output,
        file_name=f"TLC_Training_Calendar_{month_label.replace(' ', '_')}.pdf",
        mime="application/pdf",
        use_container_width=True
    )

    xml_output = generate_orchard_xml(filtered_df, start_id, time_offset, author, owner, status)
    st.sidebar.download_button(
        label="⚡ Download Orchard XML Recipe",
        data=xml_output,
        file_name="cscweb_schedule.xml",
        mime="application/xml",
        use_container_width=True
    )

    csv_html_cols = ["Date", "Title", "StartTime", "EndTime", "Location", "InPersonLink"]
    csv_html_data = filtered_df[csv_html_cols].to_csv(index=False).encode("utf-8")
    st.sidebar.download_button(
        label="📊 Download csv_html.csv",
        data=csv_html_data,
        file_name="csv_html.csv",
        mime="text/csv",
        use_container_width=True
    )

    # Main Tabs
    tab_cal, tab_edit, tab_xml = st.tabs([
        f"📅 Monthly Calendar ({month_label})",
        "✏️ Schedule Editor (Persistent)",
        "📄 Orchard XML Preview"
    ])

    with tab_cal:
        weekday_labels = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
        header_cols = st.columns(5)
        for idx, day_str in enumerate(weekday_labels):
            header_cols[idx].markdown(
                f"<div style='background-color: #1f4e79; color: white; text-align: center; "
                f"font-weight: bold; padding: 6px; border-radius: 4px;'>{day_str}</div>",
                unsafe_allow_html=True
            )
        st.write("")

        for w_idx, week in enumerate(calendar_weeks, start=1):
            st.markdown(f"#### Week {w_idx}")
            week_cols = st.columns(5)
            for c_idx, date_val in enumerate(week):
                with week_cols[c_idx]:
                    if date_val is not None:
                        with st.container(border=True):
                            st.markdown(
                                f"<div style='text-align: right; font-weight: bold; "
                                f"color: #777; font-size: 0.9em;'>{date_val}</div>",
                                unsafe_allow_html=True
                            )
                            classes_today = filtered_df[filtered_df["Date"] == date_val]
                            if classes_today.empty:
                                st.markdown("<p style='color: #ccc; font-style: italic; text-align: center;'>No classes</p>", unsafe_allow_html=True)
                            else:
                                for _, item in classes_today.iterrows():
                                    st.markdown(f"**📘 {item['Title']}**")
                                    st.caption(f"🕒 {item['StartTime']} - {item['EndTime']}")
                                    st.caption(f"📍 {item['Location']}")

                                    link = item.get("InPersonLink")
                                    if pd.notna(link) and str(link).startswith("http"):
                                        st.markdown(
                                            f'<a href="{link}" target="_blank" style="'
                                            f'display: block; text-align: center; '
                                            f'background-color: #1f4e79; color: white; '
                                            f'padding: 4px; border-radius: 4px; '
                                            f'text-decoration: none; font-size: 0.8em; '
                                            f'margin-top: 4px; margin-bottom: 8px;">🔗 Enroll</a>',
                                            unsafe_allow_html=True
                                        )
                                    st.markdown("<hr style='margin: 6px 0; border: none; border-top: 1px dashed #eee;' />", unsafe_allow_html=True)
                    else:
                        st.write("")

    with tab_edit:
        st.subheader("✏️ Interactive Schedule Table")
        st.caption("Any edits you make below and save will persist across sessions and automatically update the Calendar, PDF, and XML exports.")
        edited_df = st.data_editor(df_raw, num_rows="dynamic", use_container_width=True, key="schedule_editor")

        col_save, col_reset = st.columns(2)
        with col_save:
            if st.button("💾 Save Table Edits", type="primary", use_container_width=True):
                edited_df.to_csv(PERSISTED_DATA_FILE, index=False)
                st.success("Changes saved! Refreshing views...")
                st.rerun()
        with col_reset:
            if st.button("🗑️ Clear Saved Schedule", use_container_width=True):
                if os.path.exists(PERSISTED_DATA_FILE):
                    os.remove(PERSISTED_DATA_FILE)
                st.rerun()

    with tab_xml:
        st.subheader("📄 Orchard XML Recipe Preview")
        st.code(xml_output[:2500].decode("utf-8") + "\n\n... (Download full XML from sidebar) ...", language="xml")
