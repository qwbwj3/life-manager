import sys
import os
import argparse
from datetime import datetime
import json
import warnings
import shutil

# 忽略烦人的警告
warnings.filterwarnings("ignore")

# ==========================================
# Life Manager Core Engine - 完整实装版
# ==========================================

OBSIDIAN_VAULT_PATH = os.environ.get("OBSIDIAN_VAULT_PATH", os.path.expanduser("~/Library/Mobile Documents/iCloud~md~obsidian/Documents"))
DAILY_NOTES_DIR = os.path.join(OBSIDIAN_VAULT_PATH, "DailyNotes")
FINANCE_NOTES_DIR = os.path.join(OBSIDIAN_VAULT_PATH, "Finance")
ATTACHMENTS_DIR = os.path.join(OBSIDIAN_VAULT_PATH, "Attachments")

def setup_dirs():
    os.makedirs(DAILY_NOTES_DIR, exist_ok=True)
    os.makedirs(FINANCE_NOTES_DIR, exist_ok=True)
    os.makedirs(ATTACHMENTS_DIR, exist_ok=True)

# ------------------------------------------
# 核心功能模块
# ------------------------------------------

def handle_voice(audio_path):
    print(f"🎤 正在处理语音: {audio_path}")
    try:
        from funasr import AutoModel
        import re
        import google.generativeai as genai
        import subprocess
        import json
        
        print("-> 正在加载本地 SenseVoice 模型 (首次可能稍慢)...")
        model = AutoModel(model="iic/SenseVoiceSmall", device="cpu", disable_update=True)
        res = model.generate(input=audio_path)
        
        if res and len(res) > 0:
            raw_text = res[0]['text']
            clean_text = re.sub(r'<\|.*?\|>', '', raw_text)
            print(f"-> 识别成功: {clean_text}")
            
            api_key = os.environ.get("GEMINI_API_KEY")
            if not api_key:
                print("⚠️ 警告: 未设置 GEMINI_API_KEY，将直接输出原始转录文本。")
                now = datetime.now().strftime("%H:%M")
                return f"### 📥 碎片记录 ({now})\n> {clean_text}\n"

            print("-> 正在请求大模型进行语义分类与排版...")
            genai.configure(api_key=api_key)
            gemini_model = genai.GenerativeModel('gemini-3.1-pro-preview')
            
            now_obj = datetime.now()
            now_str = now_obj.strftime("%Y-%m-%d %H:%M:%S")
            now_time_only = now_obj.strftime("%H:%M")
            
            prompt = f"""
            你是一个私人生活管家。请分析以下通过语音转录的文字。
            当前准确时间是：{now_str}
            语音内容：“{clean_text}”
            
            请执行以下两步：
            第一步：判断这段语音的【意图】。
            - 如果这是在直接对我（你的 AI 助理）下达通用指令或聊天（比如：“帮我查一下天气”、“你觉得这个怎么样”、“给我讲个笑话”、“刚才那条记错了”），请在第一行输出纯 JSON：{{"is_chat": true, "is_reminder": false}}
            - 如果这是在记录生活、安排任务或写日记（比如：“提醒我明天开会”、“今天去吃了大餐”、“总结一下今天的工作”、“买点水果”），请在第一行输出纯 JSON：{{"is_chat": false, "is_reminder": true/false, "title": "任务标题", "due": "YYYY-MM-DD HH:MM"}}。如果时间不明确，可以不返回 due 字段。
            
            第二步：如果 is_chat 为 false，在 JSON 的下一行开始，将语音内容进行“书面化润色”（去除口语化语气词和重复停顿，不改变原意，保持第一人称）。然后分类和格式化为优美的 Markdown 片段。
            可能的分类：【✅ 备忘与待办】、【🏃‍♂️ 日常轨迹】、【📈 投资与交易】
            格式模板如下：
            
            ### 📥 {now_time_only} - [填写类别]
            > "（书面化润色后的原文）"
            
            **智能解析**：
            - （提取的关键点）
            """
            
            response = gemini_model.generate_content(prompt)
            lines = response.text.strip().split('\n')
            
            reminder_data = None
            try:
                first_line = lines[0].strip()
                if first_line.startswith('```json'): first_line = first_line[7:]
                if first_line.endswith('```'): first_line = first_line[:-3]
                reminder_data = json.loads(first_line)
                
                # 如果是聊天对话，直接返回特殊标记，不写入 Obsidian
                if reminder_data.get('is_chat'):
                    print("-> 识别为【对话/指令】意图，不写入日志。")
                    return f"[CHAT_INTENT] {clean_text}"
                    
                markdown_text = '\n'.join(lines[1:]).strip()
                if markdown_text.startswith('```markdown'): markdown_text = markdown_text[11:]
                if markdown_text.endswith('```'): markdown_text = markdown_text[:-3]
            except Exception as e:
                print(f"-> JSON 解析失败，跳过自动提醒。报错: {e}")
                markdown_text = response.text.strip()
            
            # 如果是待办，调用 Apple Reminders
            if reminder_data and reminder_data.get('is_reminder'):
                title = reminder_data.get('title', '新待办')
                due = reminder_data.get('due')
                cmd = ["remindctl", "add", "--title", title]
                if due:
                    cmd.extend(["--due", due])
                print(f"-> 发现待办事项，正在写入 Apple Reminders: {title} (Due: {due})")
                try:
                    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    print("-> ✅ 成功写入 Apple Reminders！")
                except FileNotFoundError:
                    print("-> ❌ 未找到 remindctl 命令，请确保已通过 Homebrew 安装。")
                except subprocess.CalledProcessError:
                    print("-> ❌ 写入 Apple Reminders 失败。")

            print("-> 分类排版完成！")
            return markdown_text.strip() + "\n"
        else:
            return f"### 📥 碎片记录 ({datetime.now().strftime('%H:%M')})\n> [未能识别出任何声音]\n"
            
    except Exception as e:
        print(f"❌ 语音识别出错: {e}")
        return ""

