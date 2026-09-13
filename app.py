import os
import re
import base64
from io import BytesIO

import gradio as gr
from groq import Groq
from dotenv import load_dotenv


# ============================================================
# LOAD ENVIRONMENT VARIABLES
# ============================================================

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not GROQ_API_KEY:
    raise ValueError(
        "GROQ_API_KEY is missing. "
        "Please create a .env file and add your Groq API key."
    )


# ============================================================
# GROQ CONFIGURATION
# ============================================================

GROQ_MODEL = "qwen/qwen3.6-27b"

client = Groq(api_key=GROQ_API_KEY)


# ============================================================
# WASTE CATEGORIES
# ============================================================

CATEGORIES = [
    "Recyclable",
    "Organic/Compostable",
    "Hazardous",
    "Electronic Waste",
    "General/Residual",
    "Reusable"
]


# ============================================================
# SESSION STATISTICS
# ============================================================

stats = {
    "total": 0,
    "Recyclable": 0,
    "Organic/Compostable": 0,
    "Hazardous": 0,
    "Electronic Waste": 0,
    "General/Residual": 0,
    "Reusable": 0
}


# ============================================================
# AI WASTE ANALYSIS
# ============================================================

def analyze_waste(image, region):

    if image is None:
        return "Please upload an image."

    try:

        # ----------------------------------------------------
        # Prepare image
        # ----------------------------------------------------

        image = image.convert("RGB")

        max_size = 600
        image.thumbnail((max_size, max_size))

        buffer = BytesIO()

        image.save(
            buffer,
            format="JPEG",
            quality=75
        )

        image_base64 = base64.b64encode(
            buffer.getvalue()
        ).decode("utf-8")


        # ----------------------------------------------------
        # AI PROMPT
        # ----------------------------------------------------

        prompt = f"""
You are EcoSort AI, a responsible AI-powered waste-sorting assistant.

Analyze the waste item shown in the image.

Selected region:
{region}

Your goal is to help the user understand:

1. What the item appears to be.
2. What material it is likely made from.
3. Which waste category it belongs to.
4. What the user should do with it.
5. Any important safety concerns.
6. How the user can make a more environmentally responsible choice.

Choose exactly ONE waste category:

- Recyclable
- Organic/Compostable
- Hazardous
- Electronic Waste
- General/Residual
- Reusable

Return your answer using EXACTLY this format:

Item: [name of item]

Material: [main material]

Waste Category: [one category from the list]

Confidence: [High, Medium, or Low]

Why: [brief evidence-based explanation]

What to do:

1. [practical disposal step]
2. [practical disposal step]
3. [optional additional step]

Safety Warning: [important warning, or None]

Eco Tip: [short, useful environmental advice]

Reuse Suggestion: [realistic reuse idea, or None]

IMPORTANT RESPONSIBLE-AI RULES:

IMAGE ANALYSIS:
- Only identify details that can reasonably be inferred from the image.
- Do not invent brand, chemical composition, material, or product details that cannot be determined.
- If the item is unclear or partially visible, use Low confidence.
- If multiple materials are visible, mention the main material and important components.

RECYCLING:
- Never claim that an item is recyclable everywhere.
- Never say that a material is widely accepted in a region unless this is clearly established.
- Recycling availability can vary between cities, facilities, and waste-management systems.
- When local information is uncertain, say:
  "Check your local recycling or waste-management service."
- Do not give false certainty about Pakistan or any other region.

SAFETY:
- Batteries, chemicals, paint, medical waste, sharps, aerosols,
  unknown liquids, electrical components, toxic substances,
  and potentially dangerous materials require a clear safety warning.
- Never recommend burning, crushing, puncturing, opening,
  or damaging hazardous items.
- Do not recommend putting hazardous waste into ordinary
  recycling or household waste unless there is a strong reason.
- When appropriate, recommend a designated collection or
  hazardous-waste facility.

ECO TIPS:
- Do NOT invent statistics, percentages, energy savings,
  environmental impact numbers, or scientific claims.
- Do NOT use unsupported claims about how much energy,
  water, or resources recycling saves.
- Prefer simple, reliable advice such as reducing single-use
  items, reusing suitable containers, separating materials,
  or using appropriate recycling services.

DISPOSAL:
- Give practical steps that an ordinary person can understand.
- Do not recommend actions that could create a safety risk.
- Consider the selected region, but clearly acknowledge
  when local rules may vary.

REUSE:
- Suggest reuse only when it is safe and practical.
- Do not suggest reusing containers that held hazardous
  chemicals, medical substances, or unsafe materials.
- If reuse is inappropriate, return "None".

STYLE:
- Keep the response concise.
- Use simple language.
- Do not use unnecessary technical terminology.
- Do not return JSON.
- Do not use Markdown code fences.
- Return only the requested result format.
"""


        # ----------------------------------------------------
        # GROQ VISION REQUEST
        # ----------------------------------------------------

        response = client.chat.completions.create(

            model=GROQ_MODEL,

            messages=[
                {
                    "role": "user",

                    "content": [
                        {
                            "type": "text",
                            "text": prompt
                        },

                        {
                            "type": "image_url",

                            "image_url": {
                                "url":
                                "data:image/jpeg;base64,"
                                + image_base64
                            }
                        }
                    ]
                }
            ],

            temperature=0.2,

            max_completion_tokens=700,

            reasoning_effort="none"
        )


        # ----------------------------------------------------
        # GET AI RESPONSE
        # ----------------------------------------------------

        result = response.choices[0].message.content

        if not result or not result.strip():

            return (
                "⚠️ The AI returned an empty result. "
                "Please try again."
            )


        print("AI RESPONSE:")
        print(result)


        return result.strip()


    # --------------------------------------------------------
    # ERROR HANDLING
    # --------------------------------------------------------

    except Exception as e:

        print("GROQ ERROR:")
        print(str(e))

        return (
            "⚠️ AI analysis failed.\n\n"
            "Please check your connection and try again."
        )


