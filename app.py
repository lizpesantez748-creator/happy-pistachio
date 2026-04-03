import streamlit as st
import pandas as pd
import json
import os
import random
import io
import requests
from datetime import datetime
import dashscope

# --- 1. 核心配置区 ---
# API Keys (建议后续移至 Streamlit Secrets 以增强安全性)
dashscope.api_key = "sk-bf4a0247050847988ca64c9bebb6f57d"
OCR_ID = "LTAI5tLHeLfxd13CpoqzrjBH"
OCR_SECRET = "hCRQKsFsBjES4mUUoFSCXDsrgSVsic"

# 文件路径适配 Cloud 环境
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
JSON_FILE = os.path.join(CURRENT_DIR, "medicine_data.json")

# --- 2. 页面与样式配置 (手机端适配) ---
st.set_page_config(page_title="开心果", page_icon="🥑", layout="wide")

st.markdown("""
    <style>
    /* 全局背景与字体颜色 */
    .stApp { background-color: #FDFCF0; }
    h1, h2, h3 { color: #548235 !important; }

    /* 手机端按钮加高加宽 */
    div.stButton > button {
        width: 100%;
        height: 3.5rem;
        border-radius: 15px;
        background-color: #70AD47 !important;
        color: white !important;
        font-weight: bold;
    }

    /* 聊天气泡样式 */
    [data-testid="stChatMessage"] {
        border-radius: 20px;
        background-color: #E2EFDA;
        margin-bottom: 10px;
    }

    /* 隐藏冗余白边 */
    .block-container { padding-top: 1.5rem; }
    </style>
    """, unsafe_allow_html=True)


# --- 3. 核心功能函数 ---

def ask_qwen(messages):
    """带记忆的通义千问调用"""
    try:
        response = dashscope.Generation.call(
            model=dashscope.Generation.Models.qwen_turbo,
            messages=messages,
            result_format='message'
        )
        if response.status_code == 200:
            return response.output.choices[0].message.content
        return "我咋会断线了呢~"
    except Exception as e:
        return f"AI 呼叫失败: {str(e)}"
@st.cache_data(ttl="1d")
def get_ai_greeting():
    """让 AI 生成一句温馨的每日寄语"""
    prompt = """
    你是一个名叫‘开心果’的温馨家庭健康助手。
    请生成一句简短的每日寄语（30字以内）。
    要求：语气治愈、贴心，包含健康提醒或心情鼓励。
    不要带标题，不要带引号，直接输出话语。
    例如：阳光正好，记得开窗通风，喝一杯温水开启元气满满的一天哦！
    """
    try:
        response = dashscope.Generation.call(
            model=dashscope.Generation.Models.qwen_turbo,
            messages=[{'role': 'user', 'content': prompt}],
            result_format='message'
        )
        if response.status_code == 200:
            return response.output.choices[0].message.content
        return "只要心中有阳光，每天都是好天气。记得按时吃饭哦！" # 备用方案
    except:
        return "开心果永远守护你的健康，今天也要加油呀！"
def get_ocr_text_simulated():
    """由于 SDK 安装问题，此处使用 AI 辅助模拟识别流程"""
    # 实际部署时，若能解决环境问题可换回真实 OCR 调用
    return "药品：感冒灵颗粒 EXP: 2027-05-20 用法：开水冲服，一次一袋，一日三次。类别：感冒发热"


# --- 4. 数据初始化 ---
if os.path.exists(JSON_FILE):
    with open(JSON_FILE, 'r', encoding='utf-8') as f:
        inventory = json.load(f)
else:
    inventory = []

# --- 5. 界面渲染 ---
st.title("🥑 开心果")

daily_wish = get_ai_greeting()
st.info(f"🥑 {daily_wish}")

# --- 功能 A：智能录入 (手机拍照适配) ---
with st.expander("📷 拍照/上传药盒入库"):
    file = st.file_uploader("拍一下说明书的药物说明", type=['jpg', 'png', 'jpeg'])
    if file:
        st.image(file, width=200)
        if st.button("✨ 智能识别并入库"):
            with st.spinner("正在认领药品..."):
                # 识别逻辑 (此处暂用模拟文本配合 AI 解析)
                raw_text = get_ocr_text_simulated()
                prompt = f"请从以下文字提取信息并返回JSON(名称, 类别, 有效期YYYY-MM-DD, 用法): {raw_text}"
                ai_res = ask_qwen([{"role": "user", "content": prompt}])
                try:
                    clean_json = ai_res.split('```json')[-1].split('```')[0].strip()
                    item = json.loads(clean_json)
                    item['数量'] = 1
                    inventory.append(item)
                    with open(JSON_FILE, 'w', encoding='utf-8') as f:
                        json.dump(inventory, f, ensure_ascii=False, indent=4)
                    st.success(f"✅ 成功录入：{item['名称']}")
                    st.balloons()
                    st.rerun()
                except:
                    st.error("识别信息整理失败，请再试一次。")

# --- 界面布局：清单与聊天 ---
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("📋 我的药箱")
    if inventory:
        df = pd.DataFrame(inventory)
        search = st.text_input("🔍 搜索药名/类别", placeholder="如：感冒")
        if search:
            df = df[df['名称'].str.contains(search) | df['类别'].str.contains(search)]

        # 针对手机精简表格
        st.dataframe(df[['名称', '有效期', '类别']], use_container_width=True, hide_index=True)
    else:
        st.caption("药箱空空如也，快上传照片试试！")

with col2:
    st.subheader("💬 咨询一下开心果吧")
    if "msgs" not in st.session_state:
        st.session_state.msgs = []

    # 聊天记录显示
    for m in st.session_state.msgs:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])

    if p := st.chat_input("哪里不舒服呀？"):
        st.session_state.msgs.append({"role": "user", "content": p})
        with st.chat_message("user"): st.markdown(p)

        with st.chat_message("assistant"):
            sys_msg = {"role": "system",
                       "content": f"你是温馨助手‘开心果’，你的性格想你的名字一样阳光、治愈，说话语气要亲切。你的任务是根据主人的症状，从【药箱库存】中推荐合适的药品....当前药箱库存：{json.dumps(inventory, ensure_ascii=False)}。请根据库存亲切回答。"}
            r = ask_qwen([sys_msg] + st.session_state.msgs)
            st.markdown(r)
            st.session_state.msgs.append({"role": "assistant", "content": r})