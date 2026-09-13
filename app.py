import os
import re
import base64
from io import BytesIO

import streamlit as st
from PIL import Image
from groq import Groq
from dotenv import load_dotenv


# ============================================================
# CONFIGURATION
# ============================================================

load_dotenv()

GROQ_MODEL = os.getenv("GROQ_MODEL", "qwen/qwen3.6-27b")


CATEGORIES = [
    "Recyclable",
    "Organic/Compostable",
    "Hazardous",
    "Electronic Waste",
    "General/Residual",
    "Reusable",
]


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="EcoSort AI",
    page_icon="♻️",
    layout="centered",
)


# ============================================================
# CUSTOM CSS
# ============================================================

st.markdown(
    """
    <style>
    .main {
        max-width: 900px;
        margin: auto;
    }

    .title {
        text-align: center;
        font-size: 42px;
        font-weight: 700;
        margin-bottom: 5px;
    }

    .subtitle {
        text-align: center;
        font-size: 18px;
        margin-bottom: 30px;
    }

    .result-box {
        padding: 20px;
        border-radius: 12px;
        border: 1px solid #ddd;
        margin-top: 20px;
    }

    .stat-box {
        text-align: center;
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #ddd;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# API KEY
# ============================================================

def get_api_key():
    # Local computer: .env
    key = os.getenv("GROQ_API_KEY")

    if key:
        return key

    # Streamlit Cloud: Secrets
    try:
        return st.secrets["GROQ_API_KEY"]
    except Exception:
        return None


GROQ_API_KEY = get_api_key()


# ============================================================
# SESSION STATE
# ============================================================

if "items_scanned" not in st.session_state:
    st.session_state.items_scanned = 0

if "category_counts" not in st.session_state:
    st.session_state.category_counts = {
        category: 0 for category in CATEGORIES
    }

if "result" not in st.session_state:
    st.session_state.result = None

if "uploader_key" not in st.session_state:
    st.session_state.uploader_key = 0


# ============================================================
# AI ANALYSIS
# ============================================================

def analyze_waste(image, region):
    if not GROQ_API_KEY:
        return (
            "Error: GROQ_API_KEY is not configured.\n\n"
            "For local testing, add it to your .env file.\n"
            "For Streamlit Cloud, add it under App Settings → Secrets."
        )

    try:
        client = Groq(api_key=GROQ_API_KEY)

        # Convert image to RGB
        image = image.convert("RGB")

        # Resize image
        image.thumbnail((600, 600))

        # Convert to JPEG
        buffer = BytesIO()
        image.save(buffer, format="JPEG", quality=75)

        image_bytes = buffer.getvalue()

        image_base64 = base64.b64encode(image_bytes).decode("utf-8")

        prompt = f"""
You are EcoSort AI, a responsible AI waste-sorting assistant.

Analyze the uploaded waste image carefully.

The user's selected region is:
{region}

Classify the item into EXACTLY ONE of these six categories:

1. Recyclable
2. Organic/Compostable
3. Hazardous
4. Electronic Waste
5. General/Residual
6. Reusable

Important safety rules:

- Batteries should normally be treated as Hazardous unless clearly identified
  as an electronic-waste item according to local guidance.
- Chemicals, toxic substances, unknown liquids, medical waste, sharps,
  aerosols, and dangerous materials require safety warnings.
- Electrical and electronic devices/components should normally be
  Electronic Waste.
- Food scraps and plant material should normally be Organic/Compostable.
- Items that can reasonably be used again without major processing may be
  Reusable.
- Do not claim certainty when the image is unclear.
- If identification is uncertain, clearly say so.
- Never encourage unsafe handling.
- Give practical disposal advice.
- Region-specific guidance should be cautious because local recycling rules
  may vary.

Return your answer using EXACTLY these headings:

Item:
Material:
Waste Category:
Confidence:
Why:
What to do:
Safety Warning:
Eco Tip:
Reuse Suggestion:

For Confidence, use only:
High
Medium
Low

For Waste Category, use exactly one of:
Recyclable
Organic/Compostable
Hazardous
Electronic Waste
General/Residual
Reusable

Keep the answer concise but useful.
"""

        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt,
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_base64}"
                            },
                        },
                    ],
                }
            ],
            temperature=0.2,
            max_completion_tokens=700,
            reasoning_effort="none",
        )

        return response.choices[0].message.content

    except Exception as e:
        return (
            "AI analysis failed.\n\n"
            "Please try again with a clearer image.\n\n"
            f"Technical details: {str(e)}"
        )


# ============================================================
# CATEGORY PARSER
# ============================================================

def extract_category(result_text):
    match = re.search(
        r"Waste Category:\s*(.+)",
        result_text,
        re.IGNORECASE,
    )

    if match:
        category = match.group(1).strip()

        for valid_category in CATEGORIES:
            if category.lower() == valid_category.lower():
                return valid_category

    return None


# ============================================================
# DISPLAY RESULT
# ============================================================

def display_result(result_text):
    st.markdown("### 🔎 Analysis Result")

    st.markdown(
        f"""
        <div class="result-box">
        {result_text.replace(chr(10), "<br>")}
        </div>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# RESET SCAN
# ============================================================

def reset_scan():
    st.session_state.result = None
    st.session_state.uploader_key += 1
    st.rerun()


# ============================================================
# HEADER
# ============================================================

st.markdown(
    '<div class="title">♻️ EcoSort AI</div>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="subtitle">Take a picture. Know where it belongs.</div>',
    unsafe_allow_html=True,
)


# ============================================================
# API WARNING
# ============================================================

if not GROQ_API_KEY:
    st.warning(
        "⚠️ Groq API key is not configured. "
        "Add GROQ_API_KEY before using the AI analysis."
    )


# ============================================================
# REGION
# ============================================================

region = st.selectbox(
    "🌍 Select your region",
    [
        "Pakistan",
        "General / International",
    ],
)


# ============================================================
# IMAGE UPLOAD
# ============================================================

uploaded_file = st.file_uploader(
    "📷 Upload a waste image",
    type=["jpg", "jpeg", "png", "webp"],
    key=f"uploader_{st.session_state.uploader_key}",
)


# ============================================================
# IMAGE PREVIEW
# ============================================================

if uploaded_file is not None:

    image = Image.open(uploaded_file)

    st.image(
        image,
        caption="Uploaded waste item",
        use_container_width=True,
    )

    # ========================================================
    # ANALYZE BUTTON
    # ========================================================

    if st.button(
        "🔍 Analyze Waste",
        use_container_width=True,
        type="primary",
    ):

        with st.spinner("AI is analyzing the item..."):

            result = analyze_waste(
                image,
                region,
            )

        st.session_state.result = result

        category = extract_category(result)

        if category:

            st.session_state.items_scanned += 1

            st.session_state.category_counts[category] += 1

        st.rerun()


# ============================================================
# RESULT
# ============================================================

if st.session_state.result:

    display_result(
        st.session_state.result
    )

    st.markdown("---")

    if st.button(
        "📷 Scan Another Item",
        use_container_width=True,
    ):
        reset_scan()


# ============================================================
# STATISTICS
# ============================================================

st.markdown("---")

st.markdown("### 📊 Session Statistics")

st.metric(
    "Items Scanned",
    st.session_state.items_scanned,
)

cols = st.columns(3)

for index, category in enumerate(CATEGORIES):

    with cols[index % 3]:

        st.markdown(
            f"""
            <div class="stat-box">
                <strong>{category}</strong>
                <br>
                {st.session_state.category_counts[category]}
            </div>
            """,
            unsafe_allow_html=True,
        )


# ============================================================
# FOOTER
# ============================================================

st.markdown("---")

st.caption(
    "EcoSort AI provides AI-assisted guidance. "
    "Always follow local waste-management rules, especially for hazardous materials."
)