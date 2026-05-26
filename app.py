import streamlit as st
import asyncio
import edge_tts
import os
import random
import time
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

# --- 2. 智能随机提取与挖空算法（通用文本记忆适用） ---
def generate_quiz_questions(text):
    if len(text) < 10:
        return []
    # 统一按句号或换行切分
    sentences = [s.strip() for s in text.replace("；", "。").replace("\n", "。").split("。") if len(s.strip()) > 8]
    if not sentences:
        return []
    
    quizzes = []
    # 随机抽取不超过2个代表性句子进行盲测提问
    sample_size = min(2, len(sentences))
    chosen_sentences = random.sample(sentences, sample_size)
    
    for q_text in chosen_sentences:
        # 提取高频逻辑词作为挖空参考
        keywords = ["因为", "所以", "核心", "基础", "根本", "实质", "特征", "要求", "主要", "矛盾", "由于", "包括"]
        blank_word = "【关键点】"
        for kw in keywords:
            if kw in q_text:
                blank_word = kw
                break
        
        if blank_word == "【关键点】" and len(q_text) > 15:
            # 文本较长且无显式逻辑词时，截取后半段引导深度回忆
            split_pos = len(q_text) // 2
            question = q_text[:split_pos] + "______？"
            answer = q_text[split_pos:]
        else:
            question = q_text.replace(blank_word, "______") + " （请问横线处缺失的词或概念是什么？）"
            answer = blank_word
            
        quizzes.append({"question": question, "answer": q_text})
    return quizzes

# --- 3. 异步语音合成接口 ---
async def amain(text, voice, rate, output_filename) -> None:
    communicate = edge_tts.Communicate(text, voice, rate=rate)
    await communicate.save(output_filename)

