import streamlit as st
import asyncio
import edge_tts
import os
from pypdf import PdfReader
from docx import Document

# --- 1. 文档格式文本提取（去掉图片识别） ---
def extract_text_from_file(uploaded_file):
    file_extension = uploaded_file.name.split(".")[-1].lower()
    text = ""
    
    if file_extension == "txt":
        text = uploaded_file.read().decode("utf-8", errors="ignore")
        
    elif file_extension == "pdf":
        reader = PdfReader(uploaded_file)
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
                
    elif file_extension in ["doc", "docx"]:
        doc = Document(uploaded_file)
        for para in doc.paragraphs:
            text += para.text + "\n"
                
    return text.strip()

# --- 2. 异步调用 Edge-TTS 生成音频 ---
async def amain(text, voice, rate, output_filename) -> None:
    communicate = edge_tts.Communicate(text, voice, rate=rate)
    await communicate.save(output_filename)

# --- 3. Streamlit 前端界面 ---
def main():
    st.set_page_config(page_title="考研背诵磨耳朵神器", page_icon="📚", layout="centered")
    st.title("📚 考研背诵磨耳朵神器")
    st.caption("支持输入文字或上传 PDF/Word/TXT，自定义语速与朗读遍数。")

    st.sidebar.header("🎛️ 语音参数设置")
    
    voice_options = {
        "清晰女声 (晓晓)": "zh-CN-XiaoxiaoNeural",
        "稳重男声 (云希)": "zh-CN-YunxiNeural",
        "温柔女声 (晓伊)": "zh-CN-XiaoyiNeural",
        "情感男声 (云健)": "zh-CN-YunjianNeural"
    }
    selected_voice_label = st.sidebar.selectbox("选择朗读音色", list(voice_options.keys()))
    voice = voice_options[selected_voice_label]

    speed = st.sidebar.slider("语速调节 (0为正常语速)", min_value=-50, max_value=100, value=0, step=10)
    speed_str = f"+{speed}%" if speed >= 0 else f"{speed}%"
    loops = st.sidebar.number_input("循环复述遍数", min_value=1, max_value=20, value=3, step=1)

    tab1, tab2 = st.tabs(["📝 直接粘贴文本", "📂 上传文档(PDF/Word)"])
    input_text = ""

    with tab1:
        input_text = st.text_area("请在这里输入或粘贴你需要背诵的专业课/政治/英语文本：", height=250, placeholder="例如：唯物辩证法认为...")

    with tab2:
        uploaded_file = st.file_uploader("支持 PDF, DOCX, TXT 格式", type=["txt", "pdf", "doc", "docx"])
        if uploaded_file is not None:
            with st.spinner("正在努力解析文件中..."):
                input_text = extract_text_from_file(uploaded_file)
            st.success("文件解析成功！")
            st.text_area("解析出的文本内容：", value=input_text, height=150)

    if st.button("🚀 开始生成复述音频", type="primary"):
        if not input_text.strip():
            st.warning("⚠️ 请先输入文字或上传有效的文件！")
            return

        with st.spinner("正在为您疯狂合成背诵音频..."):
            final_text = ""
            for i in range(loops):
                final_text += f"第{i+1}遍。 {input_text} \n\n "
            
            output_filename = "output_recitation.mp3"
            asyncio.run(amain(final_text, voice, speed_str, output_filename))

        st.success(f"🎉 音频生成成功！已连续复述 {loops} 遍。")
        
        with open(output_filename, "rb") as audio_file:
            audio_bytes = audio_file.read()
            st.audio(audio_bytes, format="audio/mpeg")
            st.download_button(
                label="📥 下载音频到手机/电脑",
                data=audio_bytes,
                file_name="考研背诵音频.mp3",
                mime="audio/mpeg"
            )

if __name__ == "__main__":
    main()
