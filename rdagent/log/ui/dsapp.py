import re
from collections import defaultdict
from datetime import timedelta
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from streamlit import session_state as state

from rdagent.app.data_science.loop import DataScienceRDLoop
from rdagent.log.mle_summary import extract_mle_json, is_valid_session
from rdagent.log.storage import FileStorage
from rdagent.utils import remove_ansi_codes

st.set_page_config(layout="wide", page_title="RD-Agent", page_icon="🎓", initial_sidebar_state="expanded")

# 设置主日志路径
if "log_folder" not in state:
    state.log_folder = Path("./log")
if "log_folders" not in state:
    state.log_folders = ["./log"]
if "log_path" not in state:
    state.log_path = None
if "show_all_summary" not in state:
    state.show_all_summary = True
if "show_stdout" not in state:
    state.show_stdout = False


def load_stdout():
    # FIXME: TODO: 使用配置项来指定stdout文件名
    stdout_path = state.log_folder / f"{state.log_path}.stdout"
    if stdout_path.exists():
        stdout = stdout_path.read_text()
    else:
        stdout = f"Please Set: {stdout_path}"
    return stdout


def extract_loopid_func_name(tag):
    """提取 Loop ID 和函数名称"""
    match = re.search(r"Loop_(\d+)\.([^.]+)", tag)
    return match.groups() if match else (None, None)


def extract_evoid(tag):
    """提取 EVO ID"""
    match = re.search(r"\.evo_loop_(\d+)\.", tag)
    return match.group(1) if match else None


# @st.cache_data
def load_data(log_path: Path):
    state.data = defaultdict(lambda: defaultdict(dict))
    state.times = defaultdict(lambda: defaultdict(dict))
    for msg in FileStorage(log_path).iter_msg():
        if msg.tag and "llm" not in msg.tag and "session" not in msg.tag:
            if msg.tag == "competition":
                state.data["competition"] = msg.content
                continue

            li, fn = extract_loopid_func_name(msg.tag)
            li = int(li)

            # read times
            loop_obj_path = log_path / "__session__" / f"{li}" / "4_record"
            if loop_obj_path.exists():
                state.times[li] = DataScienceRDLoop.load(loop_obj_path).loop_trace[li]

            ei = extract_evoid(msg.tag)
            msg.tag = re.sub(r"\.evo_loop_\d+", "", msg.tag)
            msg.tag = re.sub(r"Loop_\d+\.[^.]+\.?", "", msg.tag)
            msg.tag = msg.tag.strip()

            if ei:
                state.data[li][int(ei)][msg.tag] = msg.content
            else:
                if msg.tag:
                    state.data[li][fn][msg.tag] = msg.content
                else:
                    if not isinstance(msg.content, str):
                        state.data[li][fn] = msg.content


# @st.cache_data
def get_folders_sorted(log_path):
    """缓存并返回排序后的文件夹列表，并加入进度打印"""
    with st.spinner("正在加载文件夹列表..."):
        folders = sorted(
            (folder for folder in log_path.iterdir() if is_valid_session(folder)),
            key=lambda folder: folder.stat().st_mtime,
            reverse=True,
        )
        st.write(f"找到 {len(folders)} 个文件夹")
    return [folder.name for folder in folders]


# UI - Sidebar
with st.sidebar:
    log_folder_str = st.text_area(
        "**Log Folders**(split by ';')", placeholder=state.log_folder, value=";".join(state.log_folders)
    )
    state.log_folders = [folder.strip() for folder in log_folder_str.split(";") if folder.strip()]

    state.log_folder = Path(st.radio(f"Select :blue[**one log folder**]", state.log_folders))
    if not state.log_folder.exists():
        st.warning(f"Path {state.log_folder} does not exist!")

    folders = get_folders_sorted(state.log_folder)
    st.selectbox(f"Select from :blue[**{state.log_folder.absolute()}**]", folders, key="log_path")

    if st.button("Refresh Data"):
        if state.log_path is None:
            st.toast("Please select a log path first!", type="error")
            st.stop()

        load_data(state.log_folder / state.log_path)

    st.toggle("One Trace / Log Folder Summary", key="show_all_summary")
    st.toggle("Show stdout", key="show_stdout")