# --- 4. 网页主程序界面（全人群通用版） ---
def main():
    st.set_page_config(page_title="智能复述与记忆自测平台", page_icon="🧠", layout="centered")
    st.title("🧠 智能复述与记忆自测平台")
    st.caption("面向考证、学术背诵、语言学习及剧本记忆的深度高效复述与自测系统。")

    # 侧边栏：参数科学配置
    st.sidebar.header("🎛️ 1. 语音及时间管理")
    
    # 语音特质严谨化调整，去除具体省份/地域标签，改用声线特质与标准分类
    voice_options = {
        "🎙️ 晓晓 (标准清晰 - 女声)": "zh-CN-XiaoxiaoNeural",
        "🎙️ 云希 (稳重沉稳 - 男声)": "zh-CN-YunxiNeural",
        "🎙️ 云扬 (纪录片播音 - 男声)": "zh-CN-YunyangNeural",
        "🎙️ 晓辰 (知名电台播音 - 女声)": "zh-CN-XiaochenNeural",
        "🎙️ 晓伊 (温润教学 - 女声)": "zh-CN-XiaoyiNeural",
        "🎙️ 云夏 (朝气青年 - 男声)": "zh-CN-YunxiaNeural",
        "🎙️ 云健 (饱满热烈 - 男声)": "zh-CN-YunjianNeural",
        "🎙️ 晓北 (自然日常 - 女声)": "zh-LN-XiaobeiNeural",
        "🎙️ 云西 (平实叙述 - 男声)": "zh-SC-YunxiNeural",
        "🎙️ 晓妮 (沉静叙事 - 女声)": "zh-CN-shaanxi-XiaoniNeural"
    }
    selected_voice_label = st.sidebar.selectbox("选择复述声线特质", list(voice_options.keys()))
    voice = voice_options[selected_voice_label]

    speed = st.sidebar.slider("语速调节 (0为正常语速)", min_value=-50, max_value=100, value=10, step=10)
    speed_str = f"+{speed}%" if speed >= 0 else f"{speed}%"

    # 循环模式配置
    loop_mode = st.sidebar.radio("循环机制", ["按遍数循环", "按设定时长磨耳朵"])
    loop_count = 1
    duration_min = 0
    
    if loop_mode == "按遍数循环":
        loop_count = st.sidebar.number_input("循环复述遍数", min_value=1, max_value=50, value=3)
    else:
        time_options = {"5分钟": 5, "10 minutes": 10, "15分钟": 15, "30分钟": 30, "45分钟": 45, "1小时": 60}
        selected_time = st.sidebar.selectbox("选择持续时间", list(time_options.keys()))
        duration_min = time_options[selected_time]

    # 自测模块配置
    st.sidebar.write("---")
    st.sidebar.header("❓ 2. 主动回忆与输出检测")
    enable_quiz = st.sidebar.checkbox("开启复述后的随机效果抽查", value=True)
    
    quiz_mode = "交互式电子答题"
    wait_time = 5
    if enable_quiz:
        quiz_mode = st.sidebar.radio("检测形式", ["📱 交互式电子答题", "🔊 语音播报问题"])
        if quiz_mode == "🔊 语音播报问题":
            wait_time = st.sidebar.slider("留给脑海中思索答案的时间 (秒)", min_value=5, max_value=15, value=10, step=5)

    # 主界面输入模块
    tab1, tab2 = st.tabs(["📝 纯文本录入", "📂 本地文档解析(PDF/Word)"])
    input_text = ""

    with tab1:
        input_text = st.text_area("请在此粘贴或输入需要复述记忆的专业文本、法条、讲义或剧本台词：", height=200, placeholder="支持任意学科及语言的文本内容...")

    with tab2:
        uploaded_file = st.file_uploader("支持上传主流格式：PDF, DOCX, TXT", type=["txt", "pdf", "doc", "docx"])
        if uploaded_file is not None:
            with st.spinner("正在安全解析文档内容..."):
                input_text = extract_text_from_file(uploaded_file)
            st.success("文档解析完毕！")

    # 执行音频与试题合成
    if st.button("🚀 编译并生成复述系统", type="primary"):
        if not input_text.strip():
            st.warning("⚠️ 请先录入需要复述的文本或上传文档！")
            return

        with st.spinner("系统正在为您重组复述音频与测试盲盒..."):
            # 组织最终播放文本
            final_text = ""
            if loop_mode == "按遍数循环":
                for i in range(loop_count):
                    final_text += f"第{i+1}遍。 {input_text} \n\n "
            else:
                # 按照1分钟约300字粗略估算时长所需的文本复制量
                estimated_words_needed = duration_min * 300
                current_words = len(input_text)
                repeats = max(1, estimated_words_needed // current_words)
                for i in range(repeats):
                    final_text += f"第{i+1}轮循环。 {input_text} \n\n "

            # 融合智能出题逻辑
            quiz_data = []
            if enable_quiz:
                quiz_data = generate_quiz_questions(input_text)
                if quiz_data and quiz_mode == "🔊 语音播报问题":
                    final_text += " \n\n 复述环节已结束，下面进入主动回忆与输出抽查环节。请听题。 "
                    for idx, q in enumerate(quiz_data):
                        final_text += f"第{idx+1}题：{q['question']} 。。。 请在倒计时中思考答案。 "
                        final_text += " 。 " * (wait_time // 2)  # 用句号模拟自然的静音间隔
                        final_text += f" 思考时间结束。参考原文为：{q['answer']} 。 "
                    final_text += " 深度自测结束，祝您早日完成记忆目标！"

            # 异步合成写入
            output_filename = "professional_recitation.mp3"
            asyncio.run(amain(final_text, voice, speed_str, output_filename))

            # 缓存试题以防交互刷新
            st.session_state['quiz_data'] = quiz_data
            st.session_state['quiz_mode'] = quiz_mode
            st.session_state['enable_quiz'] = enable_quiz

        st.success("🎉 复述系统编译完成！")
        
        with open(output_filename, "rb") as audio_file:
            audio_bytes = audio_file.read()
            st.audio(audio_bytes, format="audio/mpeg")
            st.download_button(label="📥 下载独立音频文件 (MP3)", data=audio_bytes, file_name="专属复述音频.mp3")

        # 闭环测试面板展示
        if enable_quiz and quiz_data:
            st.write("---")
            st.subheader("📝 记忆效果深度自测面板")
            st.info("💡 建议：您可以听完上方音频后回到此处作答，或直接利用本面板进行模拟默写。")
            
            for idx, q in enumerate(quiz_data):
                st.markdown(f"**📍 随机记忆盲查第 {idx+1} 题：**")
                st.code(q['question'])
                
                if quiz_mode == "📱 交互式电子答题":
                    user_ans = st.text_input(f"请输入您的关键记忆或核心短语 (第{idx+1}题)", key=f"user_ans_{idx}")
                    with st.expander("🔍 展开核对标准参考原句"):
                        st.success(q['answer'])
                else:
                    st.caption("提示：本题已包含在复述音频的尾部中，您可以进行盲听作答。")
                    with st.expander("🔍 展开核对文字版题目与参考答案"):
                        st.write(f"问题句：{q['question']}")
                        st.success(f"参考句：{q['answer']}")

if __name__ == "__main__":
    main()