def handle_food(image_paths):
    print(f"🥗 正在分析 {len(image_paths)} 张食物图片...")
    try:
        import google.generativeai as genai
        from PIL import Image
        
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            print("❌ 错误: 未设置 GEMINI_API_KEY 环境变量。")
            return ""
            
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-3.1-pro-preview')
        
        images = []
        obsidian_images_md = ""
        
        for path in image_paths:
            # Copy to Obsidian Attachments
            filename = os.path.basename(path)
            dest_path = os.path.join(ATTACHMENTS_DIR, filename)
            shutil.copy2(path, dest_path)
            
            # Load image for Gemini
            img = Image.open(path)
            images.append(img)
            obsidian_images_md += f"![[{filename}]]\n"
        
        now = datetime.now()
        now_time_str = now.strftime("%H:%M")
        
        prompt = f"""
        你是一个精准的饮食记录员。当前时间是 {now_time_str}。
        请根据当前时间，推断这顿饭的时间属性（早餐、午餐、晚餐或夜宵/加餐）。
        请仔细观察提供的图片，准确识别里面的菜品（特别是中餐，要注意食材细节，如干锅花菜、红烧排骨等，不要随意编造西式菜名）。
        请直接输出以下格式的数据，不要包含任何多余的寒暄、解释或饮食建议：

        **餐食类型**：[基于时间推断的类型]
        **菜品识别**：[菜品1、菜品2...]
        **热量预估**：[总热量] 大卡
        **营养构成**：
        - 蛋白质：[预估克数或占比]
        - 碳水化合物：[预估克数或占比]
        - 脂肪：[预估克数或占比]
        """
        
        print("-> 正在请求大模型进行视觉分析...")
        request_data = [prompt] + images
        response = model.generate_content(request_data)
        
        obsidian_text = f"### 🥗 饮食记录 ({now_time_str})\n"
        obsidian_text += obsidian_images_md
        obsidian_text += f"\n{response.text.strip()}\n"
        
        return obsidian_text
        
    except Exception as e:
        print(f"❌ 食物分析出错: {e}")
        return ""