# UI windows
def task_win(data):
    with st.container(border=True):
        st.markdown(f"**:violet[{data.name}]**")
        st.markdown(data.description)
        if hasattr(data, "architecture"):  # model task
            st.markdown(
                f"""
    | Model_type | Architecture | hyperparameters |
    |------------|--------------|-----------------|
    | {data.model_type} | {data.architecture} | {data.hyperparameters} |
    """
            )


def workspace_win(data):
    show_files = {k: v for k, v in data.file_dict.items() if not "test" in k}
    if len(show_files) > 0:
        with st.expander(f"Files in :blue[{replace_ep_path(data.workspace_path)}]"):
            code_tabs = st.tabs(show_files.keys())
            for ct, codename in zip(code_tabs, show_files.keys()):
                with ct:
                    st.code(
                        show_files[codename],
                        language=("python" if codename.endswith(".py") else "markdown"),
                        wrap_lines=True,
                    )
    else:
        st.markdown("No files in the workspace")


def exp_gen_win(data):
    st.header("Exp Gen", divider="blue")
    st.subheader("Hypothesis")
    st.code(str(data.hypothesis).replace("\n", "\n\n"), wrap_lines=True)

    st.subheader("pending_tasks")
    for tasks in data.pending_tasks_list:
        task_win(tasks[0])
    st.subheader("Exp Workspace", anchor="exp-workspace")
    workspace_win(data.experiment_workspace)


def evolving_win(data):
    st.header("Code Evolving", divider="green")
    if len(data) > 1:
        evo_id = st.slider("Evolving", 0, len(data) - 1, 0)
    else:
        evo_id = 0

    if evo_id in data:
        if data[evo_id]["evolving code"][0] is not None:
            st.subheader("codes")
            workspace_win(data[evo_id]["evolving code"][0])
            fb = data[evo_id]["evolving feedback"][0]
            st.subheader("evolving feedback" + ("✅" if bool(fb) else "❌"), anchor="c_feedback")
            f1, f2, f3 = st.tabs(["execution", "return_checking", "code"])
            f1.code(fb.execution, wrap_lines=True)
            f2.code(fb.return_checking, wrap_lines=True)
            f3.code(fb.code, wrap_lines=True)
        else:
            st.write("data[evo_id]['evolving code'][0] is None.")
            st.write(data[evo_id])
    else:
        st.markdown("No evolving.")


def exp_after_coding_win(data):
    st.header("Exp After Coding", divider="blue")
    st.subheader("Exp Workspace", anchor="eac-exp-workspace")
    workspace_win(data.experiment_workspace)


def exp_after_running_win(data, mle_score):
    st.header("Exp After Running", divider="blue")
    st.subheader("Exp Workspace", anchor="ear-exp-workspace")
    workspace_win(data.experiment_workspace)
    st.subheader("Result")
    st.write(data.result)
    st.subheader("MLE Submission Score" + ("✅" if (isinstance(mle_score, dict) and mle_score["score"]) else "❌"))
    if isinstance(mle_score, dict):
        st.json(mle_score)
    else:
        st.code(mle_score, wrap_lines=True)


def feedback_win(data):
    st.header("Feedback" + ("✅" if bool(data) else "❌"), divider="orange")
    st.code(data, wrap_lines=True)
    if data.exception is not None:
        st.markdown(f"**:red[Exception]**: {data.exception}")


def sota_win(data):
    st.header("SOTA Experiment", divider="rainbow")
    if data:
        st.subheader("Exp Workspace", anchor="sota-exp-workspace")
        workspace_win(data.experiment_workspace)
    else:
        st.markdown("No SOTA experiment.")


