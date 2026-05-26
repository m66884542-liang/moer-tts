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

# --- 4. 核心：高级仿 Type Words 弹窗设置面板 ---
@st.dialog("系统设置", width="large")
def show_settings_dialog():
    st.caption("自定义调配您的复述声线、循环机制与自测盲盒")
    st.write("---")
    
    # 采用 1:2 两栏布局，完美复刻 Type Words 的设置逻辑
    left_menu, right_content = st.columns([1, 2.2], gap="large")
    
    with left_menu:
        # 左侧垂直分类导航（隐藏原生边框，做成纯文本菜单感）
        setting_tab = st.radio(
            "配置分类",
            ["🔊 语音特质调校", "⏳ 循环记忆机制", "❓ 记忆输出抽查"],
            label_visibility="collapsed"
        )
        
    with right_content:
        # 右侧根据左侧的点击动态渲染具体内容
        if setting_tab == "🔊 语音特质调校":
            st.markdown("##### 🔊 语音特质调校")
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
            selected_label = st.selectbox("选择复述声线特质", list(voice_options.keys()), index=0)
            st.session_state['voice'] = voice_options[selected_label]
            st.session_state['voice_label'] = selected_label

            speed = st.slider("语速精调 (0为标准语速)", min_value=-50, max_value=100, value=st.session_state.get('speed_val', 10), step=10)
            st.session_state['speed_val'] = speed
            st.session_state['speed_str'] = f"+{speed}%" if speed >= 0 else f"{speed}%"

        elif setting_tab == "⏳ 循环记忆机制":
            st.markdown("##### ⏳ 循环记忆机制")
            loop_mode = st.radio("配置复述机制", ["定量（按遍数循环）", "定长（按时长磨耳朵）"], index=0 if st.session_state.get('loop_mode', "定量（按遍数循环）") == "定量（按遍数循环）" else 1)
            st.session_state['loop_mode'] = loop_mode
            
            if loop_mode == "定量（按遍数循环）":
                st.session_state['loop_count'] = st.number_input("循环复述遍数", min_value=1, max_value=50, value=st.session_state.get('loop_count', 3))
            else:
                time_options = {"5分钟": 5, "10分钟": 10, "15分钟": 15, "30分钟": 30, "45分钟": 45, "1小时": 60}
                selected_time = st.selectbox("选择磨耳朵持续时间", list(time_options.keys()))
                st.session_state['duration_min'] = time_options[selected_time]

        elif setting_tab == "❓ 记忆输出抽查":
            st.markdown("##### ❓ 记忆输出抽查")
            enable_quiz = st.checkbox("开启复述后的效果抽查", value=st.session_state.get('enable_quiz', True))
            st.session_state['enable_quiz'] = enable_quiz
            
            if enable_quiz:
                quiz_mode = st.radio("自测答题形式", ["📱 交互式电子答题", "🔊 语音播报问题"], index=0 if st.session_state.get('quiz_mode', "📱 交互式电子答题") == "📱 交互式电子答题" else 1)
                st.session_state['quiz_mode'] = quiz_mode
                if quiz_mode == "🔊 语音播报问题":
                    st.session_state['wait_time'] = st.slider("留给脑海中思索答案的时间 (秒)", min_value=5, max_value=15, value=st.session_state.get('wait_time', 10), step=5)

    st.write("---")
    if st.button("保存并应用配置", use_container_width=True):
        st.rerun()

