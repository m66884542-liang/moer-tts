import streamlit as st
import asyncio
import edge_tts
import os
import random
import time
from pypdf import PdfReader
from docx import Document

# --- 1. 文档解析器 ---
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

# --- 2. 简易智能出题算法（基于标点和关键词，防止第三方API卡死） ---
def generate_quiz_questions(text):
    if len(text) < 10:
        return []
    # 按照句子切分
    sentences = [s.strip() for s in text.replace("；", "。").replace("\n", "。").split("。") if len(s.strip()) > 8]
    if not sentences:
        return []
    
    quizzes = []
    # 随机抽取1-2个核心句子伪造成挖空提问
    sample_size = min(2, len(sentences))
    chosen_sentences = random.sample(sentences, sample_size)
    
    for q_text in chosen_sentences:
        # 尝试找出句子中的核心名词或关键连接词进行挖空
        keywords = ["因为", "所以", "核心", "基础", "根本", "核心", "实质", "特征", "要求", "主要", "矛盾"]
        blank_word = "【核心概念】"
        for kw in keywords:
            if kw in q_text:
                blank_word = kw
                break
        
        if blank_word == "【核心概念】" and len(q_text) > 15:
            # 如果没匹配到关键词，随机切断后半句作为填空
            split_pos = len(q_text) // 2
            question = q_text[:split_pos] + "______？"
            answer = q_text[split_pos:]
        else:
            question = q_text.replace(blank_word, "______") + " （请问横线处应该填什么？）"
            answer = blank_word
            
        quizzes.append({"question": question, "answer": q_text}) # 答案给出原句，最利于记忆核对
    return quizzes

# --- 3. 异步语音合成 ---
async def amain(text, voice, rate, output_filename) -> None:
    communicate = edge_tts.Communicate(text, voice, rate=rate)
    await communicate.save(output_filename)