def main_win(data):
    exp_gen_win(data["direct_exp_gen"])
    evo_data = {k: v for k, v in data.items() if isinstance(k, int)}
    evolving_win(evo_data)
    if "coding" in data:
        exp_after_coding_win(data["coding"])
    if "running" in data:
        exp_after_running_win(data["running"], data["mle_score"])
    if "feedback" in data:
        feedback_win(data["feedback"])
    sota_win(data["SOTA experiment"])

    with st.sidebar:
        st.markdown(
            f"""
- [Exp Gen](#exp-gen)
    - [Hypothesis](#hypothesis)
    - [pending_tasks](#pending-tasks)
    - [Exp Workspace](#exp-workspace)
- [Code Evolving ({len(evo_data)})](#code-evolving)
    - [codes](#codes)
    - [evolving feedback](#c_feedback)
{"- [Exp After Coding](#exp-after-coding)" if "coding" in data else ""}
{"- [Exp After Running](#exp-after-running)" if "running" in data else ""}
{"- [Feedback](#feedback)" if "feedback" in data else ""}
- [SOTA Experiment](#sota-experiment)
"""
        )


def replace_ep_path(p: Path):
    # 替换workspace path为对应ep机器mount在ep03的path
    # TODO: FIXME: 使用配置项来处理
    match = re.search(r"ep\d+", str(state.log_folder))
    if match:
        ep = match.group(0)
        return Path(
            str(p).replace("repos/RD-Agent-Exp", f"repos/batch_ctrl/all_projects/{ep}").replace("/Data", "/data")
        )
    return p


def summarize_data():
    st.header("Summary", divider="rainbow")
    df = pd.DataFrame(
        columns=["Component", "Running Score", "Feedback", "Time", "Start Time (UTC+8)", "End Time (UTC+8)"],
        index=range(len(state.data) - 1),
    )

    for loop in range(len(state.data) - 1):
        loop_data = state.data[loop]
        df.loc[loop, "Component"] = loop_data["direct_exp_gen"].hypothesis.component
        if state.times[loop]:
            df.loc[loop, "Time"] = str(sum((i.end - i.start for i in state.times[loop]), timedelta())).split(".")[0]
            df.loc[loop, "Start Time (UTC+8)"] = state.times[loop][0].start + timedelta(hours=8)
            df.loc[loop, "End Time (UTC+8)"] = state.times[loop][-1].end + timedelta(hours=8)
        if "running" in loop_data:
            if "mle_score" not in state.data[loop]:
                mle_score_path = (
                    replace_ep_path(loop_data["running"].experiment_workspace.workspace_path) / "mle_score.txt"
                )
                try:
                    mle_score_txt = mle_score_path.read_text()
                    state.data[loop]["mle_score"] = extract_mle_json(mle_score_txt)
                    if state.data[loop]["mle_score"]["score"] is not None:
                        df.loc[loop, "Running Score"] = str(state.data[loop]["mle_score"]["score"])
                    else:
                        state.data[loop]["mle_score"] = mle_score_txt
                        df.loc[loop, "Running Score"] = "❌"
                except Exception as e:
                    state.data[loop]["mle_score"] = str(e)
                    df.loc[loop, "Running Score"] = "❌"
            else:
                if isinstance(state.data[loop]["mle_score"], dict):
                    df.loc[loop, "Running Score"] = str(state.data[loop]["mle_score"]["score"])
                else:
                    df.loc[loop, "Running Score"] = "❌"

        else:
            df.loc[loop, "Running Score"] = "N/A"

        if "feedback" in loop_data:
            df.loc[loop, "Feedback"] = "✅" if bool(loop_data["feedback"]) else "❌"
        else:
            df.loc[loop, "Feedback"] = "N/A"
    st.dataframe(df)


