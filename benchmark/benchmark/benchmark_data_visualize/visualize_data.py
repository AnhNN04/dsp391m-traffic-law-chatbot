import json
import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from wordcloud import WordCloud
import re
from datetime import datetime

# Cấu hình đường dẫn
current_dir = os.path.dirname(os.path.abspath(__file__))
base_dir = os.path.dirname(os.path.dirname(current_dir))
data_path = os.path.join(base_dir, "benchmark", "benchmark_data", "preprocess", "clean_benchmark_data.json")
output_dir = os.path.join(base_dir, "benchmark", "benchmark_data_visualize")

if not os.path.exists(output_dir):
    os.makedirs(output_dir)

def load_data():
    with open(data_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def extract_year(date_str):
    try:
        return datetime.strptime(date_str, "%d/%m/%Y").year
    except:
        return 2024 # Default

def visualize():
    data = load_data()
    df = pd.DataFrame(data)
    
    # 1. Phân bổ theo năm (Data Distribution by Year)
    df['year'] = df['date'].apply(extract_year)
    year_counts = df['year'].value_counts().sort_index()
    
    plt.figure(figsize=(10, 6))
    sns.set_style("whitegrid")
    ax = sns.barplot(x=year_counts.index, y=year_counts.values, palette="viridis")
    plt.title("Benchmark data distribution by year", fontsize=15)
    plt.xlabel("Year", fontsize=12)
    plt.ylabel("Number of question", fontsize=12)
    for p in ax.patches:
        ax.annotate(f'{int(p.get_height())}', (p.get_x() + p.get_width() / 2., p.get_height()), 
                    ha='center', va='center', xytext=(0, 9), textcoords='offset points')
    plt.savefig(os.path.join(output_dir, "data_by_year.png"))
    print(f"Bản đồ năm đã lưu: {os.path.join(output_dir, 'data_by_year.png')}")

    # 2. Phân tích độ dài câu trả lời (Answer Length Distribution)
    df['ans_length'] = df['answer'].apply(len)
    plt.figure(figsize=(10, 6))
    sns.histplot(df['ans_length'], bins=20, kde=True, color="skyblue")
    plt.title("Answer length distribution", fontsize=15)
    plt.xlabel("Number of token", fontsize=12)
    plt.ylabel("Number of sample", fontsize=12)
    plt.savefig(os.path.join(output_dir, "answer_length.png"))
    print(f"Bản đồ độ dài đã lưu: {os.path.join(output_dir, 'answer_length.png')}")

    # 3. Word Cloud (Common Legal Topics)
    text = " ".join(df['question'])
    # Loại bỏ một số từ dừng tiếng Việt cơ bản
    stop_words = ["là", "của", "và", "có", "không", "bao", "nhiêu", "như", "thế", "nào", "được", "bị", "phạt", "cho", "xe", "ô", "tô", "máy"]
    
    wordcloud = WordCloud(width=800, height=400, background_color='white', 
                          colormap='Dark2', font_path='C:\\Windows\\Fonts\\Arial.ttf').generate(text)
    
    plt.figure(figsize=(15, 8))
    plt.imshow(wordcloud, interpolation='bilinear')
    plt.axis("off")
    plt.title("Common words in benchmark dataset", fontsize=20)
    plt.savefig(os.path.join(output_dir, "topic_wordcloud.png"))
    print(f"WordCloud đã lưu: {os.path.join(output_dir, 'topic_wordcloud.png')}")

    # 4. Thống kê nguồn dữ liệu (Source URL analysis - Top 5)
    df['domain'] = "Thư Viện Pháp Luật" # Vì hiện tại crawl 1 nguồn
    source_counts = df['url'].apply(lambda x: x.split('/')[2]).value_counts().head(5)
    plt.figure(figsize=(10, 6))
    plt.pie(source_counts.values, labels=source_counts.index, autopct='%1.1f%%', startangle=140, colors=sns.color_palette("pastel"))
    plt.title("Data sources", fontsize=15)
    plt.savefig(os.path.join(output_dir, "data_sources.png"))
    print(f"Biểu đồ nguồn đã lưu: {os.path.join(output_dir, 'data_sources.png')}")

if __name__ == "__main__":
    visualize()
