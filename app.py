import streamlit as st
import asyncio
import edge_tts
import os
import random
from pypdf import PdfReader
from docx import Document

# --- 1. 通用文档解析器 ---
def extract_text_from_file(uploaded_file):
    file_extension = uploaded_file.name.split(".")[-1].lower()
    text = ""
    if file_extension == "txt":
        text = uploaded_file.read().decode("utf-8", errors="ignore")
    elif file_extension == "pdf":
        reader = PdfReader(uploaded_file)
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text: text += page_text + "\n"
    elif file_extension in ["doc", "docx"]:
        doc = Document(uploaded_file)
        for para in doc.paragraphs: text += para.text + "\n"
    return text.strip()

# --- 2. 严谨的记忆点抽取与挖空算法 ---
def generate_quiz_questions(text):
    if len(text) < 15:
        return []
    sentences = [s.strip() for s in text.replace("；", "。").replace("\n", "。").split("。") if len(s.strip()) > 10]
    if not sentences:
        return []
    
    quizzes = []
    sample_size = min(2, len(sentences))
    chosen_sentences = random.sample(sentences, sample_size)
    
    for q_text in chosen_sentences:
        keywords = ["核心", "基础", "根本", "实质", "特征", "要求", "主要", "关键", "定义", "内涵", "包括"]
        blank_word = "【核心概念】"
        for kw in keywords:
            if kw in q_text:
                blank_word = kw
                break
        
        if blank_word == "【核心概念】" and len(q_text) > 20:
            split_pos = len(q_text) // 2
            question = q_text[:split_pos] + "______"
            answer = q_text[split_pos:]
        else:
            question = q_text.replace(blank_word, "______")
            answer = blank_word
            
        quizzes.append({"question": question, "answer": q_text})
    return quizzes

# --- 3. 语音合成接口 ---
async def amain(text, voice, rate, output_filename) -> None:
    communicate = edge_tts.Communicate(text, voice, rate=rate)
    await communicate.save(output_filename)