def all_summarize_win():
    summarys = {}
    for lf in state.log_folders:
        if not (Path(lf) / "summary.pkl").exists():
            st.warning(
                f"No summary file found in {lf}\nRun:`dotenv run -- python rdagent/log/mle_summary.py grade_summary --log_folder=<your trace folder>`"
            )
        else:
            summarys[lf] = pd.read_pickle(Path(lf) / "summary.pkl")

    if len(summarys) == 0:
        return

    summary = {}
    for lf, s in summarys.items():
        for k, v in s.items():
            summary[f"{lf[lf.rfind('ep'):]}{k}"] = v

    summary = {k: v for k, v in summary.items() if "competition" in v}
    base_df = pd.DataFrame(
        columns=[
            "Competition",
            "Total Loops",
            "Successful Final Decision",
            "Made Submission",
            "Valid Submission",
            "V/M",
            "Above Median",
            "Bronze",
            "Silver",
            "Gold",
            "Any Medal",
            "SOTA Exp",
            "Ours - Base",
            "SOTA Exp Score",
            "Baseline Score",
            "Bronze Threshold",
            "Silver Threshold",
            "Gold Threshold",
            "Medium Threshold",
        ],
        index=summary.keys(),
    )

    # Read baseline results
    baseline_result_path = ""
    if Path(baseline_result_path).exists():
        baseline_df = pd.read_csv(baseline_result_path)

    for k, v in summary.items():
        loop_num = v["loop_num"]
        base_df.loc[k, "Competition"] = v["competition"]
        base_df.loc[k, "Total Loops"] = loop_num
        if loop_num == 0:
            base_df.loc[k] = "N/A"
        else:
            base_df.loc[k, "Successful Final Decision"] = (
                f"{v['success_loop_num']} ({round(v['success_loop_num'] / loop_num * 100, 2)}%)"
            )
            base_df.loc[k, "Made Submission"] = (
                f"{v['made_submission_num']} ({round(v['made_submission_num'] / loop_num * 100, 2)}%)"
            )
            base_df.loc[k, "Valid Submission"] = (
                f"{v['valid_submission_num']} ({round(v['valid_submission_num'] / loop_num * 100, 2)}%)"
            )
            if v["made_submission_num"] != 0:
                base_df.loc[k, "V/M"] = f"{round(v['valid_submission_num'] / v['made_submission_num'] * 100, 2)}%"
            else:
                base_df.loc[k, "V/M"] = "N/A"
            base_df.loc[k, "Above Median"] = (
                f"{v['above_median_num']} ({round(v['above_median_num'] / loop_num * 100, 2)}%)"
            )
            base_df.loc[k, "Bronze"] = f"{v['bronze_num']} ({round(v['bronze_num'] / loop_num * 100, 2)}%)"
            base_df.loc[k, "Silver"] = f"{v['silver_num']} ({round(v['silver_num'] / loop_num * 100, 2)}%)"
            base_df.loc[k, "Gold"] = f"{v['gold_num']} ({round(v['gold_num'] / loop_num * 100, 2)}%)"
            base_df.loc[k, "Any Medal"] = f"{v['get_medal_num']} ({round(v['get_medal_num'] / loop_num * 100, 2)}%)"

            baseline_score = None
            if Path(baseline_result_path).exists():
                baseline_score = baseline_df.loc[baseline_df["competition_id"] == v["competition"], "score"].item()

            base_df.loc[k, "SOTA Exp"] = v.get("sota_exp_stat", None)
            if (
                baseline_score is not None
                and not pd.isna(baseline_score)
                and not pd.isna(v.get("sota_exp_score", None))
            ):
                base_df.loc[k, "Ours - Base"] = v.get("sota_exp_score", 0.0) - baseline_score
            base_df.loc[k, "SOTA Exp Score"] = v.get("sota_exp_score", None)
            base_df.loc[k, "Baseline Score"] = baseline_score
            base_df.loc[k, "Bronze Threshold"] = v.get("bronze_threshold", None)
            base_df.loc[k, "Silver Threshold"] = v.get("silver_threshold", None)
            base_df.loc[k, "Gold Threshold"] = v.get("gold_threshold", None)
            base_df.loc[k, "Medium Threshold"] = v.get("median_threshold", None)

    base_df["SOTA Exp"].replace("", pd.NA, inplace=True)
    st.dataframe(base_df)
    total_stat = (
        (
            base_df[
                [
                    "Made Submission",
                    "Valid Submission",
                    "Above Median",
                    "Bronze",
                    "Silver",
                    "Gold",
                    "Any Medal",
                ]
            ]
            != "0 (0.0%)"
        ).sum()
        / base_df.shape[0]
        * 100
    )
    total_stat.name = "总体统计(%)"

    # SOTA Exp 统计
    se_counts = base_df["SOTA Exp"].value_counts(dropna=True)
    se_counts.loc["made_submission"] = se_counts.sum()
    se_counts.loc["Any Medal"] = se_counts.get("gold", 0) + se_counts.get("silver", 0) + se_counts.get("bronze", 0)
    se_counts.loc["above_median"] = se_counts.get("above_median", 0) + se_counts.get("Any Medal", 0)
    se_counts.loc["valid_submission"] = se_counts.get("valid_submission", 0) + se_counts.get("above_median", 0)

    sota_exp_stat = pd.Series(index=total_stat.index, dtype=int, name="SOTA Exp 统计(%)")
    sota_exp_stat.loc["Made Submission"] = se_counts.get("made_submission", 0)
    sota_exp_stat.loc["Valid Submission"] = se_counts.get("valid_submission", 0)
    sota_exp_stat.loc["Above Median"] = se_counts.get("above_median", 0)
    sota_exp_stat.loc["Bronze"] = se_counts.get("bronze", 0)
    sota_exp_stat.loc["Silver"] = se_counts.get("silver", 0)
    sota_exp_stat.loc["Gold"] = se_counts.get("gold", 0)
    sota_exp_stat.loc["Any Medal"] = se_counts.get("Any Medal", 0)
    sota_exp_stat = sota_exp_stat / base_df.shape[0] * 100

    stat_df = pd.concat([total_stat, sota_exp_stat], axis=1)
    st.dataframe(stat_df.round(2))

    # write curve
    for k, v in summary.items():
        with st.container(border=True):
            st.markdown(f"**:blue[{k}] - :violet[{v['competition']}]**")
            vscores = {k: v.iloc[:, 0] for k, v in v["valid_scores"].items()}
            tscores = {f"loop {k}": v for k, v in v["test_scores"].items()}
            if len(vscores) > 0:
                metric_name = list(vscores.values())[0].name
            else:
                metric_name = "None"

            fc1, fc2 = st.columns(2)
            try:
                vdf = pd.DataFrame(vscores)
                vdf.columns = [f"loop {i}" for i in vdf.columns]
                f1 = px.line(vdf.T, markers=True, title=f"Valid scores (metric: {metric_name})")
                fc1.plotly_chart(f1, key=f"{k}_v")

                tdf = pd.Series(tscores, name="score")
                f2 = px.line(tdf, markers=True, title="Test scores")
                fc2.plotly_chart(f2, key=k)
            except Exception as e:
                import traceback

                st.markdown("- Error: " + str(e))
                st.code(traceback.format_exc())
                st.markdown("- Valid Scores: ")
                st.json(vscores)
                st.markdown("- Test Scores: ")
                st.json(tscores)