# ============================================================
# RUN ECOSORT
# ============================================================

def run_ecosort(image, region):

    if image is None:

        return (
            "⚠️ Please upload a waste image first."
        )


    result = analyze_waste(
        image,
        region
    )


    if not result:

        return (
            "⚠️ Unable to analyze the image."
        )


    # --------------------------------------------------------
    # Handle dictionary response if returned
    # --------------------------------------------------------

    if isinstance(result, dict):

        if not result.get(
            "success",
            False
        ):

            return (
                "⚠️ "
                + result.get(
                    "message",
                    "Unable to analyze the image."
                )
            )

        result = result.get(
            "data",
            result
        )


    result_text = str(result)


    # --------------------------------------------------------
    # FIXED CATEGORY DETECTION
    #
    # Only read the actual Waste Category line.
    # This prevents words such as "recyclables"
    # appearing elsewhere from affecting statistics.
    # --------------------------------------------------------

    detected_category = None


    category_match = re.search(
        r"Waste Category\s*:\s*(.+)",
        result_text,
        re.IGNORECASE
    )


    if category_match:

        detected_value = (
            category_match
            .group(1)
            .strip()
        )


        for category in CATEGORIES:

            if detected_value.lower().startswith(
                category.lower()
            ):

                detected_category = category

                break


    # --------------------------------------------------------
    # UPDATE STATISTICS
    # --------------------------------------------------------

    stats["total"] += 1


    if detected_category:

        stats[detected_category] += 1


    return result_text


# ============================================================
# SHOW STATISTICS
# ============================================================

def show_stats():

    return f"""
### 📊 Session Statistics

**Items Scanned:** {stats["total"]}

♻️ **Recyclable:** {stats["Recyclable"]}

🌱 **Organic/Compostable:** {stats["Organic/Compostable"]}

⚠️ **Hazardous:** {stats["Hazardous"]}

🔌 **Electronic Waste:** {stats["Electronic Waste"]}

🗑️ **General/Residual:** {stats["General/Residual"]}

🔄 **Reusable:** {stats["Reusable"]}
"""


# ============================================================
# RESET APPLICATION
# ============================================================

def reset_app():

    stats["total"] = 0


    for category in CATEGORIES:

        stats[category] = 0


    return (

        None,

        show_stats(),

        """
### 🌱 Ready to Scan

Upload a waste image and click **Analyze Waste**.
"""
    )


# ============================================================
# GRADIO APPLICATION
# ============================================================

with gr.Blocks(
    title="EcoSort AI"
) as demo:


    # --------------------------------------------------------
    # HEADER
    # --------------------------------------------------------

    gr.Markdown(
        """
# 🌱 EcoSort AI

### Take a picture. Know where it belongs.

AI-powered waste identification, safety checks, and
disposal guidance.
"""
    )


    # --------------------------------------------------------
    # MAIN SCANNER
    # --------------------------------------------------------

    with gr.Row():


        # ----------------------------------------------------
        # LEFT COLUMN
        # ----------------------------------------------------

        with gr.Column():

            image_input = gr.Image(
                type="pil",
                label="📷 Upload Waste Image"
            )


            region_input = gr.Dropdown(

                choices=[
                    "Pakistan",
                    "General / International"
                ],

                value="Pakistan",

                label="🌍 Select Region"
            )


            with gr.Row():

                analyze_button = gr.Button(
                    "🔍 Analyze Waste",
                    variant="primary"
                )


                scan_again_button = gr.Button(
                    "🔄 Scan Again"
                )


        # ----------------------------------------------------
        # RIGHT COLUMN
        # ----------------------------------------------------

        with gr.Column():

            result_output = gr.Markdown(

                """
### 🌱 Ready to Scan

Upload a waste image and click **Analyze Waste**.
"""
            )


    # --------------------------------------------------------
    # STATISTICS
    # --------------------------------------------------------

    with gr.Row():

        stats_output = gr.Markdown(

            show_label=False,

            value=show_stats()
        )


    # --------------------------------------------------------
    # SCAN AGAIN
    # --------------------------------------------------------

    scan_again_button.click(

        fn=reset_app,

        inputs=[],

        outputs=[
            image_input,
            stats_output,
            result_output
        ]
    )


    # --------------------------------------------------------
    # ANALYZE WASTE
    # --------------------------------------------------------

    analyze_button.click(

        fn=run_ecosort,

        inputs=[
            image_input,
            region_input
        ],

        outputs=[
            result_output
        ]
    )


    # --------------------------------------------------------
    # UPDATE STATISTICS
    # --------------------------------------------------------

    analyze_button.click(

        fn=show_stats,

        inputs=[],

        outputs=[
            stats_output
        ]
    )


    # --------------------------------------------------------
    # FOOTER
    # --------------------------------------------------------

    gr.Markdown(
        """
---

### ♻️ How EcoSort AI Works

**📷 Scan → 🤖 Analyze → ♻️ Classify → 🧹 Get Disposal Guidance**

### ⚠️ Important

EcoSort AI provides AI-based guidance. Recycling and disposal
rules can vary by location, so always follow local
waste-management instructions.

---

**🌱 EcoSort AI — From "What is this?" to "What should I do with it?"**
"""
    )


# ============================================================
# START APPLICATION
# ============================================================

if __name__ == "__main__":

    demo.launch()