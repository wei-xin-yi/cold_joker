import streamlit as st
import random
from langchain_openai import ChatOpenAI 
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

# 初始化会话状态
def init_session():
    if "history" not in st.session_state:
        st.session_state.history = []
    if "current_temp" not in st.session_state:
        st.session_state.current_temp = random.randint(-273, -1)  # 随机初始温度
    if "current_theme" not in st.session_state:
        st.session_state.current_theme = None
    if "last_joke" not in st.session_state:
        st.session_state.last_joke = None

init_session()

# 模型配置
model = ChatOpenAI(
    base_url="https://api.deepseek.com/v1",
    api_key="sk-70920fd964c54881a9d9d7503e231ba0",
    model="deepseek-chat",
    temperature=0.5,
)

# 系统角色设定
system_role = """你是一个冷笑话冰库，按以下规则工作：
1. 生成一个包含谐音梗或双关语的冷笑话
2. 结尾添加 ❄️(-XX℃) 温度标记
3. 温度值范围在 -5℃ 到 -273℃ 之间
4. 根据用户反馈动态调整寒冷程度
5. 用中文口语化风格交流
6. 每次只输出一个笑话
7. 不要输出对用户意图的判断，只需要根据要求输出笑话
"""

# 意图分析提示词
intent_prompt = """分析用户输入，返回最匹配的意图：
[当前主题] {theme}
[上次笑话] {joke}

可选意图：
1. GREETING - 问候或闲聊
2. NEW_THEME - 指定新主题
3. TOO_COLD - 认为笑话太冷
4. NOT_COLD - 认为不够冷
5. FEEDBACK - 其他反馈

注意：如果提到温度，需要判断下是否是希望指定笑话的温度，如果是的话返回FEEDBACK
只需返回意图关键词，不要其他内容。
输入：{input}"""

# 界面布局
st.title("❄️ 冷笑话冰库")
with st.expander("使用说明"):
    st.markdown("""1. 输入任意主题（如"万圣节"）\n2. 反馈寒冷指数
       \n- 太冷啦 → 调高温度
       \n- 不够冷 → 调低温度
    \n3. 想听新笑话?
       \n- 随时更换主题
    \n温度值越小表示冷笑话越冷哦～""")

# 显示历史消息
for msg in st.session_state.history:
    st.chat_message(msg["role"]).write(msg["content"])

# 用户输入处理
if prompt := st.chat_input("输入主题或反馈..."):
    # 添加用户消息
    st.session_state.history.append({"role": "user", "content": prompt})
    st.chat_message("user").write(prompt)

    # 意图识别
    intent_chain = (
        ChatPromptTemplate.from_template(intent_prompt)
        | model
        | StrOutputParser()
    )
    intent = intent_chain.invoke({
        "theme": st.session_state.current_theme or "无",
        "joke": st.session_state.last_joke or "无",
        "input": prompt
    }).strip()

    # 处理不同意图
    if "GREETING" in intent:
        response = f"""❄️ 你好！我是冷笑话机器人，可以：
        - 根据主题生成冰冷笑话 ❄️
        - 根据反馈调节寒冷指数 🌡
        请输入一个主题开始吧~"""
        temp_change = 0
    elif intent == "NEW_THEME":
        st.session_state.current_theme = prompt
        st.session_state.current_temp = random.randint(-273,-1)  # 重置温度
        joke_prompt = f"""主题：{prompt}
        只生成一个包含谐音梗的冷笑话，结尾用 ❄️(-XX℃) 标注，温度值在{-abs(st.session_state.current_temp)-10}℃左右。不要输出对用户意图的判断，只需要根据要求输出笑话"""
        response = model.invoke(joke_prompt).content
        temp_change = 0
    elif intent in ["TOO_COLD", "NOT_COLD"]:
    # 温度调整逻辑
        if intent == "TOO_COLD":
            temp_change = 10  # 提高温度
        else:
            temp_change = -10  # 降低温度

    # 更新当前温度
        st.session_state.current_temp += temp_change
    # 限制范围
        st.session_state.current_temp = max(min(st.session_state.current_temp, -1), -273)

    # 生成新的笑话
        adjust_prompt = f"""上次笑话：{st.session_state.last_joke}
    用户反馈：{prompt}
    只生成一个新的笑话（温度：{st.session_state.current_temp}℃），温度在结尾用 ❄️(-XX℃) 标注，同时保持主题：{st.session_state.current_theme}。不要输出对用户意图的判断，只需要根据要求输出笑话"""
        response = model.invoke(adjust_prompt).content
    else:
        response = model.invoke(f"""用户说：{prompt}，如果用户是在闲聊，请用亲切的语气引导用户输入冷笑话主题；
                                如果用户希望指定冷笑话的温度，请按照用户说的温度重新生成一个笑话，温度在结尾用 ❄️(-XX℃) 标注。
                                不要输出对用户意图的判断，只需要根据要求输出笑话""").content
        temp_change = 0

    # 确保温度标识格式正确
    if "❄️" not in response:
        response += f" ❄️({st.session_state.current_temp}℃)"

    # 更新状态
    st.session_state.last_joke = response
    st.session_state.history.append({"role": "assistant", "content": response})
    st.chat_message("assistant").write(response)

    with st.sidebar:
        st.subheader("❄️ 当前寒冷指数")
    
    # 获取历史温度数据
        current_temp = None
        prev_temp = None
    
        try:
        # 解析当前笑话温度
            current_joke = st.session_state.last_joke
            current_temp = int(current_joke.split("❄️(")[1].split("℃")[0])
        
        # 查找上一次有效笑话温度
            history_jokes = [msg["content"] for msg in st.session_state.history 
                            if msg["role"] == "assistant"]
            if len(history_jokes) > 1:
                prev_joke = history_jokes[-2]  # 获取前一个笑话
                prev_temp = int(prev_joke.split("❄️(")[1].split("℃")[0])
            
        except (IndexError, ValueError, AttributeError):
            pass
    
    # 计算温度变化
        delta_temp = current_temp - prev_temp if current_temp and prev_temp else None
    
    # 显示指标
        st.metric(
            label="温度",
            value=f"{current_temp}℃" if current_temp is not None else "N/A",
            delta=f"{delta_temp}℃" if delta_temp else None
        )
    
    # 进度条显示（使用实际温度或默认值）
        if current_temp is not None:
            st.progress(abs(current_temp)/273)
        else:
            st.progress(0)
        