def handle_finance(file_path):
    print(f"💰 正在处理财务账单: {file_path}")
    try:
        import pandas as pd
        import google.generativeai as genai
        
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            print("❌ 错误: 未设置 GEMINI_API_KEY。")
            return ""
            
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-3.1-pro-preview')

        df = pd.read_excel(file_path, skiprows=16)
        df = df[df['收/支'] == '支出']
        df['金额(元)'] = pd.to_numeric(df['金额(元)'].astype(str).str.replace('¥', ''), errors='coerce')
        
        sample_df = df[['交易时间', '交易对方', '商品', '金额(元)']].copy()
        records_json = sample_df.to_json(orient='records', force_ascii=False)
        
        prompt = f"""
        你是一个专业的财务管家。请帮我给以下微信支付账单记录进行分类。
        可选分类：[餐饮美食, 交通出行, 日常购物, 生活缴费, 休闲娱乐, 人情往来, 医疗健康, 其他]
        返回格式必须是纯 JSON 数组（不要包裹在 ```json 代码块里），包含原始信息和新增的 '类别' 字段。
        账单数据：
        {records_json}
        """
        
        response = model.generate_content(prompt)
        
        result_text = response.text.strip()
        if result_text.startswith("```json"): result_text = result_text[7:]
        if result_text.startswith("```"): result_text = result_text[3:]
        if result_text.endswith("```"): result_text = result_text[:-3]
        
        categorized_data = json.loads(result_text)
        categorized_df = pd.DataFrame(categorized_data)
        
        summary = categorized_df.groupby('类别')['金额(元)'].sum().reset_index().sort_values(by='金额(元)', ascending=False)
        
        current_month = datetime.now().strftime("%Y-%m")
        report = f"## 💰 {current_month} 财务复盘\n\n### 📊 各类支出占比\n"
        for _, row in summary.iterrows():
            report += f"- **{row['类别']}**: ¥{row['金额(元)']:.2f}\n"
        
        report += "\n### 📝 详细支出清单\n"
        for _, row in categorized_df.iterrows():
            report += f"- {row['交易时间']} | {row['交易对方']} | {row['商品']} | **¥{row['金额(元)']}** ({row['类别']})\n"
            
        return report
        
    except Exception as e:
        print(f"❌ 财务处理出错: {e}")
        return ""

def append_to_daily_note(content):
    if not content: return
    today_str = datetime.now().strftime("%Y-%m-%d")
    note_path = os.path.join(DAILY_NOTES_DIR, f"{today_str}.md")
    
    if not os.path.exists(note_path):
        with open(note_path, 'w', encoding='utf-8') as f:
            f.write(f"# {today_str}\n\n")
            
    with open(note_path, 'a', encoding='utf-8') as f:
        f.write(f"\n{content}\n")
    print(f"\n✅ 内容已追加到 Obsidian: {note_path}")

def save_finance_report(content):
    if not content: return
    current_month = datetime.now().strftime("%Y-%m")
    note_path = os.path.join(FINANCE_NOTES_DIR, f"{current_month}_财务复盘.md")
    
    with open(note_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"\n✅ 财务报告已生成到 Obsidian: {note_path}")

if __name__ == "__main__":
    setup_dirs()
    parser = argparse.ArgumentParser(description="Life Manager Core Engine")
    parser.add_argument("action", choices=["voice", "food", "finance"], help="Action to perform")
    parser.add_argument("filepaths", nargs='+', help="Path(s) to the input file(s)")
    
    args = parser.parse_args()
    
    # Check all files exist
    for path in args.filepaths:
        if not os.path.exists(path):
            print(f"❌ 错误: 文件不存在 - {path}")
            sys.exit(1)

    if args.action == "voice":
        content = handle_voice(args.filepaths[0])
        if content and content.startswith("[CHAT_INTENT]"):
            print("\n" + content)
        else:
            append_to_daily_note(content)
    elif args.action == "food":
        content = handle_food(args.filepaths) # Pass the whole list
        append_to_daily_note(content)
    elif args.action == "finance":
        content = handle_finance(args.filepaths[0])
        save_finance_report(content)