def stdout_win(loop_id: int):
    stdout = load_stdout()
    if stdout.startswith("Please Set"):
        st.toast(stdout, icon="🟡")
        return
    start_index = stdout.find(f"Start Loop {loop_id}")
    end_index = stdout.find(f"Start Loop {loop_id + 1}")
    loop_stdout = remove_ansi_codes(stdout[start_index:end_index])
    with st.container(border=True):
        st.subheader(f"Loop {loop_id} stdout")
        pattern = f"Start Loop {loop_id}, " + r"Step \d+: \w+"
        matches = re.finditer(pattern, loop_stdout)
        step_stdouts = {}
        for match in matches:
            step = match.group(0)
            si = match.start()
            ei = loop_stdout.find(f"Start Loop {loop_id}", match.end())
            step_stdouts[step] = loop_stdout[si:ei].strip()

        for k, v in step_stdouts.items():
            expanded = True if "coding" in k else False
            with st.expander(k, expanded=expanded):
                st.code(v, language="log", wrap_lines=True)


# UI - Main
if state.show_all_summary:
    all_summarize_win()
elif "data" in state:
    st.title(state.data["competition"])
    summarize_data()
    loop_id = st.slider("Loop", 0, len(state.data) - 2, 0)
    if state.show_stdout:
        stdout_win(loop_id)
    main_win(state.data[loop_id])