# --- 4. 界面主程序 ---
def main():
    st.set_page_config(page_title="考研背诵超级磨耳朵", page_icon="🧠", layout="centered")
    st.title("🧠 考研背诵自测超级神器")
    st.caption("集成了定时循环复述、主动出题反思模块，考研上岸全靠它！")

    # 侧边栏
    st.sidebar.header("🎛️ 1. 语音及时间设置")
    
    # 扩充至10种专业配音演员音色
    voice_options = {
        "🎤 晓晓 (标准清晰女声)": "zh-CN-XiaoxiaoNeural",
        "🎤 云希 (稳重专业男声-肖秀荣同款推荐)": "zh-CN-YunxiNeural",
        "🎤 云健 (充满激情活力男声)": "zh-CN-YunjianNeural",
        "🎤 晓伊 (温柔文科专业课女声)": "zh-CN-XiaoyiNeural",
        "🎤 云夏 (清新元气学姐声)": "zh-CN-YunxiaNeural",
        "🎤 辽宁宁 (东北唠嗑式背诵风)": "zh-LN-XiaobeiNeural",
        "🎤 四川陕 (豪爽西南方言风)": "zh-SC-YunxiNeural",
        "🎤 陕西青 (沉稳西北风)": "zh-CN-shaanxi-XiaoniNeural",
        "🎤 晓辰 (知名电台情感女播音)": "zh-CN-XiaochenNeural",
        "🎤 云扬 (高端新闻纪录片男播)": "zh-CN-YunyangNeural"
    }
    selected_voice_label = st.sidebar.selectbox("选择背诵导师音色", list(voice_options.keys()))
    voice = voice_options[selected_voice_label]

    speed = st.sidebar.slider("调节语速 (0为正常)", min_value=-50, max_value=100, value=10, step=10)
    speed_str = f"+{speed}%" if speed >= 0 else f"{speed}%"

    # 功能一：循环时间设置
    loop_mode = st.sidebar.radio("循环模式", ["按遍数循环", "按时长磨耳朵"])
    loop_count = 1
    duration_min = 0
    
    if loop_mode == "按遍数循环":
        loop_count = st.sidebar.number_input("循环复述遍数", min_value=1, max_value=50, value=3)
    else:
        time_options = {"5分钟": 5, "10分钟": 10, "15分钟": 15, "30分钟": 30, "45分钟": 45, "1小时": 60}
        selected_time = st.sidebar.selectbox("选择磨耳朵时长", list(time_options.keys()))
        duration_min = time_options[selected_time]

    # 功能二：抽查提问模块设置
    st.sidebar.write("---")
    st.sidebar.header("❓ 2. 智能背诵抽查盲盒")
    enable_quiz = st.sidebar.checkbox("开启复述后随机提问抽查", value=True)
    
    quiz_mode = "电子答题"
    wait_time = 5
    if enable_quiz:
        quiz_mode = st.sidebar.radio("提问模式", ["📱 电子文字答题", "🔊 语音播报提问"])
        if quiz_mode == "🔊 语音播报提问":
            wait_time = st.sidebar.slider("留给脑海中想答案的时间 (秒)", min_value=5, max_value=15, value=10, step=5)

    # 主界面
    tab1, tab2 = st.tabs(["📝 直接粘贴文本", "📂 上传文档(PDF/Word)"])
    input_text = ""

    with tab1:
        input_text = st.text_area("粘贴需要背诵的专业课/政治大题/英语：", height=200, placeholder="例如：唯物辩证法认为...")

    with tab2:
        uploaded_file = st.file_uploader("支持 PDF, DOCX, TXT 格式", type=["txt", "pdf", "doc", "docx"])
        if uploaded_file is not None:
            with st.spinner("正在快速解析文件..."):
                input_text = extract_text_from_file(uploaded_file)
            st.success("文档解析成功！")

    # 开始生成
    if st.button("🚀 开始疯狂磨耳朵 + 模拟自测", type="primary"):
        if not input_text.strip():
            st.warning("⚠️ 请先提供需要背诵的内容！")
            return

        with st.spinner("正在为你编排背诵音频及提问试卷..."):
            # 逻辑处理：计算最终文本
            final_text = ""
            if loop_mode == "按遍数循环":
                for i in range(loop_count):
                    final_text += f"第{i+1}遍。 {input_text} \n\n "
            else:
                # 估算字数，1分钟正常语速约300字，根据设定时间强行复制拼接
                estimated_words_needed = duration_min * 300
                current_words = len(input_text)
                repeats = max(1, estimated_words_needed // current_words)
                for i in range(repeats):
                    final_text += f"第{i+1}轮循环。 {input_text} \n\n "

            # 提问模块逻辑接入
            quiz_data = []
            if enable_quiz:
                quiz_data = generate_quiz_questions(input_text)
                if quiz_data and quiz_mode == "🔊 语音播报提问":
                    final_text += " \n\n 复述环节结束，下面进入随机抽查提问环节，请听题。 "
                    for idx, q in enumerate(quiz_data):
                        final_text += f"第{idx+1}题：{q['question']} 。。。 请在倒计时中思考答案。 "
                        final_text += " 。 " * (wait_time // 2) # 利用句号和停顿模拟思考缓冲时间
                        final_text += f" 思考时间到。正确答案和原句参考为：{q['answer']} 。 "
                    final_text += " 提问环节结束，祝你考研顺利，成功上岸！"

            # 异步合成最终音频
            output_filename = "super_recitation.mp3"
            asyncio.run(amain(final_text, voice, speed_str, output_filename))

            # 将提问存入session缓存，以便前端展示
            st.session_state['quiz_data'] = quiz_data
            st.session_state['quiz_mode'] = quiz_mode
            st.session_state['enable_quiz'] = enable_quiz

        st.success("🎉 专属定制音频生成成功！")
        
        with open(output_filename, "rb") as audio_file:
            audio_bytes = audio_file.read()
            st.audio(audio_bytes, format="audio/mpeg")
            st.download_button(label="📥 导出音频到手机随时听", data=audio_bytes, file_name="考研背诵高分版.mp3")

        # 前端电子答题板展示
        if enable_quiz and quiz_data:
            st.write("---")
            st.subheader("📝 考研人背诵效果电子自测板")
            st.info("💡 建议：点击上方播放器听完背诵后，再来下方核对，或者直接利用下方进行默写输入。")
            
            for idx, q in enumerate(quiz_data):
                st.markdown(f"**📍 随机抽查第 {idx+1} 题：**")
                st.code(q['question'])
                
                if quiz_mode == "📱 电子文字答题":
                    user_ans = st.text_input(f"在这里输入你的核心关键词/默写记忆 (第{idx+1}题)", key=f"user_ans_{idx}")
                    with st.expander("🔍 查看官方参考原句及答案"):
                        st.success(q['answer'])
                else:
                    st.caption("提示：本轮提问已融入音频的末尾中，请戴耳机直接盲听并作答。")
                    with st.expander("🔍 点击展开文字版题目与答案对照"):
                        st.write(f"问题：{q['question']}")
                        st.success(f"答案：{q['answer']}")

if __name__ == "__main__":
    main()