# --- 4. 主界面逻辑与高级 UI 注入 ---
def main():
    # 严格将初始化代码置于最前，避免 TypeError 冲突
    st.set_page_config(page_title="EchoMind | 智能复述与记忆自测系统", page_icon="🧠", layout="centered")

    # 致敬 Type Words 风格的极简高级自定义 CSS
    custom_css = """
    <style>
        /* 浅色多色调高雅渐变底色 */
        .stApp {
            background: linear-gradient(135deg, #F4F7FB 0%, #E8EEF9 100%) !important;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        }
        
        /* 隐藏原生组件，增强封装感 */
        header, footer {visibility: hidden;}
        
        /* 极简现代化大标题与副标题 */
        .brand-title {
            font-size: 3.2rem;
            font-weight: 800;
            background: linear-gradient(45deg, #7B2CBF, #3A86FF);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            text-align: center;
            margin-top: 1rem;
            margin-bottom: 0.2rem;
            letter-spacing: -0.06rem;
        }
        .brand-subtitle {
            font-size: 1.05rem;
            color: #6C757D;
            text-align: center;
            margin-bottom: 2.5rem;
        }
        
        /* 具有呼吸感的白色圆角卡片化设计 */
        .stTextArea textarea, .stFileUploader, div[data-testid="stForm"], .stTabs {
            background-color: rgba(255, 255, 255, 0.95) !important;
            border-radius: 16px !important;
            border: 1px solid rgba(226, 232, 240, 0.8) !important;
            box-shadow: 0 4px 24px rgba(0, 0, 0, 0.02) !important;
            padding: 10px !important;
        }
        
        /* 侧边栏高级灰色调与边界线 */
        section[data-testid="stSidebar"] {
            background-color: #F8F9FA !important;
            border-right: 1px solid #E9ECEF;
        }
        
        /* 全宽、高质感扁平化渐变主按钮 */
        .stButton>button {
            background: linear-gradient(90deg, #3A86FF 0%, #4CC9F0 100%) !important;
            color: white !important;
            border: none !important;
            padding: 0.7rem 2rem !important;
            border-radius: 12px !important;
            font-weight: 600 !important;
            font-size: 1rem !important;
            box-shadow: 0 4px 14px rgba(58, 134, 255, 0.25) !important;
            transition: all 0.2s ease !important;
            width: 100%;
            margin-top: 1rem;
        }
        .stButton>button:hover {
            transform: translateY(-1px) !important;
            box-shadow: 0 6px 20px rgba(58, 134, 255, 0.35) !important;
        }
    </style>
    """
    st.markdown(custom_css, unsafe_html=True)

    # 显示高端品牌标识与中性化严谨副标题
    st.markdown('<div class="brand-title">EchoMind</div>', unsafe_html=True)
    st.markdown('<div class="brand-subtitle">面向深度记忆、学术背诵、职场考证与文本复述的科学自测工具</div>', unsafe_html=True)

    # 侧边栏：参数科学配置
    st.sidebar.markdown("### 🎛️ 语音与时间管理")
    
    # 彻底去除具体地域标签，按声线场景严谨划分
    voice_options = {
        "标准清晰 · 叙事女声 (晓晓)": "zh-CN-XiaoxiaoNeural",
        "沉稳理性 · 教学男声 (云希)": "zh-CN-YunxiNeural",
        "纪录片风 · 浑厚男声 (云扬)": "zh-CN-YunyangNeural",
        "自然流畅 · 日常女声 (晓北)": "zh-LN-XiaobeiNeural",
        "温润和缓 · 宣讲女声 (晓伊)": "zh-CN-XiaoyiNeural",
        "电台质感 · 抒情女声 (晓辰)": "zh-CN-XiaochenNeural",
        "清爽开朗 · 青年男声 (云夏)": "zh-CN-YunxiaNeural",
        "饱满宏亮 · 演讲男声 (云健)": "zh-CN-YunjianNeural"
    }
    selected_voice_label = st.sidebar.selectbox("选择复述声线特质", list(voice_options.keys()))
    voice = voice_options[selected_voice_label]

    speed = st.sidebar.slider("语速精调 (0为标准语速)", min_value=-50, max_value=100, value=10, step=10)
    speed_str = f"+{speed}%" if speed >= 0 else f"{speed}%"

    # 循环机制配置
    loop_mode = st.sidebar.radio("配置复述机制", ["定量（按遍数循环）", "定长（按时长磨耳朵）"])
    loop_count = 1
    duration_min = 0
    
    if loop_mode == "定量（按遍数循环）":
        loop_count = st.sidebar.number_input("循环复述遍数", min_value=1, max_value=50, value=3)
    else:
        time_options = {"5分钟": 5, "10分钟": 10, "15分钟": 15, "30分钟": 30, "45分钟": 45, "1小时": 60}
        selected_time = st.sidebar.selectbox("选择磨耳朵持续时间", list(time_options.keys()))
        duration_min = time_options[selected_time]

    # 输出检测模块配置
    st.sidebar.write("---")
    st.sidebar.markdown("### ❓ 主动回忆输出检测")
    enable_quiz = st.sidebar.checkbox("开启复述后的随机效果抽查", value=True)
    
    quiz_mode = "交互式电子答题"
    wait_time = 5
    if enable_quiz:
        quiz_mode = st.sidebar.radio("测试形式", ["📱 交互式电子答题", "🔊 语音播报问题"])
        if quiz_mode == "🔊 语音播报问题":
            wait_time = st.sidebar.slider("留给脑海中思索答案的时间 (秒)", min_value=5, max_value=15, value=10, step=5)

    # 主界面输入区域卡片
    tab1, tab2 = st.tabs(["📝 纯文本录入", "📂 本地文档解析 (PDF/Word/TXT)"])
    input_text = ""

    with tab1:
        input_text = st.text_area("请在此录入需要复述记忆的专业文本、法律条文、演讲学术讲义或台词剧本：", height=220, placeholder="支持任意学科及文本内容...")

    with tab2:
        uploaded_file = st.file_uploader("支持解析主流格式：PDF, DOCX, TXT", type=["txt", "pdf", "doc", "docx"])
        if uploaded_file is not None:
            with st.spinner("正在安全解析文档内容..."):
                input_text = extract_text_from_file(uploaded_file)
            st.success("文档内容解析成功！")

    # 执行合成
    if st.button("🚀 编译并生成复述记忆系统"):
        if not input_text.strip():
            st.warning("⚠️ 请先录入需要复述的文本内容！")
            return

        with st.spinner("系统正在为您构建复述音频与记忆盲盒..."):
            # 组织文本
            final_text = ""
            if loop_mode == "定量（按遍数循环）":
                for i in range(loop_count):
                    final_text += f"第{i+1}遍。 {input_text} \n\n "
            else:
                estimated_words_needed = duration_min * 280
                current_words = len(input_text)
                repeats = max(1, estimated_words_needed // current_words)
                for i in range(repeats):
                    final_text += f"第{i+1}轮循环。 {input_text} \n\n "

            # 智能挖空逻辑接入
            quiz_data = []
            if enable_quiz:
                quiz_data = generate_quiz_questions(input_text)
                if quiz_data and quiz_mode == "🔊 语音播报问题":
                    final_text += " \n\n 复述环节已结束，下面进入主动回忆与输出抽查环节。请听题。 "
                    for idx, q in enumerate(quiz_data):
                        final_text += f"第{idx+1}题，请补充缺失内容：{q['question']} 。。。 请在倒计时中思考答案。 "
                        final_text += " 。 " * (wait_time // 2)
                        final_text += f" 思考时间结束。参考原文为：{q['answer']} 。 "
                    final_text += " 深度自测结束，祝您早日完成记忆目标！"

            # 异步写入独立存储区
            output_filename = "professional_recitation.mp3"
            asyncio.run(amain(final_text, voice, speed_str, output_filename))

            st.session_state['quiz_data'] = quiz_data
            st.session_state['quiz_mode'] = quiz_mode
            st.session_state['enable_quiz'] = enable_quiz

        st.success("🎉 复述系统编译完成！")
        st.audio(output_filename, format="audio/mpeg")
        st.download_button(label="📥 导出独立音频文件 (MP3)", data=open(output_filename, "rb").read(), file_name="EchoMind_Audio.mp3")

        # 闭环测试面板展示
        if enable_quiz and quiz_data:
            st.write("---")
            st.markdown("### 📝 记忆效果深度自测面板")
            st.caption("建议听完上方音频后回到此处作答，通过“检索输出”强化大脑神经元连接。")
            
            for idx, q in enumerate(quiz_data):
                st.markdown(f"**📍 随机盲查第 {idx+1} 题：**")
                st.code(q['question'])
                
                if quiz_mode == "📱 交互式电子答题":
                    st.text_input(f"请输入您记忆中缺失的核心词或原句 (第{idx+1}题)", key=f"user_ans_{idx}")
                    with st.expander("🔍 核对标准参考原句"):
                        st.success(q['answer'])
                else:
                    st.caption("提示：本题已包含在复述音频的末尾，您可在盲听时同步思考。")
                    with st.expander("🔍 查看文字版题目与标准答案对照"):
                        st.write(f"问题句：{q['question']}")
                        st.success(f"参考句：{q['answer']}")

if __name__ == "__main__":
    main()
