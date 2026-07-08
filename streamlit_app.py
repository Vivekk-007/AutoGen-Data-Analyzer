import asyncio
import os
from pathlib import Path

import streamlit as st
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from autogen_agentchat.base import TaskResult
from autogen_agentchat.messages import TextMessage

from config.docker_utils import (
    getDockerCommandLineExecutor,
    start_docker_container,
    stop_docker_container,
)
from config.openai_model_client import get_model_client
from team.analyzer_gpt import getDataAnalyzerTeam

st.set_page_config(page_title="Digital Data Analyzer", page_icon="📊", layout="centered")
st.title("Digital Data Analyzer")

if "messages" not in st.session_state:
    st.session_state.messages = []
if "autogen_team_state" not in st.session_state:
    st.session_state.autogen_team_state = None
if "pending_task" not in st.session_state:
    st.session_state.pending_task = None
if "current_output_path" not in st.session_state:
    st.session_state.current_output_path = None

WORK_DIR = Path(__file__).resolve().parent
TEMP_DIR = WORK_DIR / "temp"
CSV_PATH = TEMP_DIR / "data.csv"
DEFAULT_OUTPUT_PATH = TEMP_DIR / "output.png"


def build_output_path(task_text: str) -> Path:
    safe_name = "".join(ch if ch.isalnum() else "_" for ch in task_text.strip().lower())[:80] or "analysis"
    return TEMP_DIR / f"{safe_name}_{len(task_text)}.png"


def find_generated_image() -> Path | None:
    if st.session_state.current_output_path and Path(st.session_state.current_output_path).exists():
        return Path(st.session_state.current_output_path)

    if DEFAULT_OUTPUT_PATH.exists():
        return DEFAULT_OUTPUT_PATH

    png_files = sorted(TEMP_DIR.glob("**/*.png"))
    return png_files[-1] if png_files else None


def generate_fallback_image(csv_path: Path, output_path: Path) -> bool:
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        if output_path.exists():
            output_path.unlink()

        df = pd.read_csv(csv_path)
        fig, ax = plt.subplots(figsize=(6, 4))

        survived_col = None
        for col in df.columns:
            if col.lower() == "survived":
                survived_col = col
                break

        if survived_col is not None:
            counts = df[survived_col].fillna("Unknown").astype(str).value_counts()
            counts.plot(kind="bar", ax=ax, color=["#4C78A8", "#F58518", "#54A24B"])
            ax.set_title("Value distribution")
            ax.set_ylabel("Count")
            ax.set_xlabel(survived_col)
        else:
            numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
            if numeric_cols:
                numeric_series = pd.to_numeric(df[numeric_cols[0]], errors="coerce").dropna()
                ax.hist(numeric_series, bins=min(10, max(5, len(numeric_series) // 5)))
                ax.set_title(f"Distribution of {numeric_cols[0]}")
                ax.set_xlabel(numeric_cols[0])
                ax.set_ylabel("Frequency")
            else:
                ax.text(0.5, 0.5, "No numeric data available", ha="center", va="center")
                ax.set_axis_off()

        plt.tight_layout()
        fig.savefig(output_path, dpi=150)
        plt.close(fig)
        return output_path.exists()
    except Exception as exc:
        print(f"Fallback image creation failed: {exc}")
        return False


async def run_analyzer_gpt(docker, openai_model_client, task):
    try:
        await start_docker_container(docker)
        team = getDataAnalyzerTeam(docker, openai_model_client)

        if st.session_state.autogen_team_state is not None:
            await team.load_state(st.session_state.autogen_team_state)

        async for message in team.run_stream(task=task):
            if isinstance(message, TextMessage):
                content = str(message.content)
                print(f"{message.source}: {content}")
                if message.source == "user":
                    with st.chat_message("user", avatar="👨"):
                        st.markdown(content)
                else:
                    with st.chat_message("assistant", avatar="🤖"):
                        st.markdown(content)
                st.session_state.messages.append({"role": "assistant", "content": f"{message.source}: {content}"})

            elif isinstance(message, TaskResult):
                stop_reason = getattr(message, "stop_reason", "completed")
                print(f"Stop Reason: {stop_reason}")
                st.session_state.messages.append({"role": "assistant", "content": f"Stop Reason: {stop_reason}"})

        st.session_state.autogen_team_state = await team.save_state()
        return None
    except Exception as exc:
        print(exc)
        return str(exc)
    finally:
        await stop_docker_container(docker)


for msg in st.session_state.messages:
    if msg.get("role") == "user":
        with st.chat_message("user", avatar="👨"):
            st.markdown(msg.get("content", ""))
    else:
        with st.chat_message("assistant", avatar="🤖"):
            st.markdown(msg.get("content", ""))


uploaded_file = st.file_uploader("Upload your CSV file", type="csv")

task = st.chat_input("Enter your Task.")
if task:
    st.session_state.pending_task = task

if st.session_state.pending_task:
    task_text = st.session_state.pending_task
    st.session_state.pending_task = None

    if uploaded_file is None:
        st.warning("Please upload a CSV file first.")
    else:
        TEMP_DIR.mkdir(parents=True, exist_ok=True)
        with CSV_PATH.open("wb") as handle:
            handle.write(uploaded_file.getbuffer())

        with st.chat_message("user", avatar="👨"):
            st.markdown(task_text)
        st.session_state.messages.append({"role": "user", "content": task_text})

        try:
            openai_model_client = get_model_client()
            docker = getDockerCommandLineExecutor()
        except Exception as exc:
            st.error(f"Unable to initialize the AI client: {exc}")
        else:
            with st.spinner("Analyzing your data..."):
                error = asyncio.run(run_analyzer_gpt(docker, openai_model_client, task_text))

            if error:
                st.error(f"Analysis failed: {error}")

            output_path = build_output_path(task_text)
            st.session_state.current_output_path = str(output_path)

            image_path = find_generated_image()
            if image_path is None:
                generated = generate_fallback_image(CSV_PATH, output_path)
                if generated:
                    image_path = output_path

            if image_path is not None:
                st.image(image_path, caption=f"Analysis output for: {task_text}")
            else:
                st.info("The analysis completed, but no image was produced yet.")

else:
    st.info("Upload a CSV file and describe the analysis you want to run.")
