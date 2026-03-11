print("🀐 🀢 🀣 🀤 🀥 🀦 🀧 🀨 🀩 🀪 🀐")
print("🀐 🀢 🀣 🀤 🀥 🀦 🀧 🀨 🀩 🀪 🀐")
print("🀐 🀢 🀣 🀤 🀥 🀦 🀧 🀨 🀩 🀪 🀐")

import openai
import polars as pl

# Set OpenAI key 
openai.api_key = "KEY HERE"

# Load Excel file 
df = pl.read_excel("/Users/matteoperini/Documents/🔴 Radboud/Studies and Data 🟢 /Python_data/python_LLM_prova.xlsx")
print(df.describe())

# Send prompt to ChatGTP 
def ask_gpt(prompt, text):
    full_prompt = (
        f"{prompt.strip()} "
        "Rate the following text on a scale from 1 ('not at all') to 7 ('extremely').\n"
        "Respond with **only** the number (e.g., 4). No explanation. No text.\n\n"
        f"Text: {text.strip()}"
    )
    try:
        client = openai.OpenAI(api_key=openai.api_key)
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": full_prompt}],
            temperature=0,
            max_tokens=10,
        )
        answer = ''.join(filter(str.isdigit, response.choices[0].message.content.strip()))
        return answer
    except Exception as e:
        print("Errore durante la chiamata a GPT:", e)
        return "NA" 

# Apply GTP for VAR1 
if "VAR1" not in df.columns or df.select("VAR1").null_count().item() == len(df):
    df = df.with_columns([
        pl.struct(["Prompt1", "Text"]).map_elements(lambda row: ask_gpt(row["Prompt1"], row["Text"])).alias("VAR1")
    ])
    df.write_excel("valutazioni_con_risposte.xlsx")

# Apply GTP for VAR2
if "VAR2" not in df.columns or df.select("VAR2").null_count().item() == len(df):
    df = df.with_columns([
        pl.struct(["Prompt2", "Text"]).map_elements(lambda row: ask_gpt(row["Prompt2"], row["Text"])).alias("VAR2")
    ])
    df.write_excel("valutazioni_con_risposte.xlsx")

print("🀐 🀢 🀣 🀤 🀥 🀦 🀧 🀨 🀩 🀪 🀐")
print("🀐 🀢 🀣 🀤 🀥 🀦 🀧 🀨 🀩 🀪 🀐")
print("🀐 🀢 🀣 🀤 🀥 🀦 🀧 🀨 🀩 🀪 🀐")