# --- 5. 主界面逻辑 ---
def main():
    st.set_page_config(page_title="EchoMind | 智能复述与记忆自测系统", page_icon="🧠", layout="centered")

    # 初始化会话全局默认状态
    if 'voice' not in st.session_state: st.session_state['voice'] = "zh-CN-XiaoxiaoNeural"
    if 'voice_label' not in st.session_state: st.session_state['voice_label'] = "标准清晰 · 叙事女声 (晓晓)"
    if 'speed_str' not in st.session_state: st.session_state['speed_str'] = "+10%"
    if 'loop_mode' not in st.session_state: st.session_state['loop_mode'] = "定量（按遍数循环）"
    if 'loop_count' not in st.session_state: st.session_state['loop_count'] = 3
    if 'enable_quiz' not in st.session_state: st.session_state['enable_quiz'] = True
    if 'quiz_mode' not in st.session_state: st.session_state['quiz_mode'] = "📱 交互式电子答题"

    # 注入全局 CSS 样式（隐藏拉伸手柄、精致化顶部布局）
    st.html("""
    <style>
        .stTextArea textarea { resize: none !important; }
        .gradient-brand-title {
            font-size: 3.5rem; font-weight: bold; font-family: 'Georgia', serif; font-style: italic;
            letter-spacing: -0.05rem; text-align: center; margin-top: 1rem; margin-bottom: 0.1rem;
            background: linear-gradient(135deg, #0288D1 20%, #F06292 80%);
            -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
        }
        .brand-subtitle-text { font-size: 0.95rem; color: #64748B; text-align: center; margin-bottom: 1.5rem; }
        
        /* 仿 Type Words 左侧菜单高亮样式微调 */
        div[data-testid="stRadio"] iframe { display: none; }
    </style>
    """)

    # 顶部工具栏：左侧是渐变 Logo，右侧是极简设置按钮
    header_col, btn_col = st.columns([5, 1])
    with header_col:
        st.html('<div class="gradient-brand-title">EchoMind</div>')
    with btn_col:
        st.write("") # 错位对齐
        st.write("") 
        if st.button("⚙️ 设置", help="点击打开 Type Words 风格设置面板"):
            show_settings_dialog()

    st.html('<div class="brand-subtitle-text">面向深度记忆、学术背诵与文本复述的科学自测工具</div>')

    # 当前配置微型状态提示条
    st.caption(f"当前配置：{st.session_state['voice_label']} | {st.session_state['loop_mode']} | 效果抽查: {'开启' if st.session_state['enable_quiz'] else '关闭'}")

    # 主界面输入区域
    tab1, tab2 = st.tabs(["📝 纯文本录入", "📂 本地文档解析 (PDF/Word/TXT)"])
    input_text = ""

    with tab1:
        input_text = st.text_area("请在此录入需要复述记忆的专业文本...", height=220, placeholder="支持任意学科及文本内容...")

    with tab2:
        uploaded_file = st.file_uploader("支持解析主流格式：PDF, DOCX, TXT", type=["txt", "pdf", "doc", "docx"])
        if uploaded_file is not None:
            with st.spinner("正在安全解析文档内容..."):
                input_text = extract_text_from_file(uploaded_file)
            st.success("文档内容解析成功！")

    # 执行生成
    if st.button("🚀 编译并生成复述记忆系统", use_container_width=True):
        if not input_text.strip():
            st.warning("⚠️ 请先录入需要复述的文本内容！")
            return

        with st.spinner("系统正在为您构建复述音频与记忆盲盒..."):
            final_text = ""
            if st.session_state['loop_mode'] == "定量（按遍数循环）":
                for i in range(st.session_state['loop_count']):
                    final_text += f"第{i+1}遍。 {input_text} \n\n "
            else:
                estimated_words_needed = st.session_state.get('duration_min', 5) * 280
                repeats = max(1, estimated_words_needed // len(input_text))
                for i in range(repeats):
                    final_text += f"第{i+1}轮循环。 {input_text} \n\n "

            quiz_data = []
            if st.session_state['enable_quiz']:
                quiz_data = generate_quiz_questions(input_text)
                if quiz_data and st.session_state['quiz_mode'] == "🔊 语音播报问题":
                    final_text += " \n\n 复述环节已结束，下面进入主动回忆与输出抽查环节。请听题。 "
                    for idx, q in enumerate(quiz_data):
                        final_text += f"第{idx+1}题，请补充缺失内容：{q['question']} 。。。 请在倒计时中思考答案。 "
                        final_text += " 。 " * (st.session_state.get('wait_time', 10) // 2)
                        final_text += f" 思考时间结束。参考原文为：{q['answer']} 。 "
                    final_text += " 深度自测结束，祝您早日完成记忆目标！"

            output_filename = "professional_recitation.mp3"
            asyncio.run(amain(final_text, st.session_state['voice'], st.session_state['speed_str'], output_filename))

            st.session_state['current_quiz_data'] = quiz_data

        st.success("🎉 复述系统编译完成！")
        st.audio(output_filename, format="audio/mpeg")
        st.download_button(label="📥 导出独立音频文件 (MP3)", data=open(output_filename, "rb").read(), file_name="EchoMind_Audio.mp3", use_container_width=True)

        # 闭环测试面板展示
        if st.session_state['enable_quiz'] and st.session_state.get('current_quiz_data'):
            st.write("---")
            st.markdown("### 📝 记忆效果深度自测面板")
            
            for idx, q in enumerate(st.session_state['current_quiz_data']):
                st.write(f"**📍 随机盲查第 {idx+1} 题：**")
                st.code(q['question'])
                
                if st.session_state['quiz_mode'] == "📱 交互式电子答题":
                    st.text_input(f"请输入您记忆中缺失的核心词或原句 (第{idx+1}题)", key=f"user_ans_{idx}")
                    with st.expander("🔍 核对标准参考原句"):
                        st.success(q['answer'])
                else:
                    with st.expander("🔍 查看文字版题目与标准答案对照"):
                        st.write(f"问题句：{q['question']}")
                        st.success(f"参考句：{q['answer']}")

if __name__ == "__main__":
    main()
